"""
Enhanced coordinator for the comprehensive backlink indexing system
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json

from .config import IndexingConfig, URLRecord
from ..automation.browser_manager import StealthBrowserManager
from ..automation.proxy_rotator import ProxyRotator
from ..automation.user_agent_rotator import UserAgentRotator
from ..automation.stealth_features import StealthFeatures

from ..indexing_methods.social_bookmarking import SocialBookmarkingEngine
from ..indexing_methods.rss_distribution import RSSDistributionEngine
from ..indexing_methods.web2_posting import Web2PostingEngine
from ..indexing_methods.forum_commenting import ForumCommentingEngine
from ..indexing_methods.directory_submission import DirectorySubmissionEngine
from ..indexing_methods.social_signals import SocialSignalEngine

from ..monitoring.serp_checker import SERPChecker
from ..monitoring.success_tracker import SuccessTracker, IndexingAttempt


class MultiLayerIndexingStrategy:
    """Multi-layered indexing strategy for maximum coverage"""
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.setup_logging()
        
        # Strategy configuration
        self.strategy_layers = {
            'primary': ['social_bookmarking', 'rss_distribution', 'web2_posting'],
            'secondary': ['forum_commenting', 'directory_submission'],
            'amplification': ['social_signals']
        }
        
        # Success thresholds for each layer
        self.layer_thresholds = {
            'primary': 0.7,      # 70% success rate to proceed
            'secondary': 0.5,    # 50% success rate to proceed
            'amplification': 0.3  # 30% success rate acceptable
        }
    
    def setup_logging(self):
        """Configure logging"""
        self.logger = logging.getLogger(f"{__name__}.MultiLayerStrategy")
    
    async def execute_layered_strategy(self, urls: List[str], metadata_list: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute multi-layered indexing strategy"""
        metadata_list = metadata_list or [{}] * len(urls)
        
        strategy_results = {
            'urls_processed': len(urls),
            'layer_results': {},
            'overall_success_rate': 0.0,
            'failed_urls': [],
            'successful_urls': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Track URLs through each layer
        remaining_urls = list(zip(urls, metadata_list))
        
        # Execute primary layer
        if remaining_urls:
            primary_results = await self.execute_layer(
                'primary', remaining_urls
            )
            strategy_results['layer_results']['primary'] = primary_results
            
            # Filter out successful URLs
            remaining_urls = self.filter_unsuccessful_urls(remaining_urls, primary_results)
        
        # Execute secondary layer for remaining URLs
        if remaining_urls and len(remaining_urls) > 0:
            secondary_results = await self.execute_layer(
                'secondary', remaining_urls
            )
            strategy_results['layer_results']['secondary'] = secondary_results
            
            # Filter again
            remaining_urls = self.filter_unsuccessful_urls(remaining_urls, secondary_results)
        
        # Execute amplification layer for all URLs (regardless of previous success)
        amplification_urls = list(zip(urls, metadata_list))  # Reset to all URLs
        amplification_results = await self.execute_layer(
            'amplification', amplification_urls
        )
        strategy_results['layer_results']['amplification'] = amplification_results
        
        # Calculate overall results
        self.calculate_overall_results(strategy_results, urls)
        
        return strategy_results
    
    async def execute_layer(self, layer_name: str, url_metadata_pairs: List[tuple]) -> Dict[str, Any]:
        """Execute a specific strategy layer"""
        methods = self.strategy_layers[layer_name]
        layer_results = {
            'layer': layer_name,
            'methods_used': methods,
            'method_results': {},
            'success_rate': 0.0,
            'total_attempts': len(url_metadata_pairs)
        }
        
        # Execute all methods in parallel for better performance
        method_tasks = []
        for method_name in methods:
            if hasattr(self.coordinator, f"{method_name}_engine"):
                engine = getattr(self.coordinator, f"{method_name}_engine")
                urls = [pair[0] for pair in url_metadata_pairs]
                task = self.execute_method_batch(engine, method_name, urls)
                method_tasks.append(task)
        
        # Wait for all methods to complete
        if method_tasks:
            method_results_list = await asyncio.gather(*method_tasks, return_exceptions=True)
            
            # Process results
            for i, method_name in enumerate(methods):
                if i < len(method_results_list):
                    result = method_results_list[i]
                    if not isinstance(result, Exception):
                        layer_results['method_results'][method_name] = result
                    else:
                        self.logger.error(f"Method {method_name} failed: {str(result)}")
                        layer_results['method_results'][method_name] = {
                            'success': False,
                            'error': str(result)
                        }
        
        # Calculate layer success rate
        self.calculate_layer_success_rate(layer_results)
        
        return layer_results
    
    async def execute_method_batch(self, engine, method_name: str, urls: List[str]) -> Dict[str, Any]:
        """Execute a single method on a batch of URLs"""
        try:
            results = await engine.process_batch(urls)
            
            successful_count = sum(1 for result in results if result.get('success', False))
            
            return {
                'method': method_name,
                'total_urls': len(urls),
                'successful_urls': successful_count,
                'success_rate': successful_count / len(urls) if urls else 0.0,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Batch execution failed for {method_name}: {str(e)}")
            return {
                'method': method_name,
                'success': False,
                'error': str(e)
            }
    
    def filter_unsuccessful_urls(self, url_metadata_pairs: List[tuple], layer_results: Dict[str, Any]) -> List[tuple]:
        """Filter out URLs that achieved success in this layer"""
        if not layer_results.get('method_results'):
            return url_metadata_pairs
        
        successful_urls = set()
        
        # Collect successful URLs from all methods in the layer
        for method_result in layer_results['method_results'].values():
            if 'results' in method_result:
                for result in method_result['results']:
                    if result.get('success', False):
                        successful_urls.add(result.get('url'))
        
        # Return only URLs that weren't successful
        remaining = [pair for pair in url_metadata_pairs if pair[0] not in successful_urls]
        
        self.logger.info(f"Layer filtered out {len(successful_urls)} successful URLs, {len(remaining)} remaining")
        
        return remaining
    
    def calculate_layer_success_rate(self, layer_results: Dict[str, Any]):
        """Calculate success rate for a layer"""
        method_results = layer_results.get('method_results', {})
        
        if not method_results:
            layer_results['success_rate'] = 0.0
            return
        
        # Average success rate across all methods
        success_rates = [
            result.get('success_rate', 0.0) 
            for result in method_results.values() 
            if isinstance(result, dict) and 'success_rate' in result
        ]
        
        if success_rates:
            layer_results['success_rate'] = sum(success_rates) / len(success_rates)
        else:
            layer_results['success_rate'] = 0.0
    
    def calculate_overall_results(self, strategy_results: Dict[str, Any], original_urls: List[str]):
        """Calculate overall strategy results"""
        all_successful_urls = set()
        
        # Collect successful URLs from all layers
        for layer_result in strategy_results['layer_results'].values():
            method_results = layer_result.get('method_results', {})
            for method_result in method_results.values():
                if 'results' in method_result:
                    for result in method_result['results']:
                        if result.get('success', False):
                            all_successful_urls.add(result.get('url'))
        
        strategy_results['successful_urls'] = list(all_successful_urls)
        strategy_results['failed_urls'] = [
            url for url in original_urls if url not in all_successful_urls
        ]
        strategy_results['overall_success_rate'] = len(all_successful_urls) / len(original_urls) if original_urls else 0.0


class EnhancedBacklinkIndexingCoordinator:
    """Enhanced coordinator with comprehensive indexing capabilities"""
    
    def __init__(self, config: IndexingConfig):
        self.config = config
        self.setup_logging()
        
        # Initialize core components
        self.browser_manager = StealthBrowserManager(config)
        self.proxy_rotator = ProxyRotator(config)
        self.user_agent_rotator = UserAgentRotator(config)
        self.stealth_features = StealthFeatures(config)
        
        # Initialize indexing engines
        self.social_bookmarking_engine = SocialBookmarkingEngine(config, self.browser_manager)
        self.rss_distribution_engine = RSSDistributionEngine(config, self.browser_manager)
        self.web2_posting_engine = Web2PostingEngine(config, self.browser_manager)
        self.forum_commenting_engine = ForumCommentingEngine(config, self.browser_manager)
        self.directory_submission_engine = DirectorySubmissionEngine(config, self.browser_manager)
        self.social_signals_engine = SocialSignalEngine(config, self.browser_manager)
        
        # Initialize monitoring components
        self.serp_checker = SERPChecker(config)
        self.success_tracker = SuccessTracker(config)
        
        # Initialize strategy coordinator
        self.multi_layer_strategy = MultiLayerIndexingStrategy(self)
        
        # Performance tracking
        self.session_stats = {
            'urls_processed': 0,
            'successful_indexing': 0,
            'failed_indexing': 0,
            'session_start': datetime.now(),
            'methods_used': set()
        }
    
    def setup_logging(self):
        """Configure logging for the coordinator"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backlink_indexer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"{__name__}.EnhancedCoordinator")
    
    async def process_url_collection(self, urls: List[str], metadata_list: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a collection of URLs through the comprehensive indexing pipeline"""
        start_time = datetime.now()
        self.logger.info(f"Starting comprehensive indexing for {len(urls)} URLs")
        
        # Validate URLs
        valid_urls = []
        valid_metadata = []
        
        metadata_list = metadata_list or [{}] * len(urls)
        
        for i, url in enumerate(urls):
            try:
                if await self.validate_url(url):
                    valid_urls.append(url)
                    valid_metadata.append(metadata_list[i] if i < len(metadata_list) else {})
                else:
                    self.logger.warning(f"Invalid URL skipped: {url}")
            except Exception as e:
                self.logger.error(f"URL validation failed for {url}: {str(e)}")
        
        if not valid_urls:
            return {
                'success': False,
                'error': 'No valid URLs to process',
                'timestamp': datetime.now().isoformat()
            }
        
        # Execute multi-layer indexing strategy
        strategy_results = await self.multi_layer_strategy.execute_layered_strategy(
            valid_urls, valid_metadata
        )
        
        # Record attempts in success tracker
        await self.record_indexing_attempts(strategy_results)
        
        # Optional: Verify indexing through SERP checking
        verification_results = None
        if len(valid_urls) <= 10:  # Only for small batches to avoid rate limiting
            try:
                verification_results = await self.verify_indexing_success(
                    strategy_results['successful_urls'][:5]  # Check top 5 successful URLs
                )
            except Exception as e:
                self.logger.warning(f"Verification failed: {str(e)}")
        
        # Update session stats
        self.update_session_stats(strategy_results)
        
        # Compile final results
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        final_results = {
            'success': True,
            'overall_success_rate': strategy_results['overall_success_rate'],
            'urls_processed': len(valid_urls),
            'successful_urls': len(strategy_results['successful_urls']),
            'failed_urls': len(strategy_results['failed_urls']),
            'processing_time_seconds': processing_time,
            'layer_results': strategy_results['layer_results'],
            'verification_results': verification_results,
            'session_stats': self.session_stats.copy(),
            'timestamp': end_time.isoformat()
        }
        
        self.logger.info(f"Indexing completed: {final_results['overall_success_rate']:.2%} success rate")
        
        return final_results
    
    async def validate_url(self, url: str) -> bool:
        """Validate URL format and accessibility"""
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            if not parsed.netloc or parsed.scheme not in ['http', 'https']:
                return False
            
            # Additional validation could be added here
            return True
            
        except Exception:
            return False
    
    async def record_indexing_attempts(self, strategy_results: Dict[str, Any]):
        """Record all indexing attempts in the success tracker"""
        try:
            for layer_name, layer_result in strategy_results['layer_results'].items():
                method_results = layer_result.get('method_results', {})
                
                for method_name, method_result in method_results.items():
                    if 'results' in method_result:
                        for result in method_result['results']:
                            # Determine platform
                            platform = result.get('platform', 'unknown')
                            if 'platform_results' in result:
                                # For methods with multiple platforms
                                for platform_result in result['platform_results']:
                                    platform_name = platform_result.get('platform', 'unknown')
                                    success = platform_result.get('success', False)
                                    
                                    attempt = IndexingAttempt(
                                        url=result.get('url', ''),
                                        method=method_name,
                                        platform=platform_name,
                                        success=success,
                                        timestamp=datetime.now(),
                                        error_message=platform_result.get('error', '')
                                    )
                                    
                                    await self.success_tracker.record_attempt(attempt)
                            else:
                                # Single platform result
                                attempt = IndexingAttempt(
                                    url=result.get('url', ''),
                                    method=method_name,
                                    platform=platform,
                                    success=result.get('success', False),
                                    timestamp=datetime.now(),
                                    error_message=result.get('error', '')
                                )
                                
                                await self.success_tracker.record_attempt(attempt)
        
        except Exception as e:
            self.logger.error(f"Failed to record attempts: {str(e)}")
    
    async def verify_indexing_success(self, urls: List[str]) -> Dict[str, Any]:
        """Verify indexing success through SERP checking"""
        try:
            verification_results = await self.serp_checker.batch_check_indexing(urls)
            
            # Calculate verification stats
            indexed_count = sum(1 for result in verification_results if result.get('indexing_score', 0) > 0)
            
            return {
                'urls_checked': len(urls),
                'indexed_count': indexed_count,
                'verification_rate': indexed_count / len(urls) if urls else 0.0,
                'detailed_results': verification_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Indexing verification failed: {str(e)}")
            return {'error': str(e)}
    
    def update_session_stats(self, strategy_results: Dict[str, Any]):
        """Update session statistics"""
        self.session_stats['urls_processed'] += strategy_results['urls_processed']
        self.session_stats['successful_indexing'] += len(strategy_results['successful_urls'])
        self.session_stats['failed_indexing'] += len(strategy_results['failed_urls'])
        
        # Track methods used
        for layer_result in strategy_results['layer_results'].values():
            self.session_stats['methods_used'].update(layer_result.get('methods_used', []))
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the indexing system"""
        try:
            # Get performance metrics for each method
            method_performance = {}
            methods = ['social_bookmarking', 'rss_distribution', 'web2_posting', 
                      'forum_commenting', 'directory_submission', 'social_signals']
            
            for method in methods:
                try:
                    performance = await self.success_tracker.get_method_performance(method)
                    method_performance[method] = {
                        'success_rate': performance.success_rate,
                        'total_attempts': performance.total_attempts,
                        'last_24h_success_rate': performance.last_24h_success_rate
                    }
                except Exception as e:
                    self.logger.debug(f"Could not get stats for {method}: {str(e)}")
            
            # Get overall performance
            overall_performance = await self.success_tracker.get_overall_performance()
            
            # System health indicators
            session_duration = (datetime.now() - self.session_stats['session_start']).total_seconds()
            
            return {
                'session_stats': {
                    **self.session_stats,
                    'methods_used': list(self.session_stats['methods_used']),
                    'session_duration_seconds': session_duration
                },
                'method_performance': method_performance,
                'overall_performance': overall_performance,
                'system_health': {
                    'proxy_pool_size': len(self.config.proxy_pool),
                    'browser_pool_active': True,  # Simplified check
                    'success_tracker_active': True
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get comprehensive stats: {str(e)}")
            return {'error': str(e)}
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations"""
        try:
            # Get recent performance data
            overall_performance = await self.success_tracker.get_overall_performance(days=7)
            
            optimizations = {
                'recommended_actions': [],
                'method_adjustments': {},
                'configuration_changes': {},
                'performance_insights': {}
            }
            
            # Analyze method performance
            if 'method_breakdown' in overall_performance:
                for method_data in overall_performance['method_breakdown']:
                    method = method_data['method']
                    success_rate = method_data['success_rate']
                    
                    if success_rate < 0.3:
                        optimizations['recommended_actions'].append(
                            f"Review {method} configuration - low success rate ({success_rate:.1%})"
                        )
                        optimizations['method_adjustments'][method] = 'reduce_priority'
                    elif success_rate > 0.8:
                        optimizations['method_adjustments'][method] = 'increase_allocation'
            
            # Configuration recommendations
            if self.session_stats['urls_processed'] > 100:
                avg_success = self.session_stats['successful_indexing'] / self.session_stats['urls_processed']
                if avg_success < 0.5:
                    optimizations['configuration_changes']['increase_retry_attempts'] = True
                    optimizations['configuration_changes']['add_more_platforms'] = True
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Performance optimization analysis failed: {str(e)}")
            return {'error': str(e)}