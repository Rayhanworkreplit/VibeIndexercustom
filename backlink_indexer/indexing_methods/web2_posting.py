"""
Web 2.0 Property Automation Engine
"""

import asyncio
import random
from typing import Dict, Any, List
from selenium.webdriver.common.by import By
from datetime import datetime
from .base import IndexingMethodBase


class Web2PostingEngine(IndexingMethodBase):
    """Automated posting to Web 2.0 platforms"""
    
    def __init__(self, config, browser_manager):
        super().__init__(config, browser_manager)
        self.platforms = {
            'blogger': {
                'url': 'https://www.blogger.com/blogger.g?blogID=',
                'enabled': True,
                'authority_score': 85,
                'post_type': 'blog_post'
            },
            'wordpress': {
                'url': 'https://wordpress.com/wp-admin/post-new.php',
                'enabled': True,
                'authority_score': 90,
                'post_type': 'blog_post'
            },
            'tumblr': {
                'url': 'https://www.tumblr.com/new/text',
                'enabled': True,
                'authority_score': 75,
                'post_type': 'text_post'
            },
            'medium': {
                'url': 'https://medium.com/new-story',
                'enabled': True,
                'authority_score': 88,
                'post_type': 'article'
            }
        }
        
        # Content templates for different types of posts
        self.content_templates = {
            'review': [
                "I recently came across {url} and found it quite insightful. The content covers {topic} in great detail.",
                "Here's an excellent resource I discovered: {url}. It provides comprehensive information about {topic}.",
                "Worth sharing this valuable content: {url}. Great insights on {topic} that many would find useful."
            ],
            'recommendation': [
                "Highly recommend checking out {url} for anyone interested in {topic}.",
                "Found this helpful resource on {topic}: {url}. Definitely worth a read.",
                "Sharing a great find: {url}. Excellent content covering {topic} thoroughly."
            ],
            'educational': [
                "Learning more about {topic}? This resource is excellent: {url}",
                "Educational content on {topic} that I found valuable: {url}",
                "For those studying {topic}, this is a must-read: {url}"
            ]
        }
    
    async def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create posts on Web 2.0 platforms featuring the URL"""
        
        if not await self.validate_url(url):
            return {
                'url': url,
                'method': 'web2_posting',
                'success': False,
                'error': 'Invalid URL format',
                'timestamp': datetime.now().isoformat()
            }
        
        results = []
        successful_posts = 0
        
        for platform_name, platform_config in self.platforms.items():
            if not platform_config.get('enabled', True):
                continue
                
            try:
                result = await self.create_post_on_platform(url, platform_name, platform_config, metadata)
                results.append(result)
                
                if result.get('success', False):
                    successful_posts += 1
                
                # Rate limiting between platforms
                await asyncio.sleep(random.uniform(10, 20))
                
            except Exception as e:
                self.logger.error(f"Failed to post to {platform_name}: {str(e)}")
                results.append({
                    'platform': platform_name,
                    'success': False,
                    'error': str(e)
                })
        
        overall_success = successful_posts > 0
        
        return {
            'url': url,
            'method': 'web2_posting',
            'success': overall_success,
            'successful_posts': successful_posts,
            'total_platforms': len([p for p in self.platforms.values() if p.get('enabled', True)]),
            'platform_results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def create_post_on_platform(self, url: str, platform_name: str, 
                                    platform_config: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Create a post on a specific Web 2.0 platform"""
        
        driver = None
        try:
            driver = self.browser_manager.create_stealth_browser()
            
            # Navigate to platform
            success = await self.browser_manager.safe_navigate(driver, platform_config['url'])
            if not success:
                return {'platform': platform_name, 'success': False, 'error': 'Navigation failed'}
            
            # Generate post content
            post_content = self._generate_post_content(url, platform_name, metadata)
            
            # Handle platform-specific posting logic
            if platform_name == 'blogger':
                return await self._post_to_blogger(driver, post_content, url)
            elif platform_name == 'wordpress':
                return await self._post_to_wordpress(driver, post_content, url)
            elif platform_name == 'tumblr':
                return await self._post_to_tumblr(driver, post_content, url)
            elif platform_name == 'medium':
                return await self._post_to_medium(driver, post_content, url)
            else:
                return {'platform': platform_name, 'success': False, 'error': 'Unsupported platform'}
            
        except Exception as e:
            self.logger.error(f"Error posting to {platform_name}: {str(e)}")
            return {'platform': platform_name, 'success': False, 'error': str(e)}
        
        finally:
            if driver:
                self.browser_manager.cleanup_driver(driver)
    
    async def _post_to_blogger(self, driver, content: Dict, target_url: str) -> Dict[str, Any]:
        """Post to Blogger platform"""
        
        try:
            # This is a simplified version - in practice, authentication would be required
            # Find title field
            title_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'input[aria-label="Title"]'
            )
            
            if title_field:
                await self.browser_manager.human_like_typing(title_field, content['title'])
            
            # Find content area
            content_area = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[contenteditable="true"]'
            )
            
            if content_area:
                await self.browser_manager.human_like_typing(content_area, content['body'])
            
            await asyncio.sleep(random.uniform(3, 6))
            
            # Find publish button
            publish_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[data-action="publish"]'
            )
            
            if publish_button:
                success = await self.browser_manager.safe_click(driver, publish_button)
                
                if success:
                    await asyncio.sleep(random.uniform(5, 10))
                    return {
                        'platform': 'blogger',
                        'success': True,
                        'post_title': content['title'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {'platform': 'blogger', 'success': False, 'error': 'Publishing failed'}
            
        except Exception as e:
            return {'platform': 'blogger', 'success': False, 'error': str(e)}
    
    async def _post_to_wordpress(self, driver, content: Dict, target_url: str) -> Dict[str, Any]:
        """Post to WordPress platform"""
        
        try:
            # Find title field
            title_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '.editor-post-title__input'
            )
            
            if title_field:
                await self.browser_manager.human_like_typing(title_field, content['title'])
            
            # Find content area
            content_area = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '.block-editor-writing-flow'
            )
            
            if content_area:
                await self.browser_manager.safe_click(driver, content_area)
                await asyncio.sleep(1)
                
                # Type content
                from selenium.webdriver.common.keys import Keys
                content_area.send_keys(content['body'])
            
            await asyncio.sleep(random.uniform(3, 6))
            
            # Find publish button
            publish_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '.editor-post-publish-button'
            )
            
            if publish_button:
                success = await self.browser_manager.safe_click(driver, publish_button)
                
                if success:
                    await asyncio.sleep(random.uniform(5, 10))
                    return {
                        'platform': 'wordpress',
                        'success': True,
                        'post_title': content['title'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {'platform': 'wordpress', 'success': False, 'error': 'Publishing failed'}
            
        except Exception as e:
            return {'platform': 'wordpress', 'success': False, 'error': str(e)}
    
    async def _post_to_tumblr(self, driver, content: Dict, target_url: str) -> Dict[str, Any]:
        """Post to Tumblr platform"""
        
        try:
            # Find title field
            title_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, 'input[placeholder="Title"]'
            )
            
            if title_field:
                await self.browser_manager.human_like_typing(title_field, content['title'])
            
            # Find text area
            text_area = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '.ProseMirror'
            )
            
            if text_area:
                await self.browser_manager.human_like_typing(text_area, content['body'])
            
            await asyncio.sleep(random.uniform(3, 6))
            
            # Find post button
            post_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[data-testid="post-button"]'
            )
            
            if post_button:
                success = await self.browser_manager.safe_click(driver, post_button)
                
                if success:
                    await asyncio.sleep(random.uniform(5, 10))
                    return {
                        'platform': 'tumblr',
                        'success': True,
                        'post_title': content['title'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {'platform': 'tumblr', 'success': False, 'error': 'Publishing failed'}
            
        except Exception as e:
            return {'platform': 'tumblr', 'success': False, 'error': str(e)}
    
    async def _post_to_medium(self, driver, content: Dict, target_url: str) -> Dict[str, Any]:
        """Post to Medium platform"""
        
        try:
            # Find title field
            title_field = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[data-testid="richTextEditor"] h1'
            )
            
            if title_field:
                await self.browser_manager.human_like_typing(title_field, content['title'])
            
            # Find content area
            content_area = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[data-testid="richTextEditor"] div[contenteditable]'
            )
            
            if content_area:
                await self.browser_manager.human_like_typing(content_area, content['body'])
            
            await asyncio.sleep(random.uniform(3, 6))
            
            # Find publish button
            publish_button = await self.browser_manager.safe_find_element(
                driver, By.CSS_SELECTOR, '[data-testid="publishButton"]'
            )
            
            if publish_button:
                success = await self.browser_manager.safe_click(driver, publish_button)
                
                if success:
                    await asyncio.sleep(random.uniform(5, 10))
                    return {
                        'platform': 'medium',
                        'success': True,
                        'post_title': content['title'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {'platform': 'medium', 'success': False, 'error': 'Publishing failed'}
            
        except Exception as e:
            return {'platform': 'medium', 'success': False, 'error': str(e)}
    
    def _generate_post_content(self, url: str, platform: str, metadata: Dict = None) -> Dict[str, str]:
        """Generate appropriate content for the post"""
        
        # Extract domain for context
        domain = ""
        topic = "relevant topics"
        
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            
            if metadata and 'topic' in metadata:
                topic = metadata['topic']
        except:
            pass
        
        # Choose content template
        template_type = random.choice(['review', 'recommendation', 'educational'])
        templates = self.content_templates[template_type]
        chosen_template = random.choice(templates)
        
        # Generate title
        titles = [
            f"Valuable Resource: {domain}",
            f"Insights on {topic}",
            f"Worth Sharing: Quality Content",
            f"Interesting Find: {domain}",
            f"Educational Content on {topic}"
        ]
        
        title = random.choice(titles)
        if metadata and 'title' in metadata:
            title = metadata['title']
        
        # Generate body content
        body_parts = [
            chosen_template.format(url=url, topic=topic),
            "",  # Empty line
            "The content is well-structured and provides valuable insights that readers will find helpful.",
            "",
            f"Check it out here: {url}",
            "",
            "What are your thoughts on this topic? Feel free to share your experiences in the comments."
        ]
        
        body = "\n".join(body_parts)
        
        return {
            'title': title,
            'body': body
        }