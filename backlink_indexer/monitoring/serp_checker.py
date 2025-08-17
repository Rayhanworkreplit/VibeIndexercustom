"""
SERP (Search Engine Results Page) verification system
Checks if URLs are indexed by scraping search results
"""

import asyncio
import aiohttp
import random
import time
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from ..models import SERPResult
from ..anti_detection.stealth_browser import StealthBrowserManager


class SERPChecker:
    """
    Advanced SERP checker for verifying URL indexing status
    Supports multiple search engines with anti-detection
    """
    
    def __init__(self, config):
        self.config = config
        self.user_agent = UserAgent()
        self.browser_manager = StealthBrowserManager(config)
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.logger = logging.getLogger(__name__)
        
        self.search_engines = {
            'google': {
                'url': 'https://www.google.com/search',
                'params': {'q': '{query}', 'num': 20},
                'result_selector': '.g .yuRUbf a',
                'title_selector': 'h3',
                'snippet_selector': '.VwiC3b'
            },
            'bing': {
                'url': 'https://www.bing.com/search',
                'params': {'q': '{query}', 'count': 20},
                'result_selector': '.b_algo h2 a',
                'title_selector': '',
                'snippet_selector': '.b_caption p'
            },
            'yandex': {
                'url': 'https://yandex.com/search/',
                'params': {'text': '{query}', 'numdoc': 20},
                'result_selector': '.organic__url a',
                'title_selector': '.organic__title-wrapper',
                'snippet_selector': '.organic__text'
            },
            'duckduckgo': {
                'url': 'https://duckduckgo.com/html/',
                'params': {'q': '{query}'},
                'result_selector': '.result__a',
                'title_selector': '.result__title',
                'snippet_selector': '.result__snippet'
            }
        }
    
    async def check_url_indexed(self, url: str, search_engines: List[str] = None) -> Dict[str, SERPResult]:
        """Check if URL is indexed across multiple search engines"""
        
        if search_engines is None:
            search_engines = ['google', 'bing']
        
        # Generate search queries for the URL
        queries = self._generate_search_queries(url)
        results = {}
        
        for engine in search_engines:
            if engine not in self.search_engines:
                self.logger.warning(f"Unknown search engine: {engine}")
                continue
            
            engine_results = []
            
            for query in queries:
                try:
                    result = await self._search_engine(engine, query)
                    
                    # Check if URL appears in results
                    found = self._check_url_in_results(url, result.get('results', []))
                    
                    serp_result = SERPResult(
                        url=url,
                        query=query,
                        search_engine=engine,
                        found=found['found'],
                        position=found.get('position'),
                        title=found.get('title'),
                        snippet=found.get('snippet')
                    )
                    
                    engine_results.append(serp_result)
                    
                    # Add delay between queries to avoid rate limiting
                    await asyncio.sleep(random.uniform(2, 5))
                    
                except Exception as e:
                    self.logger.error(f"Error checking {url} on {engine}: {str(e)}")
            
            results[engine] = engine_results
        
        return results
    
    def _generate_search_queries(self, url: str) -> List[str]:
        """Generate effective search queries for a URL"""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        queries = [
            f'site:{domain} "{path}"',  # Exact path search
            f'site:{domain}',           # Domain search
            f'"{url}"',                 # Exact URL search
        ]
        
        # Add additional query variations
        if len(path) > 1:
            path_parts = [part for part in path.split('/') if part]
            if path_parts:
                # Search for path components
                queries.append(f'site:{domain} {" ".join(path_parts[:3])}')
        
        return queries
    
    async def _search_engine(self, engine: str, query: str) -> Dict[str, Any]:
        """Perform search on specified search engine"""
        
        engine_config = self.search_engines[engine]
        search_url = engine_config['url']
        
        # Format query parameters
        params = {}
        for key, value in engine_config['params'].items():
            params[key] = value.format(query=quote(query))
        
        headers = {
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_search_results(html, engine_config)
                    else:
                        self.logger.error(f"Search request failed with status {response.status}")
                        return {'results': []}
                        
        except asyncio.TimeoutError:
            self.logger.error(f"Search timeout for {engine}")
            return {'results': []}
        except Exception as e:
            self.logger.error(f"Search error for {engine}: {str(e)}")
            return {'results': []}
    
    def _parse_search_results(self, html: str, engine_config: Dict) -> Dict[str, Any]:
        """Parse search engine results HTML"""
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        try:
            # Find result containers
            result_elements = soup.select(engine_config['result_selector'])
            
            for i, element in enumerate(result_elements):
                try:
                    # Extract URL
                    url = element.get('href', '')
                    if not url.startswith('http'):
                        continue
                    
                    # Extract title
                    title = ""
                    if engine_config['title_selector']:
                        title_elem = element.select_one(engine_config['title_selector'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    else:
                        title = element.get_text(strip=True)
                    
                    # Extract snippet
                    snippet = ""
                    if engine_config['snippet_selector']:
                        snippet_elem = soup.select_one(engine_config['snippet_selector'])
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                    
                    results.append({
                        'url': url,
                        'title': title,
                        'snippet': snippet,
                        'position': i + 1
                    })
                    
                except Exception as e:
                    self.logger.debug(f"Error parsing result element: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error parsing search results: {str(e)}")
        
        return {'results': results}
    
    def _check_url_in_results(self, target_url: str, results: List[Dict]) -> Dict[str, Any]:
        """Check if target URL appears in search results"""
        
        from urllib.parse import urlparse
        
        target_parsed = urlparse(target_url)
        target_domain = target_parsed.netloc.lower()
        target_path = target_parsed.path.lower()
        
        for result in results:
            result_parsed = urlparse(result['url'])
            result_domain = result_parsed.netloc.lower()
            result_path = result_parsed.path.lower()
            
            # Exact match
            if result['url'] == target_url:
                return {
                    'found': True,
                    'position': result['position'],
                    'title': result['title'],
                    'snippet': result['snippet'],
                    'match_type': 'exact'
                }
            
            # Domain and path match
            if result_domain == target_domain and result_path == target_path:
                return {
                    'found': True,
                    'position': result['position'],
                    'title': result['title'],
                    'snippet': result['snippet'],
                    'match_type': 'domain_path'
                }
        
        return {'found': False}
    
    async def bulk_check_urls(self, urls: List[str], search_engines: List[str] = None, 
                             batch_size: int = 5) -> Dict[str, Dict[str, List[SERPResult]]]:
        """Check multiple URLs in batches to avoid rate limiting"""
        
        results = {}
        
        # Process URLs in batches
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = []
            for url in batch:
                task = self.check_url_indexed(url, search_engines)
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                url = batch[j]
                if isinstance(result, Exception):
                    self.logger.error(f"Error checking {url}: {str(result)}")
                    results[url] = {}
                else:
                    results[url] = result
            
            # Delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(random.uniform(10, 20))
        
        return results
    
    async def verify_indexing_success(self, urls: List[str], 
                                    min_engines: int = 2) -> Dict[str, bool]:
        """Verify if URLs are successfully indexed across minimum number of engines"""
        
        all_results = await self.bulk_check_urls(urls)
        verification_results = {}
        
        for url, engine_results in all_results.items():
            indexed_engines = 0
            
            for engine, serp_results in engine_results.items():
                # Check if URL was found in any query for this engine
                if any(result.found for result in serp_results):
                    indexed_engines += 1
            
            verification_results[url] = indexed_engines >= min_engines
        
        return verification_results
    
    def get_indexing_report(self, results: Dict[str, Dict[str, List[SERPResult]]]) -> Dict[str, Any]:
        """Generate comprehensive indexing report"""
        
        total_urls = len(results)
        indexed_urls = 0
        engine_stats = {}
        
        for url, engine_results in results.items():
            url_indexed = False
            
            for engine, serp_results in engine_results.items():
                if engine not in engine_stats:
                    engine_stats[engine] = {'total': 0, 'found': 0}
                
                engine_stats[engine]['total'] += 1
                
                found = any(result.found for result in serp_results)
                if found:
                    engine_stats[engine]['found'] += 1
                    url_indexed = True
            
            if url_indexed:
                indexed_urls += 1
        
        # Calculate success rates
        for engine in engine_stats:
            total = engine_stats[engine]['total']
            found = engine_stats[engine]['found']
            engine_stats[engine]['success_rate'] = (found / total * 100) if total > 0 else 0
        
        overall_success_rate = (indexed_urls / total_urls * 100) if total_urls > 0 else 0
        
        return {
            'total_urls': total_urls,
            'indexed_urls': indexed_urls,
            'overall_success_rate': overall_success_rate,
            'engine_statistics': engine_stats,
            'detailed_results': results
        }