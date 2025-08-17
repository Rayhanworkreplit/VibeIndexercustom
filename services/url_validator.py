import hashlib
import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app import db
from models import URL, CrawlResult
from config import Config

logger = logging.getLogger(__name__)

class URLValidator:
    """Comprehensive URL validation service"""
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=Config.REQUEST_TIMEOUT,
            follow_redirects=True,
            max_redirects=Config.MAX_REDIRECTS,
            headers={'User-Agent': Config.DEFAULT_USER_AGENT}
        )
    
    def validate_url(self, url_id: int) -> dict:
        """
        Perform comprehensive validation of a URL
        Returns validation results dict
        """
        url_obj = URL.query.get(url_id)
        if not url_obj:
            return {'success': False, 'error': 'URL not found'}
        
        url = url_obj.url
        start_time = time.time()
        issues = []
        
        try:
            # 1. Check robots.txt
            robots_allowed = self._check_robots_txt(url)
            if not robots_allowed:
                issues.append("Blocked by robots.txt")
            
            # 2. Fetch the URL
            response = self._fetch_url(url)
            response_time = time.time() - start_time
            
            if not response:
                issues.append("Failed to fetch URL")
                self._save_crawl_result(url_obj, None, issues, response_time)
                return {'success': False, 'issues': issues}
            
            # 3. Check HTTP status
            if response.status_code != 200:
                issues.append(f"HTTP {response.status_code}")
            
            # 4. Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 5. Check for noindex
            if self._has_noindex(soup, response.headers):
                issues.append("Meta noindex or X-Robots-Tag noindex")
            
            # 6. Validate canonical URL
            canonical_url = self._get_canonical_url(soup, url)
            canonical_ok = canonical_url == url or canonical_url is None
            if not canonical_ok:
                issues.append(f"Canonical mismatch: {canonical_url}")
            
            # 7. Content analysis
            content_hash = hashlib.md5(response.text.encode()).hexdigest()
            word_count = len(response.text.split())
            
            if word_count < 100:
                issues.append("Low content (< 100 words)")
            
            # 8. Check for structured data
            has_structured_data = self._has_structured_data(soup)
            
            # 9. Check content uniqueness (against other URLs)
            duplicate_url = self._check_content_duplicate(content_hash, url_obj.id)
            if duplicate_url:
                issues.append(f"Duplicate content detected (matches: {duplicate_url})")
            
            # Save crawl result
            crawl_result = self._save_crawl_result(
                url_obj, response, issues, response_time,
                robots_allowed, canonical_ok, canonical_url,
                content_hash, word_count, has_structured_data
            )
            
            # Update URL status based on validation
            if not issues:
                url_obj.status = 'ready'
                url_obj.last_error = None
            else:
                url_obj.status = 'error'
                url_obj.last_error = '; '.join(issues)
            
            url_obj.last_checked = datetime.utcnow()
            url_obj.content_hash = content_hash
            
            # Extract SEO metadata
            title_tag = soup.find('title')
            if title_tag:
                url_obj.title = title_tag.get_text().strip()[:512]
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                url_obj.meta_description = meta_desc.get('content', '').strip()
            
            db.session.commit()
            
            return {
                'success': True,
                'issues': issues,
                'status': url_obj.status,
                'crawl_id': crawl_result.id
            }
            
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            url_obj.status = 'error'
            url_obj.last_error = f"Validation error: {str(e)}"
            url_obj.last_checked = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }
    
    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            return rp.can_fetch('Googlebot', url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {str(e)}")
            return True  # Allow by default if robots.txt check fails
    
    def _fetch_url(self, url: str):
        """Fetch URL content with error handling"""
        try:
            response = self.client.get(url)
            return response
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def _has_noindex(self, soup: BeautifulSoup, headers: dict) -> bool:
        """Check for noindex directives in meta tags or headers"""
        # Check meta robots tag
        meta_robots = soup.find('meta', attrs={'name': re.compile(r'robots', re.I)})
        if meta_robots:
            content = meta_robots.get('content', '').lower()
            if 'noindex' in content:
                return True
        
        # Check X-Robots-Tag header
        x_robots_tag = headers.get('X-Robots-Tag', '').lower()
        if 'noindex' in x_robots_tag:
            return True
        
        return False
    
    def _get_canonical_url(self, soup: BeautifulSoup, original_url: str) -> str:
        """Extract canonical URL from link tag"""
        canonical_link = soup.find('link', attrs={'rel': 'canonical'})
        if canonical_link and canonical_link.get('href'):
            canonical_url = canonical_link['href']
            # Convert relative URLs to absolute
            if not canonical_url.startswith(('http://', 'https://')):
                canonical_url = urljoin(original_url, canonical_url)
            return canonical_url.rstrip('/')
        return None
    
    def _has_structured_data(self, soup: BeautifulSoup) -> bool:
        """Check for structured data (JSON-LD, microdata, etc.)"""
        # Check for JSON-LD
        json_ld = soup.find('script', attrs={'type': 'application/ld+json'})
        if json_ld:
            return True
        
        # Check for microdata
        microdata = soup.find(attrs={'itemscope': True})
        if microdata:
            return True
        
        # Check for RDFa
        rdfa = soup.find(attrs={'vocab': True}) or soup.find(attrs={'typeof': True})
        if rdfa:
            return True
        
        return False
    
    def _check_content_duplicate(self, content_hash: str, current_url_id: int) -> str:
        """Check if content hash matches another URL"""
        duplicate = CrawlResult.query.filter(
            CrawlResult.content_hash == content_hash,
            CrawlResult.url_id != current_url_id
        ).join(URL).first()
        
        return duplicate.url.url if duplicate else None
    
    def _save_crawl_result(self, url_obj: URL, response, issues: list, response_time: float,
                          robots_allowed: bool = None, canonical_ok: bool = None,
                          canonical_url: str = None, content_hash: str = None,
                          word_count: int = None, has_structured_data: bool = None) -> CrawlResult:
        """Save crawl result to database"""
        
        crawl_result = CrawlResult()
        crawl_result.url_id = url_obj.id
        crawl_result.status_code = response.status_code if response else None
        crawl_result.response_time = response_time
        crawl_result.content_length = len(response.text) if response else None
        crawl_result.content_type = response.headers.get('content-type') if response else None
        crawl_result.robots_allowed = robots_allowed
        crawl_result.has_noindex = not robots_allowed if robots_allowed is not None else None
        crawl_result.canonical_ok = canonical_ok
        crawl_result.canonical_url = canonical_url
        crawl_result.content_hash = content_hash
        crawl_result.word_count = word_count
        crawl_result.has_structured_data = has_structured_data
        crawl_result.validation_errors = '; '.join(issues) if issues else None
        
        db.session.add(crawl_result)
        return crawl_result
    
    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()

def validate_single_url(url_id: int) -> dict:
    """Convenience function to validate a single URL"""
    validator = URLValidator()
    try:
        return validator.validate_url(url_id)
    finally:
        del validator
