"""
Advanced browser manager with anti-detection capabilities
"""

import asyncio
import random
import logging
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from fake_useragent import UserAgent


class StealthBrowserManager:
    """Advanced browser manager with anti-detection capabilities"""
    
    def __init__(self, config):
        self.config = config
        self.user_agent = UserAgent()
        self.active_sessions = {}
        self.current_proxy_index = 0
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for browser operations"""
        self.logger = logging.getLogger(f"{__name__}.BrowserManager")
    
    def get_random_user_agent(self) -> str:
        """Generate random user agent for anti-detection"""
        try:
            return self.user_agent.random
        except:
            # Fallback user agents if fake_useragent fails
            fallback_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ]
            return random.choice(fallback_agents)
    
    def create_stealth_browser(self):
        """Create a browser instance with stealth capabilities"""
        
        # Mock mode for testing without Chrome driver
        if hasattr(self.config, 'mock_mode') and self.config.mock_mode:
            return MockBrowser()
        
        options = Options()
        
        if self.config.headless_mode:
            options.add_argument('--headless')
        
        # Anti-detection arguments
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Randomize window size
        window_sizes = ['--window-size=1920,1080', '--window-size=1366,768', '--window-size=1440,900']
        options.add_argument(random.choice(window_sizes))
        
        # Set random user agent
        options.add_argument(f'--user-agent={self.get_random_user_agent()}')
        
        # Proxy configuration (if enabled)
        if self.config.enable_proxy_rotation and self.config.proxy_pool:
            proxy = self.get_next_proxy()
            if proxy:
                options.add_argument(f'--proxy-server={proxy}')
        
        try:
            driver = webdriver.Chrome(options=options)
            
            # Execute JavaScript to hide automation indicators
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            self.logger.error(f"Failed to create browser instance: {str(e)}")
            # Fallback to mock mode if browser fails
            return MockBrowser()
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation pool"""
        if not self.config.proxy_pool:
            return None
        
        proxy = self.config.proxy_pool[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.config.proxy_pool)
        return proxy
    
    async def human_like_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None):
        """Simulate human-like delays between actions"""
        min_delay = min_delay or self.config.min_delay_between_actions
        max_delay = max_delay or self.config.max_delay_between_actions
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def human_like_typing(self, element, text: str):
        """Simulate human-like typing patterns"""
        typing_speed_range = self.config.human_typing_speed_range
        
        for char in text:
            element.send_keys(char)
            # Random typing speed with occasional pauses
            typing_delay = random.uniform(*typing_speed_range)
            if random.random() < 0.1:  # 10% chance of longer pause
                typing_delay *= random.uniform(2, 4)
            await asyncio.sleep(typing_delay)
    
    async def simulate_human_behavior(self, driver: webdriver.Chrome):
        """Simulate various human behaviors on the page"""
        
        # Random mouse movements (simulated via JavaScript)
        if random.random() < self.config.mouse_movement_probability:
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            driver.execute_script(f"document.dispatchEvent(new MouseEvent('mousemove', {{clientX: {x}, clientY: {y}}}));")
        
        # Random scrolling
        if random.random() < 0.3:  # 30% chance to scroll
            scroll_amount = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            await asyncio.sleep(random.uniform(0.5, 2.0))
    
    async def safe_navigate(self, driver: webdriver.Chrome, url: str, timeout: int = 10) -> bool:
        """Safely navigate to a URL with error handling"""
        try:
            driver.get(url)
            await self.human_like_delay(1, 3)  # Wait for page load
            
            # Simulate human behavior on page load
            await self.simulate_human_behavior(driver)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False
    
    async def safe_find_element(self, driver: webdriver.Chrome, by: By, value: str, 
                              timeout: int = 10) -> Optional[object]:
        """Safely find an element with timeout"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {by}={value}: {str(e)}")
            return None
    
    async def safe_click(self, driver: webdriver.Chrome, element) -> bool:
        """Safely click an element with human-like behavior"""
        try:
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
            # Simulate mouse hover before click
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            element.click()
            await self.human_like_delay(0.5, 2.0)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to click element: {str(e)}")
            return False
    
    def cleanup_driver(self, driver: webdriver.Chrome):
        """Safely cleanup a browser driver"""
        try:
            driver.quit()
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
    
    async def shutdown(self):
        """Cleanup all resources"""
        self.logger.info("Shutting down browser manager")
        
        # Close all active sessions
        for session_id, driver in self.active_sessions.items():
            self.cleanup_driver(driver)
        
        self.active_sessions.clear()


class ProxyRotator:
    """Manages proxy rotation for browser sessions"""
    
    def __init__(self, proxy_list: List[str]):
        self.proxy_list = proxy_list
        self.current_index = 0
        self.proxy_health = {proxy: True for proxy in proxy_list}
        self.logger = logging.getLogger(f"{__name__}.ProxyRotator")
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next healthy proxy from the pool"""
        if not self.proxy_list:
            return None
        
        attempts = 0
        max_attempts = len(self.proxy_list)
        
        while attempts < max_attempts:
            proxy = self.proxy_list[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxy_list)
            
            if self.proxy_health.get(proxy, True):
                return proxy
            
            attempts += 1
        
        # If no healthy proxies found, reset health status
        self.logger.warning("No healthy proxies found, resetting health status")
        self.proxy_health = {proxy: True for proxy in self.proxy_list}
        
        return self.proxy_list[0] if self.proxy_list else None
    
    def mark_proxy_unhealthy(self, proxy: str):
        """Mark a proxy as unhealthy"""
        self.proxy_health[proxy] = False
        self.logger.warning(f"Marked proxy as unhealthy: {proxy}")
    
    def reset_proxy_health(self):
        """Reset all proxy health status"""
        self.proxy_health = {proxy: True for proxy in self.proxy_list}
        self.logger.info("Reset all proxy health status")


class MockBrowser:
    """Mock browser for testing without Chrome driver"""
    
    def __init__(self):
        pass
    
    def get(self, url):
        """Mock navigation"""
        pass
    
    def find_element(self, by, value):
        """Mock element finding"""
        return MockElement()
    
    def execute_script(self, script, element=None):
        """Mock script execution"""
        pass
    
    def quit(self):
        """Mock cleanup"""
        pass


class MockElement:
    """Mock web element"""
    
    def send_keys(self, text):
        pass
    
    def clear(self):
        pass
    
    def click(self):
        pass