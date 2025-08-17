"""
Advanced stealth and anti-detection measures
"""

import asyncio
import random
import time
import logging
from typing import Dict, List, Optional, Any
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class StealthFeatures:
    """Advanced anti-detection and human behavior simulation"""
    
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        
        # Human behavior parameters
        self.typing_speeds = {
            'slow': (0.1, 0.3),
            'normal': (0.05, 0.15),
            'fast': (0.02, 0.08)
        }
        
        # Mouse movement patterns
        self.mouse_patterns = ['linear', 'curved', 'random', 'natural']
        
        # Behavioral timing patterns
        self.pause_patterns = {
            'thinking': (1.0, 3.0),
            'reading': (2.0, 5.0),
            'typing': (0.1, 0.5),
            'clicking': (0.2, 0.8)
        }
    
    def setup_logging(self):
        """Configure logging for stealth operations"""
        self.logger = logging.getLogger(f"{__name__}.StealthFeatures")
    
    async def human_like_delay(self, action_type: str = 'normal', variance: float = 0.3):
        """Generate human-like delays with natural variance"""
        base_delays = {
            'normal': (2.0, 5.0),
            'fast': (0.5, 2.0),
            'slow': (3.0, 8.0),
            'thinking': (1.0, 3.0),
            'reading': (2.0, 6.0)
        }
        
        min_delay, max_delay = base_delays.get(action_type, base_delays['normal'])
        
        # Add natural variance
        delay = random.uniform(min_delay, max_delay)
        variance_factor = random.uniform(1 - variance, 1 + variance)
        final_delay = delay * variance_factor
        
        await asyncio.sleep(final_delay)
    
    async def simulate_human_typing(self, element, text: str, typing_style: str = 'normal'):
        """Simulate realistic human typing patterns"""
        if not text:
            return
        
        speed_range = self.typing_speeds.get(typing_style, self.typing_speeds['normal'])
        
        for i, char in enumerate(text):
            # Variable typing speed
            char_delay = random.uniform(*speed_range)
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.1:  # 10% chance
                char_delay *= random.uniform(2, 4)
            
            # Occasional typos and corrections
            if random.random() < 0.05 and i > 0:  # 5% chance of typo
                # Type wrong character
                wrong_char = chr(ord(char) + random.randint(-2, 2))
                element.send_keys(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Backspace and correct
                element.send_keys(Keys.BACKSPACE)
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Type the actual character
            element.send_keys(char)
            await asyncio.sleep(char_delay)
            
            # Occasional pauses within words
            if char == ' ' and random.random() < 0.3:
                await asyncio.sleep(random.uniform(0.2, 1.0))
    
    async def simulate_mouse_movement(self, driver, target_element=None):
        """Simulate natural mouse movements"""
        try:
            actions = ActionChains(driver)
            
            if target_element:
                # Move to target with natural curve
                await self._move_to_element_naturally(actions, target_element)
            else:
                # Random mouse movement
                await self._random_mouse_movement(actions, driver)
            
            actions.perform()
            
        except Exception as e:
            self.logger.debug(f"Mouse movement simulation failed: {str(e)}")
    
    async def _move_to_element_naturally(self, actions, element):
        """Move mouse to element with natural path"""
        try:
            # Get current mouse position (simplified)
            # In real implementation, you'd track actual mouse position
            
            # Add slight offset and curve to movement
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            
            # Move with slight pause
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            self.logger.debug(f"Natural mouse movement failed: {str(e)}")
    
    async def _random_mouse_movement(self, actions, driver):
        """Perform random mouse movements for realism"""
        try:
            # Get viewport size
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")
            
            # Random movement within viewport
            x = random.randint(50, viewport_width - 50)
            y = random.randint(50, viewport_height - 50)
            
            actions.move_by_offset(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
        except Exception as e:
            self.logger.debug(f"Random mouse movement failed: {str(e)}")
    
    async def simulate_reading_behavior(self, driver, element=None):
        """Simulate natural reading patterns with scrolling"""
        try:
            # Simulate reading by scrolling
            scroll_pause_time = random.uniform(1.0, 3.0)
            
            if element:
                # Scroll to element and read
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", element)
                await asyncio.sleep(scroll_pause_time)
            else:
                # Random scrolling behavior
                scroll_distance = random.randint(100, 500)
                driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                await asyncio.sleep(scroll_pause_time)
                
                # Occasional scroll back up
                if random.random() < 0.3:
                    scroll_back = random.randint(50, 200)
                    driver.execute_script(f"window.scrollBy(0, -{scroll_back});")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            self.logger.debug(f"Reading simulation failed: {str(e)}")
    
    async def simulate_form_interaction(self, driver, form_data: Dict[str, str]):
        """Simulate realistic form filling behavior"""
        try:
            for field_name, value in form_data.items():
                # Find form field
                field_selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"#{field_name}",
                    f".{field_name}"
                ]
                
                field_element = None
                for selector in field_selectors:
                    try:
                        field_element = driver.find_element("css selector", selector)
                        break
                    except:
                        continue
                
                if not field_element:
                    continue
                
                # Simulate clicking on field
                await self.simulate_mouse_movement(driver, field_element)
                await asyncio.sleep(random.uniform(0.2, 0.8))
                field_element.click()
                
                # Clear field if needed
                if field_element.get_attribute('value'):
                    field_element.clear()
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Human-like typing
                await self.simulate_human_typing(field_element, value)
                
                # Pause between fields
                await self.human_like_delay('thinking')
            
        except Exception as e:
            self.logger.error(f"Form interaction simulation failed: {str(e)}")
    
    def inject_anti_detection_scripts(self, driver):
        """Inject JavaScript to hide automation indicators"""
        scripts = [
            # Hide webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Override plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }))
            });
            """,
            
            # Override languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
            
            # Override permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            """,
            
            # Override chrome runtime
            "delete window.chrome.runtime.onConnect;",
            "delete window.chrome.runtime.onMessage;",
        ]
        
        for script in scripts:
            try:
                driver.execute_script(script)
            except Exception as e:
                self.logger.debug(f"Failed to inject script: {str(e)}")
    
    def randomize_viewport(self, driver):
        """Randomize browser viewport for fingerprint variation"""
        try:
            # Common viewport sizes
            viewports = [
                (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
                (1600, 900), (1280, 720), (1680, 1050)
            ]
            
            width, height = random.choice(viewports)
            
            # Add slight variance
            width += random.randint(-50, 50)
            height += random.randint(-50, 50)
            
            driver.set_window_size(width, height)
            
        except Exception as e:
            self.logger.debug(f"Viewport randomization failed: {str(e)}")
    
    async def simulate_tab_behavior(self, driver):
        """Simulate natural tab and window behavior"""
        try:
            # Occasionally open new tab and close it
            if random.random() < 0.1:  # 10% chance
                # Open new tab
                driver.execute_script("window.open('about:blank', '_blank');")
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Switch to new tab
                tabs = driver.window_handles
                if len(tabs) > 1:
                    driver.switch_to.window(tabs[-1])
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                    # Close tab and return to original
                    driver.close()
                    driver.switch_to.window(tabs[0])
            
        except Exception as e:
            self.logger.debug(f"Tab behavior simulation failed: {str(e)}")
    
    async def simulate_idle_time(self, min_idle: float = 5.0, max_idle: float = 30.0):
        """Simulate periods of user inactivity"""
        idle_time = random.uniform(min_idle, max_idle)
        self.logger.debug(f"Simulating idle time: {idle_time:.2f} seconds")
        await asyncio.sleep(idle_time)
    
    def get_behavioral_stats(self) -> Dict[str, Any]:
        """Get statistics about behavioral patterns"""
        return {
            'available_typing_styles': list(self.typing_speeds.keys()),
            'mouse_patterns': self.mouse_patterns,
            'pause_patterns': list(self.pause_patterns.keys()),
            'anti_detection_scripts': 5  # Number of scripts available
        }