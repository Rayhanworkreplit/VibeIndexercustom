"""
RSS Feed Distribution Engine
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from datetime import datetime, timedelta
import hashlib
import os
from .base import IndexingMethodBase


class RSSDistributionEngine(IndexingMethodBase):
    """RSS feed creation and distribution for indexing"""
    
    def __init__(self, config, browser_manager):
        super().__init__(config, browser_manager)
        self.feed_aggregators = [
            'http://ping.feedburner.com',
            'http://www.pingler.com/ping',
            'http://feedshark.brainbliss.com/ping'
        ]
        self.rss_directory = 'generated_feeds'
        os.makedirs(self.rss_directory, exist_ok=True)
    
    async def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create RSS feeds containing the URL and distribute them"""
        
        if not await self.validate_url(url):
            return {
                'url': url,
                'method': 'rss_distribution',
                'success': False,
                'error': 'Invalid URL format',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Generate RSS feed containing the URL
            feed_data = await self.generate_rss_feed(url, metadata)
            
            # Save RSS feed to file
            feed_path = await self.save_rss_feed(feed_data, url)
            
            # Distribute to aggregators
            distribution_results = await self.distribute_feed(feed_path)
            
            # Create sitemap entry for the RSS feed
            await self.create_sitemap_entry(feed_path)
            
            success = any(result.get('success', False) for result in distribution_results) if distribution_results else True
            
            return {
                'url': url,
                'method': 'rss_distribution',
                'success': success,
                'feed_path': feed_path,
                'distribution_results': distribution_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"RSS distribution failed for {url}: {str(e)}")
            return {
                'url': url,
                'method': 'rss_distribution',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def generate_rss_feed(self, target_url: str, metadata: Dict = None) -> str:
        """Generate RSS feed XML containing the target URL"""
        
        # Create RSS feed structure
        rss = ET.Element('rss', version='2.0')
        channel = ET.SubElement(rss, 'channel')
        
        # Feed metadata
        title = ET.SubElement(channel, 'title')
        title.text = metadata.get('title', 'Quality Content Feed')
        
        link = ET.SubElement(channel, 'link')
        link.text = target_url
        
        description = ET.SubElement(channel, 'description')
        description.text = metadata.get('description', 'Curated quality content and resources')
        
        language = ET.SubElement(channel, 'language')
        language.text = 'en-us'
        
        last_build_date = ET.SubElement(channel, 'lastBuildDate')
        last_build_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Create main item for target URL
        item = ET.SubElement(channel, 'item')
        
        item_title = ET.SubElement(item, 'title')
        item_title.text = self._generate_item_title(target_url, metadata)
        
        item_link = ET.SubElement(item, 'link')
        item_link.text = target_url
        
        item_description = ET.SubElement(item, 'description')
        item_description.text = self._generate_item_description(target_url, metadata)
        
        pub_date = ET.SubElement(item, 'pubDate')
        pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        guid = ET.SubElement(item, 'guid')
        guid.text = target_url
        
        # Add additional quality items to make feed look natural
        await self._add_filler_items(channel, target_url)
        
        # Convert to string
        return ET.tostring(rss, encoding='unicode', xml_declaration=True)
    
    async def _add_filler_items(self, channel: ET.Element, target_url: str):
        """Add additional items to make feed look natural"""
        
        filler_items = [
            {
                'title': 'Industry News and Updates',
                'description': 'Latest developments in the industry',
                'url': 'https://example.com/news'
            },
            {
                'title': 'Best Practices Guide',
                'description': 'Comprehensive guide to best practices',
                'url': 'https://example.com/guide'
            },
            {
                'title': 'Resource Collection',
                'description': 'Useful resources and tools',
                'url': 'https://example.com/resources'
            }
        ]
        
        for item_data in filler_items:
            item = ET.SubElement(channel, 'item')
            
            title = ET.SubElement(item, 'title')
            title.text = item_data['title']
            
            link = ET.SubElement(item, 'link')
            link.text = item_data['url']
            
            description = ET.SubElement(item, 'description')
            description.text = item_data['description']
            
            # Make dates slightly older
            pub_date = ET.SubElement(item, 'pubDate')
            old_date = datetime.now() - timedelta(days=1, hours=2)
            pub_date.text = old_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            guid = ET.SubElement(item, 'guid')
            guid.text = item_data['url']
    
    async def save_rss_feed(self, feed_content: str, target_url: str) -> str:
        """Save RSS feed to file and return path"""
        
        # Generate unique filename based on URL hash
        url_hash = hashlib.md5(target_url.encode()).hexdigest()[:10]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'feed_{url_hash}_{timestamp}.xml'
        filepath = os.path.join(self.rss_directory, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(feed_content)
        
        self.logger.info(f"RSS feed saved: {filepath}")
        return filepath
    
    async def distribute_feed(self, feed_path: str) -> List[Dict[str, Any]]:
        """Distribute RSS feed to aggregators"""
        
        results = []
        feed_url = self._get_feed_url(feed_path)
        
        async with aiohttp.ClientSession() as session:
            for aggregator in self.feed_aggregators:
                try:
                    result = await self._ping_aggregator(session, aggregator, feed_url)
                    results.append(result)
                    
                    # Rate limiting between pings
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Failed to ping {aggregator}: {str(e)}")
                    results.append({
                        'aggregator': aggregator,
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    async def _ping_aggregator(self, session: aiohttp.ClientSession, 
                              aggregator: str, feed_url: str) -> Dict[str, Any]:
        """Ping a specific aggregator with the RSS feed"""
        
        try:
            # Prepare ping data
            ping_data = {
                'url': feed_url,
                'name': 'Quality Content Feed'
            }
            
            async with session.post(aggregator, data=ping_data, timeout=10) as response:
                success = response.status == 200
                
                return {
                    'aggregator': aggregator,
                    'success': success,
                    'status_code': response.status,
                    'timestamp': datetime.now().isoformat()
                }
                
        except asyncio.TimeoutError:
            return {
                'aggregator': aggregator,
                'success': False,
                'error': 'Timeout'
            }
        except Exception as e:
            return {
                'aggregator': aggregator,
                'success': False,
                'error': str(e)
            }
    
    def _get_feed_url(self, feed_path: str) -> str:
        """Convert local feed path to accessible URL"""
        # In production, this would return the actual URL where the feed is hosted
        filename = os.path.basename(feed_path)
        return f"https://example.com/feeds/{filename}"
    
    async def create_sitemap_entry(self, feed_path: str):
        """Create sitemap entry for the RSS feed"""
        
        sitemap_path = os.path.join(self.rss_directory, 'sitemap.xml')
        feed_url = self._get_feed_url(feed_path)
        
        try:
            # Load existing sitemap or create new one
            if os.path.exists(sitemap_path):
                tree = ET.parse(sitemap_path)
                root = tree.getroot()
            else:
                root = ET.Element('urlset')
                root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            
            # Add new URL entry
            url_elem = ET.SubElement(root, 'url')
            
            loc = ET.SubElement(url_elem, 'loc')
            loc.text = feed_url
            
            lastmod = ET.SubElement(url_elem, 'lastmod')
            lastmod.text = datetime.now().strftime('%Y-%m-%d')
            
            changefreq = ET.SubElement(url_elem, 'changefreq')
            changefreq.text = 'daily'
            
            priority = ET.SubElement(url_elem, 'priority')
            priority.text = '0.8'
            
            # Save sitemap
            tree = ET.ElementTree(root)
            tree.write(sitemap_path, encoding='utf-8', xml_declaration=True)
            
            self.logger.info(f"Sitemap updated: {sitemap_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update sitemap: {str(e)}")
    
    def _generate_item_title(self, url: str, metadata: Dict = None) -> str:
        """Generate appropriate title for RSS item"""
        
        if metadata and 'title' in metadata:
            return metadata['title']
        
        # Extract domain for title
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            return f"Quality Content from {domain}"
        except:
            return "Interesting Content Resource"
    
    def _generate_item_description(self, url: str, metadata: Dict = None) -> str:
        """Generate appropriate description for RSS item"""
        
        if metadata and 'description' in metadata:
            return metadata['description']
        
        descriptions = [
            "Discover valuable insights and information in this comprehensive resource.",
            "A well-researched article covering important topics in the field.",
            "High-quality content that provides practical knowledge and expertise.",
            "Essential reading for anyone interested in staying updated on industry trends."
        ]
        
        import random
        return random.choice(descriptions)