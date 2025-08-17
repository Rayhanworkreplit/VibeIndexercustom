"""
User-agent rotation and browser fingerprint randomization
"""

import random
import logging
from typing import List, Dict, Optional
from fake_useragent import UserAgent


class UserAgentRotator:
    """Advanced user-agent rotation and browser fingerprint management"""
    
    def __init__(self, config):
        self.config = config
        self.user_agent = UserAgent()
        self.rotation_counter = 0
        self.current_ua_index = 0
        self.setup_logging()
        
        # Pre-defined user agent pools for different browser types
        self.browser_pools = {
            'chrome': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ],
            'firefox': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0"
            ],
            'safari': [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
            ]
        }
        
        # Screen resolutions for fingerprint variation
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
            (1600, 900), (1280, 720), (1920, 1200), (2560, 1440),
            (1680, 1050), (1280, 1024), (1024, 768)
        ]
        
        # Language preferences
        self.languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-CA,en;q=0.9',
            'en-AU,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-US,en;q=0.9,fr;q=0.8'
        ]
        
        # Time zones
        self.timezones = [
            'America/New_York',
            'America/Los_Angeles', 
            'America/Chicago',
            'Europe/London',
            'Europe/Paris',
            'America/Toronto',
            'Australia/Sydney',
            'America/Denver'
        ]
    
    def setup_logging(self):
        """Configure logging for user agent operations"""
        self.logger = logging.getLogger(f"{__name__}.UserAgentRotator")
    
    def get_random_user_agent(self, browser_type: str = 'random') -> str:
        """Get a random user agent string"""
        try:
            # Check rotation interval
            if self.rotation_counter >= self.config.user_agent_rotation_interval:
                self.rotation_counter = 0
                self.current_ua_index = random.randint(0, 1000)  # Randomize selection
            
            self.rotation_counter += 1
            
            if browser_type == 'random':
                # Use fake_useragent library for maximum variety
                try:
                    return self.user_agent.random
                except:
                    # Fallback to predefined pools
                    browser_type = random.choice(['chrome', 'firefox', 'safari'])
            
            if browser_type in self.browser_pools:
                return random.choice(self.browser_pools[browser_type])
            
            # Ultimate fallback
            return self.browser_pools['chrome'][0]
            
        except Exception as e:
            self.logger.error(f"Error getting user agent: {str(e)}")
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def generate_browser_fingerprint(self) -> Dict[str, any]:
        """Generate a complete browser fingerprint for anti-detection"""
        user_agent = self.get_random_user_agent()
        resolution = random.choice(self.screen_resolutions)
        
        # Extract browser info from user agent
        browser_info = self._parse_user_agent(user_agent)
        
        fingerprint = {
            'user_agent': user_agent,
            'viewport': {
                'width': resolution[0],
                'height': resolution[1]
            },
            'screen': {
                'width': resolution[0],
                'height': resolution[1],
                'color_depth': random.choice([24, 32]),
                'pixel_ratio': random.choice([1, 1.25, 1.5, 2])
            },
            'language': random.choice(self.languages),
            'timezone': random.choice(self.timezones),
            'platform': browser_info['platform'],
            'browser': {
                'name': browser_info['browser'],
                'version': browser_info['version']
            },
            'webgl_vendor': self._get_webgl_vendor(browser_info['browser']),
            'webgl_renderer': self._get_webgl_renderer(),
            'hardware_concurrency': random.choice([2, 4, 6, 8, 12, 16]),
            'device_memory': random.choice([2, 4, 8, 16, 32]),
            'canvas_fingerprint': self._generate_canvas_fingerprint(),
            'audio_fingerprint': self._generate_audio_fingerprint()
        }
        
        return fingerprint
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string to extract browser info"""
        browser_info = {
            'browser': 'Chrome',
            'version': '120.0.0.0',
            'platform': 'Windows'
        }
        
        if 'Chrome' in user_agent:
            browser_info['browser'] = 'Chrome'
            # Extract Chrome version
            import re
            match = re.search(r'Chrome/(\d+\.\d+\.\d+\.\d+)', user_agent)
            if match:
                browser_info['version'] = match.group(1)
        elif 'Firefox' in user_agent:
            browser_info['browser'] = 'Firefox'
            match = re.search(r'Firefox/(\d+\.\d+)', user_agent)
            if match:
                browser_info['version'] = match.group(1)
        elif 'Safari' in user_agent:
            browser_info['browser'] = 'Safari'
            match = re.search(r'Version/(\d+\.\d+)', user_agent)
            if match:
                browser_info['version'] = match.group(1)
        
        # Extract platform
        if 'Windows' in user_agent:
            browser_info['platform'] = 'Windows'
        elif 'Macintosh' in user_agent or 'Mac OS X' in user_agent:
            browser_info['platform'] = 'macOS'
        elif 'Linux' in user_agent:
            browser_info['platform'] = 'Linux'
        elif 'iPhone' in user_agent:
            browser_info['platform'] = 'iOS'
        elif 'Android' in user_agent:
            browser_info['platform'] = 'Android'
        
        return browser_info
    
    def _get_webgl_vendor(self, browser: str) -> str:
        """Get appropriate WebGL vendor for browser"""
        vendors = {
            'Chrome': ['Google Inc.', 'Google Inc. (NVIDIA)', 'Google Inc. (Intel)', 'Google Inc. (AMD)'],
            'Firefox': ['Mozilla', 'Mozilla (NVIDIA)', 'Mozilla (Intel)', 'Mozilla (AMD)'],
            'Safari': ['Apple Inc.', 'Apple Inc. (Intel)', 'Apple Inc. (AMD)']
        }
        
        return random.choice(vendors.get(browser, vendors['Chrome']))
    
    def _get_webgl_renderer(self) -> str:
        """Get appropriate WebGL renderer"""
        renderers = [
            'ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'Intel Iris OpenGL Engine',
            'AMD Radeon Pro 560X OpenGL Engine',
            'NVIDIA GeForce GTX 1080 OpenGL Engine'
        ]
        
        return random.choice(renderers)
    
    def _generate_canvas_fingerprint(self) -> str:
        """Generate a unique canvas fingerprint"""
        # Simplified canvas fingerprint generation
        import hashlib
        
        # Create a pseudo-unique fingerprint based on timestamp and randomness
        fingerprint_data = f"{random.random()}_{random.randint(1000, 9999)}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    def _generate_audio_fingerprint(self) -> str:
        """Generate a unique audio context fingerprint"""
        # Simplified audio fingerprint generation
        import hashlib
        
        # Simulate audio context variations
        sample_rate = random.choice([44100, 48000])
        fingerprint_data = f"audio_{sample_rate}_{random.random()}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    def get_mobile_user_agent(self) -> str:
        """Get a mobile user agent string"""
        mobile_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]
        
        return random.choice(mobile_agents)
    
    def get_stats(self) -> Dict[str, any]:
        """Get user agent rotation statistics"""
        return {
            'rotation_counter': self.rotation_counter,
            'current_ua_index': self.current_ua_index,
            'rotation_interval': self.config.user_agent_rotation_interval,
            'available_browsers': list(self.browser_pools.keys()),
            'total_user_agents': sum(len(agents) for agents in self.browser_pools.values())
        }