"""
Abstract base class for all indexing methods
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class IndexingMethodBase(ABC):
    """Abstract base class for all indexing methods"""
    
    def __init__(self, config, browser_manager):
        self.config = config
        self.browser_manager = browser_manager
        self.success_rate = 0.0
        self.total_attempts = 0
        self.successful_attempts = 0
        self.setup_logging()
    
    def setup_logging(self):
        """Set up method-specific logging"""
        method_name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{method_name}")
    
    @abstractmethod
    async def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a single URL using this indexing method"""
        pass
    
    async def process_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Process a batch of URLs"""
        results = []
        
        for url in urls:
            try:
                result = await self.process_url(url)
                results.append(result)
                self.update_success_metrics(result['success'])
                
                # Human-like delay between URLs
                await self.browser_manager.human_like_delay()
                
            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {str(e)}")
                results.append({
                    'url': url,
                    'success': False,
                    'error': str(e),
                    'method': self.__class__.__name__,
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def update_success_metrics(self, success: bool):
        """Update success rate metrics"""
        self.total_attempts += 1
        if success:
            self.successful_attempts += 1
        self.success_rate = self.successful_attempts / self.total_attempts
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this method"""
        return {
            'method': self.__class__.__name__,
            'success_rate': self.success_rate,
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'last_updated': datetime.now().isoformat()
        }
    
    async def validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except Exception:
            return False
    
    def generate_content_variations(self, base_content: str, num_variations: int = 3) -> List[str]:
        """Generate content variations to avoid duplicate detection"""
        variations = [base_content]
        
        # Simple content variation techniques
        for i in range(num_variations - 1):
            variation = base_content
            
            # Add random prefixes/suffixes
            prefixes = ["Check out this:", "Found this interesting:", "Take a look at:", "Worth reading:"]
            suffixes = ["- great content!", "- recommended read", "- very useful", ""]
            
            if i == 0:
                variation = f"{prefixes[i % len(prefixes)]} {variation}"
            elif i == 1:
                variation = f"{variation} {suffixes[i % len(suffixes)]}"
            
            variations.append(variation)
        
        return variations