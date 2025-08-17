"""
Main coordinator for the backlink indexing system
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .config import IndexingConfig, URLRecord, EXPECTED_SUCCESS_RATES
from ..automation.browser_manager import StealthBrowserManager
from ..indexing_methods.social_bookmarking import SocialBookmarkingEngine
from ..indexing_methods.rss_distribution import RSSDistributionEngine
from ..indexing_methods.web2_posting import Web2PostingEngine


class BacklinkIndexingCoordinator:
    """
    Main coordinator that orchestrates all indexing methods
    following the "Steal Like an Artist" multi-method approach
    """
    
    def __init__(self, config: IndexingConfig):
        self.config = config
        self.browser_manager = StealthBrowserManager(config)
        
        # Initialize indexing engines
        self.primary_methods = []
        self.secondary_methods = []
        
        self._setup_logging()
        self._setup_indexing_methods()
        
        # Statistics tracking
        self.stats = {
            'total_urls_processed': 0,
            'successful_urls': 0,
            'failed_urls': 0,
            'methods_performance': {}
        }
    
    def _setup_logging(self):
        """Configure logging for the coordinator"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backlink_indexer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"{__name__}.Coordinator")
    
    def _setup_indexing_methods(self):
        """Initialize all enabled indexing methods"""
        
        # Primary methods (highest success rates)
        if self.config.social_bookmarking_enabled:
            self.primary_methods.append(
                SocialBookmarkingEngine(self.config, self.browser_manager)
            )
        
        if self.config.rss_distribution_enabled:
            self.primary_methods.append(
                RSSDistributionEngine(self.config, self.browser_manager)
            )
        
        if self.config.web2_posting_enabled:
            self.primary_methods.append(
                Web2PostingEngine(self.config, self.browser_manager)
            )
        
        # Secondary methods will be added here as we implement them
        # if self.config.forum_commenting_enabled:
        #     self.secondary_methods.append(ForumCommentingEngine(...))
        
        self.logger.info(f"Initialized {len(self.primary_methods)} primary methods "
                        f"and {len(self.secondary_methods)} secondary methods")
    
    async def process_url_collection(self, urls: List[str], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a collection of URLs using multi-method approach
        Returns comprehensive results with success rates and statistics
        """
        self.logger.info(f"Starting processing of {len(urls)} URLs")
        
        url_records = [URLRecord(url=url) for url in urls]
        
        # Phase 1: Execute primary methods in parallel
        primary_results = await self._execute_primary_methods(url_records)
        
        # Phase 2: Use secondary methods for failed URLs
        failed_records = [record for record in url_records if record.success_score < self.config.success_threshold]
        secondary_results = await self._execute_secondary_methods(failed_records)
        
        # Phase 3: Compile final results
        final_results = self._compile_final_results(url_records)
        
        # Update statistics
        self._update_statistics(url_records)
        
        self.logger.info(f"Processing completed. Success rate: {final_results['overall_success_rate']:.2%}")
        
        return final_results
    
    async def _execute_primary_methods(self, url_records: List[URLRecord]) -> Dict[str, Any]:
        """Execute all primary indexing methods in parallel"""
        
        if not self.primary_methods:
            self.logger.warning("No primary methods enabled")
            return {}
        
        self.logger.info(f"Executing {len(self.primary_methods)} primary methods")
        
        # Execute all primary methods concurrently
        method_tasks = []
        for method in self.primary_methods:
            urls = [record.url for record in url_records]
            task = method.process_batch(urls)
            method_tasks.append(task)
        
        # Wait for all methods to complete
        method_results = await asyncio.gather(*method_tasks, return_exceptions=True)
        
        # Update URL records with results
        for method_idx, results in enumerate(method_results):
            if isinstance(results, Exception):
                self.logger.error(f"Primary method {method_idx} failed: {results}")
                continue
            
            method_name = self.primary_methods[method_idx].__class__.__name__
            self._update_records_with_results(url_records, results, method_name)
        
        return {'primary_methods_completed': len(self.primary_methods)}
    
    async def _execute_secondary_methods(self, failed_records: List[URLRecord]) -> Dict[str, Any]:
        """Execute secondary methods on URLs that failed primary methods"""
        
        if not self.secondary_methods or not failed_records:
            return {}
        
        self.logger.info(f"Executing secondary methods on {len(failed_records)} failed URLs")
        
        # Execute secondary methods
        method_tasks = []
        for method in self.secondary_methods:
            urls = [record.url for record in failed_records]
            task = method.process_batch(urls)
            method_tasks.append(task)
        
        method_results = await asyncio.gather(*method_tasks, return_exceptions=True)
        
        # Update records with secondary results
        for method_idx, results in enumerate(method_results):
            if isinstance(results, Exception):
                self.logger.error(f"Secondary method {method_idx} failed: {results}")
                continue
            
            method_name = self.secondary_methods[method_idx].__class__.__name__
            self._update_records_with_results(failed_records, results, method_name)
        
        return {'secondary_methods_completed': len(self.secondary_methods)}
    
    def _update_records_with_results(self, url_records: List[URLRecord], 
                                   method_results: List[Dict], method_name: str):
        """Update URL records with results from a specific method"""
        
        for record in url_records:
            # Find the result for this URL
            url_result = next((r for r in method_results if r['url'] == record.url), None)
            
            if url_result:
                record.methods_attempted.append(method_name)
                
                if url_result.get('success', False):
                    record.methods_successful.append(method_name)
                    record.success_score += EXPECTED_SUCCESS_RATES.get(
                        method_name.lower().replace('engine', ''), 0.1
                    )
                else:
                    error_msg = url_result.get('error', 'Unknown error')
                    record.error_messages.append(f"{method_name}: {error_msg}")
                
                record.attempts += 1
                record.last_attempt = datetime.now().isoformat()
                
                # Update status based on success score
                if record.success_score >= self.config.success_threshold:
                    record.status = "success"
                    record.indexed_date = datetime.now().isoformat()
                elif record.success_score > 0:
                    record.status = "partial_success"
                else:
                    record.status = "failed"
    
    def _compile_final_results(self, url_records: List[URLRecord]) -> Dict[str, Any]:
        """Compile final results summary"""
        
        total_urls = len(url_records)
        successful_urls = len([r for r in url_records if r.status == "success"])
        partial_success = len([r for r in url_records if r.status == "partial_success"])
        failed_urls = len([r for r in url_records if r.status == "failed"])
        
        # Method-specific performance
        method_performance = {}
        for method in self.primary_methods + self.secondary_methods:
            stats = method.get_performance_stats()
            method_performance[stats['method']] = {
                'success_rate': stats['success_rate'],
                'total_attempts': stats['total_attempts'],
                'successful_attempts': stats['successful_attempts']
            }
        
        return {
            'total_urls': total_urls,
            'successful_urls': successful_urls,
            'partial_success_urls': partial_success,
            'failed_urls': failed_urls,
            'overall_success_rate': (successful_urls + partial_success) / total_urls if total_urls > 0 else 0,
            'method_performance': method_performance,
            'url_records': [record.__dict__ for record in url_records],
            'processing_timestamp': datetime.now().isoformat()
        }
    
    def _update_statistics(self, url_records: List[URLRecord]):
        """Update internal statistics"""
        
        self.stats['total_urls_processed'] += len(url_records)
        self.stats['successful_urls'] += len([r for r in url_records if r.status == "success"])
        self.stats['failed_urls'] += len([r for r in url_records if r.status == "failed"])
        
        # Update method performance stats
        for method in self.primary_methods + self.secondary_methods:
            method_name = method.__class__.__name__
            method_stats = method.get_performance_stats()
            self.stats['methods_performance'][method_name] = method_stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        
        return {
            'overall_stats': self.stats,
            'expected_vs_actual': {
                method_name: {
                    'expected_success_rate': EXPECTED_SUCCESS_RATES.get(
                        method_name.lower().replace('engine', ''), 0.0
                    ),
                    'actual_success_rate': self.stats['methods_performance'].get(
                        method_name, {}
                    ).get('success_rate', 0.0)
                }
                for method_name in self.stats['methods_performance'].keys()
            },
            'configuration': self.config.__dict__,
            'timestamp': datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Cleanup resources"""
        self.logger.info("Shutting down backlink indexing coordinator")
        
        # Close browser manager resources
        await self.browser_manager.shutdown()
        
        # Log final statistics
        summary = self.get_performance_summary()
        self.logger.info(f"Final performance summary: {summary}")