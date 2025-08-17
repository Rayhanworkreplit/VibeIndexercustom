"""
SERP (Search Engine Results Page) checker for indexing verification
"""

import asyncio
import aiohttp
import random
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus


class SERPChecker:
    """Advanced SERP checking for indexing verification"""
    
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        
        # Search engines to check
        self.search_engines = {
            'google': {
                'search_url': 'https://www.google.com/search',
                'params': {'q': '', 'num': 20, 'hl': 'en'},
                'result_selector': '.g',
                'link_selector': 'h3 a',
                'authority_weight': 0.9
            },
            'bing': {
                'search_url': 'https://www.bing.com/search',
                'params': {'q': '', 'count': 20},
                'result_selector': '.b_algo',
                'link_selector': 'h2 a',
                'authority_weight': 0.7
            },
            'duckduckgo': {
                'search_url': 'https://duckduckgo.com/html',
                'params': {'q': '', 'kl': 'us-en'},
                'result_selector': '.result',
                'link_selector': '.result__a',
                'authority_weight': 0.5
            }
        }
        
        # Query patterns for checking
        self.query_patterns = [
            'site:{domain}',
            'site:{domain} "{keyword}"',
            '"{full_url}"',
            'inurl:{path}',
            '"{title}" site:{domain}'
        ]
        
        # Rate limiting
        self.last_request_time = {}
        self.min_delay_between_requests = 5  # seconds
        
    def setup_logging(self):
        """Configure logging for SERP checking"""
        self.logger = logging.getLogger(f"{__name__}.SERPChecker")
    
    async def check_url_indexing(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check if URL is indexed in search engines"""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        path = parsed_url.path
        
        metadata = metadata or {}
        title = metadata.get('title', '')
        keywords = metadata.get('keywords', [])
        
        indexing_results = {
            'url': url,
            'domain': domain,
            'indexed_engines': [],
            'total_engines_checked': 0,
            'indexing_score': 0.0,
            'search_results': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate search queries
        search_queries = self.generate_search_queries(url, domain, path, title, keywords)
        
        # Check each search engine
        for engine_name, engine_config in self.search_engines.items():
            try:
                engine_result = await self.check_engine_indexing(
                    engine_name, engine_config, search_queries, url
                )
                
                indexing_results['search_results'][engine_name] = engine_result
                indexing_results['total_engines_checked'] += 1
                
                if engine_result['indexed']:
                    indexing_results['indexed_engines'].append(engine_name)
                
                # Add weighted score
                if engine_result['indexed']:
                    indexing_results['indexing_score'] += engine_config['authority_weight']
                
                # Rate limiting between engines
                await asyncio.sleep(random.uniform(3, 7))
                
            except Exception as e:
                self.logger.error(f"Error checking {engine_name}: {str(e)}")
                indexing_results['search_results'][engine_name] = {
                    'indexed': False,
                    'error': str(e),
                    'queries_tried': 0
                }
        
        # Normalize indexing score
        max_possible_score = sum(config['authority_weight'] for config in self.search_engines.values())
        if max_possible_score > 0:
            indexing_results['indexing_score'] = indexing_results['indexing_score'] / max_possible_score
        
        return indexing_results
    
    def generate_search_queries(self, url: str, domain: str, path: str, title: str, keywords: List[str]) -> List[str]:
        """Generate various search queries to check for indexing"""
        queries = []
        
        # Extract main keyword from title or URL
        main_keyword = ''
        if title:
            # Use first few words of title as keyword
            title_words = title.split()[:3]
            main_keyword = ' '.join(title_words)
        elif keywords:
            main_keyword = keywords[0] if isinstance(keywords, list) else str(keywords)
        
        # Generate queries based on patterns
        for pattern in self.query_patterns:
            try:
                if '{domain}' in pattern:
                    query = pattern.format(domain=domain, keyword=main_keyword, 
                                         full_url=url, path=path, title=title)
                    if query and len(query.strip()) > 5:  # Valid query
                        queries.append(query.strip())
            except:
                continue
        
        # Add direct URL search
        queries.append(f'"{url}"')
        
        # Add domain-specific searches
        queries.append(f'site:{domain}')
        
        # Remove duplicates while preserving order
        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        return unique_queries[:5]  # Limit to top 5 queries
    
    async def check_engine_indexing(self, engine_name: str, engine_config: Dict[str, Any], 
                                  queries: List[str], target_url: str) -> Dict[str, Any]:
        """Check indexing status on a specific search engine"""
        result = {
            'indexed': False,
            'queries_tried': 0,
            'matches_found': 0,
            'positions': [],
            'query_results': {}
        }
        
        # Rate limiting
        await self.respect_rate_limit(engine_name)
        
        for query in queries:
            try:
                query_result = await self.perform_search(engine_name, engine_config, query)
                result['queries_tried'] += 1
                result['query_results'][query] = query_result
                
                # Check if target URL is in results
                position = self.find_url_in_results(target_url, query_result.get('urls', []))
                
                if position is not None:
                    result['indexed'] = True
                    result['matches_found'] += 1
                    result['positions'].append({
                        'query': query,
                        'position': position
                    })
                
                # Rate limiting between queries
                await asyncio.sleep(random.uniform(2, 4))
                
            except Exception as e:
                self.logger.debug(f"Query failed for {engine_name}: {query} - {str(e)}")
                result['query_results'][query] = {'error': str(e)}
        
        return result
    
    async def perform_search(self, engine_name: str, engine_config: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Perform actual search query on search engine"""
        search_url = engine_config['search_url']
        params = engine_config['params'].copy()
        params['q'] = query
        
        # Build request URL
        full_url = f"{search_url}?{urlencode(params)}"
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(full_url, headers=headers) as response:
                if response.status == 200:
                    html_content = await response.text()
                    return self.parse_search_results(html_content, engine_config)
                else:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
    
    def parse_search_results(self, html_content: str, engine_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse search results HTML to extract URLs"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find result containers
            result_containers = soup.select(engine_config['result_selector'])
            
            urls = []
            for container in result_containers[:20]:  # Top 20 results
                try:
                    # Find link within container
                    link_element = container.select_one(engine_config['link_selector'])
                    if link_element and link_element.get('href'):
                        url = link_element['href']
                        
                        # Clean URL (remove Google redirect, etc.)
                        cleaned_url = self.clean_search_result_url(url)
                        if cleaned_url:
                            urls.append(cleaned_url)
                            
                except Exception as e:
                    continue
            
            return {
                'urls': urls,
                'total_results': len(urls)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse search results: {str(e)}")
            return {'urls': [], 'total_results': 0}
    
    def clean_search_result_url(self, url: str) -> Optional[str]:
        """Clean search result URL (remove redirects, etc.)"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            # Handle Google redirect URLs
            if 'google.com/url?' in url:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                if 'url' in query_params:
                    return query_params['url'][0]
                elif 'q' in query_params:
                    return query_params['q'][0]
            
            # Handle Bing redirect URLs
            if 'bing.com/ck/a?' in url:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                if 'u' in query_params:
                    # Bing uses base64 encoding sometimes
                    return query_params['u'][0]
            
            # Return URL as-is if no cleaning needed
            if url.startswith('http'):
                return url
            
            return None
            
        except Exception:
            return None
    
    def find_url_in_results(self, target_url: str, result_urls: List[str]) -> Optional[int]:
        """Find target URL in search results and return position"""
        try:
            from urllib.parse import urlparse
            
            target_parsed = urlparse(target_url)
            target_domain = target_parsed.netloc.replace('www.', '')
            target_path = target_parsed.path.rstrip('/')
            
            for i, result_url in enumerate(result_urls):
                try:
                    result_parsed = urlparse(result_url)
                    result_domain = result_parsed.netloc.replace('www.', '')
                    result_path = result_parsed.path.rstrip('/')
                    
                    # Exact match
                    if target_url == result_url:
                        return i + 1
                    
                    # Domain and path match
                    if target_domain == result_domain and target_path == result_path:
                        return i + 1
                    
                    # Subdomain match (for broader coverage)
                    if target_domain in result_domain or result_domain in target_domain:
                        if target_path == result_path:
                            return i + 1
                            
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"URL matching failed: {str(e)}")
            return None
    
    async def respect_rate_limit(self, engine_name: str):
        """Ensure rate limiting between requests"""
        if engine_name in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[engine_name]
            if time_since_last < self.min_delay_between_requests:
                wait_time = self.min_delay_between_requests - time_since_last
                await asyncio.sleep(wait_time)
        
        self.last_request_time[engine_name] = time.time()
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent for searches"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        return random.choice(user_agents)
    
    async def batch_check_indexing(self, urls: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Check indexing status for multiple URLs"""
        metadata_list = metadata_list or [{}] * len(urls)
        
        results = []
        for i, url in enumerate(urls):
            metadata = metadata_list[i] if i < len(metadata_list) else {}
            
            try:
                result = await self.check_url_indexing(url, metadata)
                results.append(result)
                
                # Delay between URL checks to avoid being blocked
                await asyncio.sleep(random.uniform(10, 20))
                
            except Exception as e:
                self.logger.error(f"Batch check failed for {url}: {str(e)}")
                results.append({
                    'url': url,
                    'indexed_engines': [],
                    'indexing_score': 0.0,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def get_indexing_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from indexing check results"""
        if not results:
            return {}
        
        total_urls = len(results)
        indexed_urls = sum(1 for r in results if r.get('indexing_score', 0) > 0)
        
        # Engine-specific stats
        engine_stats = {}
        for engine in self.search_engines.keys():
            engine_indexed = sum(1 for r in results if engine in r.get('indexed_engines', []))
            engine_stats[engine] = {
                'indexed_count': engine_indexed,
                'indexing_rate': engine_indexed / total_urls if total_urls > 0 else 0
            }
        
        # Average scores
        avg_score = sum(r.get('indexing_score', 0) for r in results) / total_urls if total_urls > 0 else 0
        
        return {
            'total_urls_checked': total_urls,
            'indexed_urls': indexed_urls,
            'overall_indexing_rate': indexed_urls / total_urls if total_urls > 0 else 0,
            'average_indexing_score': avg_score,
            'engine_stats': engine_stats,
            'timestamp': datetime.now().isoformat()
        }