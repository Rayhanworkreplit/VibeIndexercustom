import re
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, urlunparse
from typing import List, Set

import httpx
from bs4 import BeautifulSoup
import trafilatura

from config import Config
from utils.helpers import is_valid_url, normalize_url

logger = logging.getLogger(__name__)

class URLDiscovery:
    """Service for discovering URLs from various sources"""
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=Config.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={'User-Agent': Config.DEFAULT_USER_AGENT}
        )
        self.discovered_urls: Set[str] = set()
    
    def discover_from_sitemap(self, sitemap_url: str) -> List[str]:
        """Discover URLs from XML sitemap"""
        try:
            response = self.client.get(sitemap_url)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.text)
            
            # Handle sitemap index
            if 'sitemapindex' in root.tag:
                return self._parse_sitemap_index(root, sitemap_url)
            
            # Handle regular sitemap
            elif 'urlset' in root.tag:
                return self._parse_sitemap(root)
            
            else:
                logger.warning(f"Unknown sitemap format: {sitemap_url}")
                return []
                
        except Exception as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {str(e)}")
            return []
    
    def _parse_sitemap_index(self, root: ET.Element, base_url: str) -> List[str]:
        """Parse sitemap index and recursively parse child sitemaps"""
        urls = []
        
        # Extract namespace
        ns = {'': root.tag.split('}')[0][1:]} if '}' in root.tag else {}
        
        for sitemap in root.findall('.//sitemap', ns) if ns else root.findall('.//sitemap'):
            loc_elem = sitemap.find('loc', ns) if ns else sitemap.find('loc')
            if loc_elem is not None and loc_elem.text:
                child_sitemap_url = loc_elem.text.strip()
                # Resolve relative URLs
                child_sitemap_url = urljoin(base_url, child_sitemap_url)
                
                # Recursively parse child sitemap
                child_urls = self.discover_from_sitemap(child_sitemap_url)
                urls.extend(child_urls)
        
        return urls
    
    def _parse_sitemap(self, root: ET.Element) -> List[str]:
        """Parse regular sitemap and extract URLs"""
        urls = []
        
        # Extract namespace
        ns = {'': root.tag.split('}')[0][1:]} if '}' in root.tag else {}
        
        for url_elem in root.findall('.//url', ns) if ns else root.findall('.//url'):
            loc_elem = url_elem.find('loc', ns) if ns else url_elem.find('loc')
            if loc_elem is not None and loc_elem.text:
                url = loc_elem.text.strip()
                if is_valid_url(url):
                    normalized_url = normalize_url(url)
                    urls.append(normalized_url)
        
        return urls
    
    def discover_from_rss(self, rss_url: str) -> List[str]:
        """Discover URLs from RSS/Atom feeds"""
        try:
            response = self.client.get(rss_url)
            response.raise_for_status()
            
            # Parse RSS/Atom feed
            root = ET.fromstring(response.text)
            urls = []
            
            # RSS 2.0
            if root.tag == 'rss':
                for item in root.findall('.//item'):
                    link_elem = item.find('link')
                    if link_elem is not None and link_elem.text:
                        url = link_elem.text.strip()
                        if is_valid_url(url):
                            urls.append(normalize_url(url))
            
            # Atom
            elif 'feed' in root.tag:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('.//atom:entry', ns):
                    link_elem = entry.find('atom:link[@rel="alternate"]', ns)
                    if link_elem is not None and link_elem.get('href'):
                        url = link_elem.get('href').strip()
                        if is_valid_url(url):
                            urls.append(normalize_url(url))
            
            return urls
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed {rss_url}: {str(e)}")
            return []
    
    def discover_from_webpage(self, page_url: str, same_domain_only: bool = True) -> List[str]:
        """Discover URLs from internal links on a webpage"""
        try:
            response = self.client.get(page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            base_domain = urlparse(page_url).netloc
            urls = []
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                
                # Skip empty, javascript, mailto, tel links
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(page_url, href)
                
                # Filter by domain if requested
                if same_domain_only:
                    link_domain = urlparse(full_url).netloc
                    if link_domain != base_domain:
                        continue
                
                if is_valid_url(full_url):
                    normalized_url = normalize_url(full_url)
                    urls.append(normalized_url)
            
            return list(set(urls))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error discovering URLs from webpage {page_url}: {str(e)}")
            return []
    
    def discover_from_robots_txt(self, site_url: str) -> List[str]:
        """Discover sitemaps from robots.txt"""
        try:
            parsed_url = urlparse(site_url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            response = self.client.get(robots_url)
            response.raise_for_status()
            
            # Parse robots.txt for sitemap declarations
            sitemap_urls = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line[8:].strip()  # Remove 'sitemap:' prefix
                    if is_valid_url(sitemap_url):
                        sitemap_urls.append(sitemap_url)
            
            # Discover URLs from found sitemaps
            all_urls = []
            for sitemap_url in sitemap_urls:
                urls = self.discover_from_sitemap(sitemap_url)
                all_urls.extend(urls)
            
            return all_urls
            
        except Exception as e:
            logger.error(f"Error parsing robots.txt for {site_url}: {str(e)}")
            return []
    
    def discover_from_crawl(self, start_url: str, max_depth: int = 2, max_urls: int = 1000) -> List[str]:
        """Discover URLs by crawling website (limited depth)"""
        discovered = set()
        to_crawl = [(start_url, 0)]  # (url, depth)
        crawled = set()
        
        base_domain = urlparse(start_url).netloc
        
        while to_crawl and len(discovered) < max_urls:
            url, depth = to_crawl.pop(0)
            
            if url in crawled or depth > max_depth:
                continue
            
            crawled.add(url)
            
            try:
                # Get page content
                response = self.client.get(url)
                if response.status_code != 200:
                    continue
                
                discovered.add(url)
                
                # Extract links if not at max depth
                if depth < max_depth:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for link in soup.find_all('a', href=True):
                        href = link['href'].strip()
                        
                        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                            continue
                        
                        full_url = urljoin(url, href)
                        link_domain = urlparse(full_url).netloc
                        
                        # Only follow same-domain links
                        if link_domain != base_domain:
                            continue
                        
                        if is_valid_url(full_url) and full_url not in crawled:
                            normalized_url = normalize_url(full_url)
                            to_crawl.append((normalized_url, depth + 1))
                
            except Exception as e:
                logger.warning(f"Error crawling {url}: {str(e)}")
                continue
        
        return list(discovered)
    
    def discover_from_api(self, api_endpoint: str, api_key: str = None) -> List[str]:
        """Discover URLs from custom API endpoint"""
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = self.client.get(api_endpoint, headers=headers)
            response.raise_for_status()
            
            # Assuming API returns JSON with URLs array
            data = response.json()
            urls = []
            
            # Handle different response formats
            if isinstance(data, list):
                # Direct array of URLs
                urls = [url for url in data if is_valid_url(url)]
            elif isinstance(data, dict):
                # Look for common keys
                for key in ['urls', 'pages', 'links', 'results']:
                    if key in data and isinstance(data[key], list):
                        urls = [url for url in data[key] if is_valid_url(url)]
                        break
            
            return [normalize_url(url) for url in urls]
            
        except Exception as e:
            logger.error(f"Error discovering URLs from API {api_endpoint}: {str(e)}")
            return []
    
    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()

def discover_urls(source_type: str, source_url: str = None, **kwargs) -> List[str]:
    """
    Discover URLs from various sources
    
    Args:
        source_type: Type of source ('sitemap', 'rss', 'webpage', 'robots', 'crawl', 'api')
        source_url: URL of the source
        **kwargs: Additional parameters for specific source types
    
    Returns:
        List of discovered URLs
    """
    discovery = URLDiscovery()
    
    try:
        if source_type == 'sitemap':
            return discovery.discover_from_sitemap(source_url)
        
        elif source_type == 'rss':
            return discovery.discover_from_rss(source_url)
        
        elif source_type == 'webpage':
            same_domain_only = kwargs.get('same_domain_only', True)
            return discovery.discover_from_webpage(source_url, same_domain_only)
        
        elif source_type == 'robots':
            return discovery.discover_from_robots_txt(source_url)
        
        elif source_type == 'crawl':
            max_depth = kwargs.get('max_depth', 2)
            max_urls = kwargs.get('max_urls', 1000)
            return discovery.discover_from_crawl(source_url, max_depth, max_urls)
        
        elif source_type == 'api':
            api_key = kwargs.get('api_key')
            return discovery.discover_from_api(source_url, api_key)
        
        else:
            logger.error(f"Unknown source type: {source_type}")
            return []
    
    finally:
        del discovery
