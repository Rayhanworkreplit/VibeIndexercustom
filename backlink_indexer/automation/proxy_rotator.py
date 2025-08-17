"""
Proxy rotation system for enhanced anonymity
"""

import random
import time
import logging
from typing import List, Optional
import requests
from concurrent.futures import ThreadPoolExecutor


class ProxyRotator:
    """Advanced proxy rotation and management system"""
    
    def __init__(self, config):
        self.config = config
        self.proxy_pool = config.proxy_pool.copy()
        self.working_proxies = []
        self.failed_proxies = []
        self.current_index = 0
        self.rotation_counter = 0
        self.last_validation = 0
        self.setup_logging()
        
        # Initialize proxy validation
        if self.proxy_pool:
            self.validate_proxy_pool()
    
    def setup_logging(self):
        """Configure logging for proxy operations"""
        self.logger = logging.getLogger(f"{__name__}.ProxyRotator")
    
    def validate_proxy_pool(self):
        """Validate all proxies in the pool asynchronously"""
        self.logger.info(f"Validating {len(self.proxy_pool)} proxies...")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Test each proxy
            results = list(executor.map(self._test_single_proxy, self.proxy_pool))
            
        # Separate working and failed proxies
        for proxy, is_working in zip(self.proxy_pool, results):
            if is_working:
                self.working_proxies.append(proxy)
            else:
                self.failed_proxies.append(proxy)
        
        self.logger.info(f"Proxy validation complete: {len(self.working_proxies)} working, {len(self.failed_proxies)} failed")
        
        # Update the proxy pool to only include working proxies
        self.proxy_pool = self.working_proxies.copy()
    
    def _test_single_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """Test a single proxy for connectivity"""
        try:
            # Parse proxy format (supports http, https, socks5)
            if '://' not in proxy:
                proxy = f'http://{proxy}'
            
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            # Test with a reliable endpoint
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyTest/1.0)'}
            )
            
            # Verify response and check if IP is different
            if response.status_code == 200:
                data = response.json()
                proxy_ip = data.get('origin', '').split(',')[0].strip()
                return bool(proxy_ip)
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Proxy {proxy} failed test: {str(e)}")
            return False
    
    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation"""
        if not self.proxy_pool:
            return None
        
        # Check if we need to rotate based on interval
        if self.rotation_counter >= self.config.proxy_rotation_interval:
            self.rotation_counter = 0
            self.current_index = (self.current_index + 1) % len(self.proxy_pool)
        
        self.rotation_counter += 1
        proxy = self.proxy_pool[self.current_index]
        
        # Re-validate proxy pool periodically (every hour)
        current_time = time.time()
        if current_time - self.last_validation > 3600:  # 1 hour
            self.last_validation = current_time
            self.validate_proxy_pool()
        
        return proxy
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed and remove from active pool"""
        if proxy in self.proxy_pool:
            self.proxy_pool.remove(proxy)
            self.failed_proxies.append(proxy)
            
            # Adjust current index if needed
            if self.current_index >= len(self.proxy_pool) and self.proxy_pool:
                self.current_index = 0
            
            self.logger.warning(f"Marked proxy as failed: {proxy}")
    
    def add_proxy(self, proxy: str):
        """Add a new proxy to the pool after validation"""
        if self._test_single_proxy(proxy):
            self.proxy_pool.append(proxy)
            self.working_proxies.append(proxy)
            self.logger.info(f"Added working proxy: {proxy}")
        else:
            self.failed_proxies.append(proxy)
            self.logger.warning(f"Failed to add proxy (not working): {proxy}")
    
    def get_proxy_stats(self) -> dict:
        """Get statistics about proxy pool"""
        return {
            'total_proxies': len(self.proxy_pool),
            'working_proxies': len(self.working_proxies),
            'failed_proxies': len(self.failed_proxies),
            'current_proxy': self.proxy_pool[self.current_index] if self.proxy_pool else None,
            'rotation_counter': self.rotation_counter,
            'last_validation': self.last_validation
        }
    
    def refresh_failed_proxies(self):
        """Re-test failed proxies and move working ones back to active pool"""
        if not self.failed_proxies:
            return
        
        self.logger.info(f"Re-testing {len(self.failed_proxies)} failed proxies...")
        
        recovered_proxies = []
        still_failed = []
        
        for proxy in self.failed_proxies:
            if self._test_single_proxy(proxy):
                recovered_proxies.append(proxy)
                self.proxy_pool.append(proxy)
            else:
                still_failed.append(proxy)
        
        self.failed_proxies = still_failed
        
        if recovered_proxies:
            self.logger.info(f"Recovered {len(recovered_proxies)} proxies")


class ResidentialProxyManager(ProxyRotator):
    """Enhanced proxy manager for residential proxy services"""
    
    def __init__(self, config):
        super().__init__(config)
        self.sticky_session_duration = 600  # 10 minutes
        self.session_start_time = {}
        
    def get_sticky_session_proxy(self, session_id: str) -> Optional[str]:
        """Get a proxy with sticky session for consistency"""
        current_time = time.time()
        
        # Check if session needs refresh
        if (session_id in self.session_start_time and 
            current_time - self.session_start_time[session_id] > self.sticky_session_duration):
            # Session expired, get new proxy
            del self.session_start_time[session_id]
        
        if session_id not in self.session_start_time:
            # New session, assign proxy
            proxy = self.get_next_proxy()
            if proxy:
                self.session_start_time[session_id] = current_time
                return proxy
        
        # Return existing session proxy
        return self.proxy_pool[self.current_index] if self.proxy_pool else None


class GeoTargetedProxyManager(ProxyRotator):
    """Proxy manager with geographical targeting capabilities"""
    
    def __init__(self, config):
        super().__init__(config)
        self.geo_proxies = {
            'US': [],
            'UK': [],
            'CA': [],
            'AU': [],
            'DE': [],
            'Global': self.proxy_pool.copy()
        }
        self.classify_proxies_by_geo()
    
    def classify_proxies_by_geo(self):
        """Classify proxies by geographical location (basic implementation)"""
        # This is a simplified implementation
        # In production, you'd use a GeoIP service to classify proxies
        
        for proxy in self.proxy_pool:
            # Extract IP and classify (simplified)
            # In real implementation, use GeoIP lookup
            self.geo_proxies['Global'].append(proxy)
    
    def get_geo_proxy(self, country_code: str = 'Global') -> Optional[str]:
        """Get a proxy from specific geographical region"""
        if country_code in self.geo_proxies and self.geo_proxies[country_code]:
            return random.choice(self.geo_proxies[country_code])
        
        # Fallback to global pool
        return self.get_next_proxy()