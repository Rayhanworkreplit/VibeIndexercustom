"""
Advanced stealth browser implementation with comprehensive anti-detection
"""

import asyncio
import random
import time
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from ..models import BrowserFingerprint, ProxyConfig


class StealthBrowserManager:
    """
    Production-grade stealth browser manager with comprehensive anti-detection
    Includes Selenium Grid support, proxy rotation, fingerprint randomization
    """
    
    def __init__(self, config):
        self.config = config
        self.user_agent = UserAgent()
        self.active_sessions = {}
        self.current_proxy_index = 0
        self.fingerprint_pool = []
        self.proxy_pool = []
        self.setup_logging()
        self._initialize_fingerprints()
        self._initialize_proxy_pool()
        
    def setup_logging(self):
        """Configure logging for browser operations"""
        self.logger = logging.getLogger(f"{__name__}.StealthBrowser")
        
    def _initialize_fingerprints(self):
        """Pre-generate browser fingerprints for rotation"""
        viewports = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720),
            (1600, 900), (1024, 768), (1680, 1050), (1280, 1024), (1920, 1200)
        ]
        
        timezones = [
            "America/New_York", "America/Los_Angeles", "America/Chicago",
            "Europe/London", "Europe/Berlin", "Europe/Paris", "Asia/Tokyo",
            "Australia/Sydney", "America/Toronto", "Europe/Amsterdam"
        ]
        
        languages = ["en-US", "en-GB", "en-CA", "en-AU", "de-DE", "fr-FR", "es-ES", "it-IT"]
        platforms = ["Win32", "MacIntel", "Linux x86_64"]
        
        webgl_vendors = [
            "Google Inc. (Intel)", "Google Inc. (NVIDIA)", "Google Inc. (AMD)",
            "Google Inc. (Apple)", "Intel Inc.", "NVIDIA Corporation"
        ]
        
        webgl_renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "Intel Iris OpenGL Engine", "AMD Radeon Pro 560X OpenGL Engine"
        ]
        
        for _ in range(50):  # Generate 50 unique fingerprints
            viewport = random.choice(viewports)
            screen = (viewport[0] + random.randint(0, 200), viewport[1] + random.randint(0, 200))
            
            fingerprint = BrowserFingerprint(
                user_agent=self.user_agent.random,
                viewport_width=viewport[0],
                viewport_height=viewport[1],
                screen_width=screen[0],
                screen_height=screen[1],
                timezone=random.choice(timezones),
                language=random.choice(languages),
                platform=random.choice(platforms),
                webgl_vendor=random.choice(webgl_vendors),
                webgl_renderer=random.choice(webgl_renderers)
            )
            
            self.fingerprint_pool.append(fingerprint)
    
    def _initialize_proxy_pool(self):
        """Initialize proxy pool from configuration"""
        if hasattr(self.config, 'proxy_list') and self.config.proxy_list:
            for proxy_data in self.config.proxy_list:
                proxy = ProxyConfig(**proxy_data)
                self.proxy_pool.append(proxy)
    
    def get_random_fingerprint(self) -> BrowserFingerprint:
        """Get a random browser fingerprint"""
        return random.choice(self.fingerprint_pool) if self.fingerprint_pool else self._generate_basic_fingerprint()
    
    def _generate_basic_fingerprint(self) -> BrowserFingerprint:
        """Generate a basic fingerprint if pool is empty"""
        return BrowserFingerprint(
            user_agent=self.user_agent.random,
            viewport_width=1920,
            viewport_height=1080,
            screen_width=1920,
            screen_height=1080,
            timezone="America/New_York",
            language="en-US",
            platform="Win32",
            webgl_vendor="Google Inc.",
            webgl_renderer="ANGLE"
        )
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy from rotation pool"""
        if not self.proxy_pool:
            return None
            
        # Filter active proxies
        active_proxies = [p for p in self.proxy_pool if p.active]
        if not active_proxies:
            return None
        
        # Simple round-robin selection
        proxy = active_proxies[self.current_proxy_index % len(active_proxies)]
        self.current_proxy_index += 1
        
        return proxy
    
    def create_stealth_browser(self, session_id: Optional[str] = None) -> webdriver.Chrome:
        """Create a fully stealth browser instance with anti-detection features"""
        
        # Mock mode for testing
        if hasattr(self.config, 'mock_mode') and self.config.mock_mode:
            return MockBrowser()
        
        # Get random fingerprint
        fingerprint = self.get_random_fingerprint()
        
        # Create Chrome options
        options = uc.ChromeOptions()
        
        # Basic stealth options
        if self.config.headless_mode:
            options.add_argument('--headless=new')
        
        # Anti-detection arguments
        stealth_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions',
            '--disable-plugins-discovery',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--disable-web-security',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-client-side-phishing-detection',
            '--disable-hang-monitor',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-domain-reliability',
            '--disable-component-extensions-with-background-pages',
            '--no-first-run',
            '--no-default-browser-check',
            '--no-pings',
            '--password-store=basic',
            '--use-mock-keychain',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors-spki-list',
            '--ignore-certificate-errors-skip-list'
        ]
        
        for arg in stealth_args:
            options.add_argument(arg)
        
        # Set fingerprint-based configuration
        options.add_argument(f'--window-size={fingerprint.viewport_width},{fingerprint.viewport_height}')
        options.add_argument(f'--user-agent={fingerprint.user_agent}')
        options.add_argument(f'--lang={fingerprint.language}')
        
        # Proxy configuration
        proxy = self.get_next_proxy()
        if proxy and self.config.enable_proxy_rotation:
            options.add_argument(f'--proxy-server={proxy.proxy_url}')
            
        # Advanced Chrome preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Block images for faster loading
            },
            "profile.default_content_settings": {
                "popups": 0
            },
            "intl.accept_languages": fingerprint.language,
            "intl.charset_default": "UTF-8"
        }
        
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Create browser with undetected-chromedriver
            driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                driver_executable_path=None  # Auto-download driver
            )
            
            # Apply additional stealth scripts
            self._apply_stealth_scripts(driver, fingerprint)
            
            # Store session info
            if session_id:
                self.active_sessions[session_id] = {
                    'driver': driver,
                    'fingerprint': fingerprint,
                    'proxy': proxy,
                    'created_at': time.time()
                }
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to create stealth browser: {str(e)}")
            raise
    
    def _apply_stealth_scripts(self, driver: webdriver.Chrome, fingerprint: BrowserFingerprint):
        """Apply JavaScript-based stealth modifications"""
        
        # Override navigator properties
        stealth_script = f"""
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{fingerprint.platform}',
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['{fingerprint.language}'],
        }});
        
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [1, 2, 3, 4, 5],
        }});
        
        Object.defineProperty(screen, 'width', {{
            get: () => {fingerprint.screen_width},
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {fingerprint.screen_height},
        }});
        
        // Override WebGL fingerprinting
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type) {{
            if (type === 'webgl' || type === 'experimental-webgl') {{
                const context = getContext.apply(this, arguments);
                const getParameter = context.getParameter;
                
                context.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{fingerprint.webgl_vendor}';
                    }}
                    if (parameter === 37446) {{
                        return '{fingerprint.webgl_renderer}';
                    }}
                    return getParameter.apply(this, arguments);
                }};
                return context;
            }}
            return getContext.apply(this, arguments);
        }};
        
        // Override timezone
        Date.prototype.getTimezoneOffset = function() {{
            return -new Date().getTimezoneOffset();
        }};
        
        // Hide chrome runtime
        window.chrome = undefined;
        
        // Override permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        """
        
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_script
            })
        except Exception as e:
            self.logger.warning(f"Could not apply CDP stealth scripts: {str(e)}")
            # Fallback to regular execute_script
            try:
                driver.execute_script(stealth_script)
            except Exception as e2:
                self.logger.warning(f"Could not apply fallback stealth scripts: {str(e2)}")
    
    def human_like_typing(self, element, text: str, typing_speed: float = 0.1):
        """Type text with human-like patterns"""
        for char in text:
            element.send_keys(char)
            # Random typing delay
            time.sleep(random.uniform(typing_speed * 0.5, typing_speed * 1.5))
    
    def human_like_scroll(self, driver: webdriver.Chrome, scroll_distance: int = None):
        """Scroll with human-like patterns"""
        if scroll_distance is None:
            scroll_distance = random.randint(200, 800)
        
        # Gradual scrolling
        steps = random.randint(3, 8)
        step_size = scroll_distance // steps
        
        for _ in range(steps):
            driver.execute_script(f"window.scrollBy(0, {step_size});")
            time.sleep(random.uniform(0.1, 0.3))
    
    def random_mouse_movements(self, driver: webdriver.Chrome):
        """Perform random mouse movements"""
        try:
            actions = ActionChains(driver)
            
            # Get viewport size
            viewport_width = driver.execute_script("return window.innerWidth")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            # Random movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(0, viewport_width - 1)
                y = random.randint(0, viewport_height - 1)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.5, 1.5))
            
            actions.perform()
            
        except Exception as e:
            self.logger.debug(f"Random mouse movements failed: {str(e)}")
    
    def wait_with_human_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Wait with human-like random delay"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def close_session(self, session_id: str):
        """Close a browser session safely"""
        if session_id in self.active_sessions:
            try:
                driver = self.active_sessions[session_id]['driver']
                driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing session {session_id}: {str(e)}")
            finally:
                del self.active_sessions[session_id]
    
    def cleanup_all_sessions(self):
        """Clean up all active browser sessions"""
        for session_id in list(self.active_sessions.keys()):
            self.close_session(session_id)


class MockBrowser:
    """Mock browser for testing without Chrome driver"""
    
    def __init__(self):
        self.current_url = ""
        self.page_source = "<html><body>Mock browser for testing</body></html>"
        
    def get(self, url: str):
        self.current_url = url
        time.sleep(random.uniform(1, 3))  # Simulate page load time
        
    def find_element(self, by, value):
        return MockElement()
        
    def find_elements(self, by, value):
        return [MockElement() for _ in range(random.randint(1, 3))]
    
    def execute_script(self, script: str):
        return "mock_result"
    
    def execute_cdp_cmd(self, cmd: str, params: dict):
        return {"success": True}
    
    def quit(self):
        pass
    
    def close(self):
        pass


class MockElement:
    """Mock element for testing"""
    
    def click(self):
        time.sleep(random.uniform(0.1, 0.5))
        
    def send_keys(self, keys):
        time.sleep(len(str(keys)) * 0.1)
        
    def clear(self):
        time.sleep(0.1)
        
    @property
    def text(self):
        return "Mock element text"