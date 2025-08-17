"""
Social bookmarking automation engine
"""

import asyncio
import random
from typing import Dict, Any, List
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from datetime import datetime
from .base import IndexingMethodBase


class SocialBookmarkingEngine(IndexingMethodBase):
    """Automated social bookmarking for link indexing"""
    
    def __init__(self, config, browser_manager):
        super().__init__(config, browser_manager)
        self.platforms = {
            'reddit': {
                'url': 'https://www.reddit.com/submit',
                'enabled': True,
                'authority_score': 95,
                'selectors': {
                    'url_field': 'input[name="url"]',
                    'title_field': 'input[name="title"]',
                    'submit_button': 'button[type="submit"]'
                }
            },
            'digg': {
                'url': 'https://digg.com/submit',
                'enabled': True,
                'authority_score': 82,
                'selectors': {
                    'url_field': 'input[name="url"]',
                    'submit_button': '.submit-btn'
                }
            }
        }
        
        # Load platform configs from main config
        if hasattr(config, 'platform_configs'):
            for platform, platform_config in config.platform_configs.items():
                if platform in self.platforms:
                    self.platforms[platform].update(platform_config)
    
    async def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Submit URL to social bookmarking platforms"""
        
        if not await self.validate_url(url):
            return {
                'url': url,
                'method': 'social_bookmarking',
                'success': False,
                'error': 'Invalid URL format',
                'timestamp': datetime.now().isoformat()
            }
        
        results = []
        successful_submissions = 0
        
        for platform_name, platform_config in self.platforms.items():
            if not platform_config.get('enabled', True):
                continue
                
            try:
                result = await self.submit_to_platform(url, platform_name, platform_config, metadata)
                results.append(result)
                
                if result.get('success', False):
                    successful_submissions += 1
                
                # Rate limiting between platforms
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                self.logger.error(f"Failed to submit to {platform_name}: {str(e)}")
                results.append({
                    'platform': platform_name,
                    'success': False,
                    'error': str(e)
                })
        
        overall_success = successful_submissions > 0
        
        return {
            'url': url,
            'method': 'social_bookmarking',
            'success': overall_success,
            'successful_platforms': successful_submissions,
            'total_platforms': len([p for p in self.platforms.values() if p.get('enabled', True)]),
            'platform_results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def submit_to_platform(self, url: str, platform_name: str, 
                                platform_config: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Submit URL to a specific social bookmarking platform"""
        
        driver = None
        try:
            driver = self.browser_manager.create_stealth_browser()
            
            # Navigate to submission page
            success = await self.browser_manager.safe_navigate(driver, platform_config['url'])
            if not success:
                return {'platform': platform_name, 'success': False, 'error': 'Navigation failed'}
            
            # Handle platform-specific submission logic
            if platform_name == 'reddit':
                return await self._submit_to_reddit(driver, url, metadata)
            elif platform_name == 'digg':
                return await self._submit_to_digg(driver, url, metadata)
            else:
                return await self._generic_submission(driver, url, platform_config, metadata)
            
        except Exception as e:
            self.logger.error(f"Error submitting to {platform_name}: {str(e)}")
            return {'platform': platform_name, 'success': False, 'error': str(e)}
        
        finally:
            if driver:
                self.browser_manager.cleanup_driver(driver)
    
    async def _submit_to_reddit(self, driver, url: str, metadata: Dict = None) -> Dict[str, Any]:
        """Submit to Reddit with platform-specific logic"""
        
        try:
            # Check if we need to login (Reddit often requires this)
            # For demo purposes, we'll simulate the submission process
            
            # Find URL input field
            url_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'input[name="url"]'
            )
            
            if not url_field:
                return {'platform': 'reddit', 'success': False, 'error': 'URL field not found'}
            
            # Clear and enter URL
            url_field.clear()
            await self.browser_manager.human_like_typing(url_field, url)
            
            # Generate appropriate title
            title = self._generate_reddit_title(url, metadata)
            
            # Find title field
            title_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'input[name="title"]'
            )
            
            if title_field:
                title_field.clear()
                await self.browser_manager.human_like_typing(title_field, title)
            
            # Wait before submission
            await asyncio.sleep(random.uniform(2, 5))
            
            # Find and click submit button
            submit_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'button[type="submit"]'
            )
            
            if submit_button:
                success = await self.browser_manager.safe_click(driver, submit_button)
                
                if success:
                    # Wait for submission to complete
                    await asyncio.sleep(random.uniform(3, 7))
                    
                    return {
                        'platform': 'reddit',
                        'success': True,
                        'title_used': title,
                        'submission_time': datetime.now().isoformat()
                    }
            
            return {'platform': 'reddit', 'success': False, 'error': 'Submission failed'}
            
        except Exception as e:
            return {'platform': 'reddit', 'success': False, 'error': str(e)}
    
    async def _submit_to_digg(self, driver, url: str, metadata: Dict = None) -> Dict[str, Any]:
        """Submit to Digg with platform-specific logic"""
        
        try:
            # Find URL input field
            url_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'input[name="url"]'
            )
            
            if not url_field:
                return {'platform': 'digg', 'success': False, 'error': 'URL field not found'}
            
            # Enter URL
            url_field.clear()
            await self.browser_manager.human_like_typing(url_field, url)
            
            # Wait and submit
            await asyncio.sleep(random.uniform(2, 4))
            
            submit_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '.submit-btn'
            )
            
            if submit_button:
                success = await self.browser_manager.safe_click(driver, submit_button)
                
                if success:
                    await asyncio.sleep(random.uniform(3, 6))
                    return {
                        'platform': 'digg',
                        'success': True,
                        'submission_time': datetime.now().isoformat()
                    }
            
            return {'platform': 'digg', 'success': False, 'error': 'Submission failed'}
            
        except Exception as e:
            return {'platform': 'digg', 'success': False, 'error': str(e)}
    
    async def _generic_submission(self, driver, url: str, platform_config: Dict, 
                                metadata: Dict = None) -> Dict[str, Any]:
        """Generic submission logic for other platforms"""
        
        platform_name = platform_config.get('name', 'unknown')
        selectors = platform_config.get('selectors', {})
        
        try:
            # Find URL field
            url_selector = selectors.get('url_field', 'input[name="url"]')
            url_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, url_selector
            )
            
            if not url_field:
                return {'platform': platform_name, 'success': False, 'error': 'URL field not found'}
            
            # Enter URL
            url_field.clear()
            await self.browser_manager.human_like_typing(url_field, url)
            
            # Handle title if required
            title_selector = selectors.get('title_field')
            if title_selector:
                title_field = await self.browser_manager.safe_find_element(
                    driver, By.CSS_SELECTOR, title_selector
                )
                if title_field:
                    title = self._generate_generic_title(url, metadata)
                    title_field.clear()
                    await self.browser_manager.human_like_typing(title_field, title)
            
            # Submit
            await asyncio.sleep(random.uniform(2, 5))
            
            submit_selector = selectors.get('submit_button', 'button[type="submit"]')
            submit_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, submit_selector
            )
            
            if submit_button:
                success = await self.browser_manager.safe_click(driver, submit_button)
                
                if success:
                    await asyncio.sleep(random.uniform(3, 7))
                    return {
                        'platform': platform_name,
                        'success': True,
                        'submission_time': datetime.now().isoformat()
                    }
            
            return {'platform': platform_name, 'success': False, 'error': 'Submission failed'}
            
        except Exception as e:
            return {'platform': platform_name, 'success': False, 'error': str(e)}
    
    def _generate_reddit_title(self, url: str, metadata: Dict = None) -> str:
        """Generate appropriate title for Reddit submission"""
        
        if metadata and 'title' in metadata:
            return metadata['title']
        
        # Generate generic titles
        titles = [
            "Interesting article worth reading",
            "Found this helpful resource",
            "Great content on this topic",
            "Useful information here",
            "Worth checking out"
        ]
        
        return random.choice(titles)
    
    def _generate_generic_title(self, url: str, metadata: Dict = None) -> str:
        """Generate generic title for bookmarking"""
        
        if metadata and 'title' in metadata:
            return metadata['title']
        
        # Extract domain for title
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            return f"Content from {domain}"
        except:
            return "Interesting content"