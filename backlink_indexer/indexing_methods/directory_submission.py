"""
Directory submission engine for automated web directory submissions
"""

import asyncio
import random
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import IndexingMethodBase


class DirectorySubmissionEngine(IndexingMethodBase):
    """Automated web directory submission system"""
    
    def __init__(self, config, browser_manager):
        super().__init__(config, browser_manager)
        
        # High-quality web directories
        self.directory_platforms = {
            'dmoz_alternatives': {
                'directories': [
                    'https://www.businessseek.biz',
                    'https://www.exactseek.com',
                    'https://www.goguides.org',
                    'https://www.jayde.com'
                ],
                'authority_score': 70,
                'submission_type': 'free',
                'approval_time': '1-4 weeks',
                'category_based': True
            },
            'niche_directories': {
                'directories': [
                    'https://www.addme.com',
                    'https://www.directory.com',
                    'https://www.websitessubmission.com'
                ],
                'authority_score': 60,
                'submission_type': 'mixed',
                'approval_time': '1-2 weeks',
                'category_based': True
            },
            'local_directories': {
                'directories': [
                    'https://www.yellowpages.com',
                    'https://www.superpages.com',
                    'https://www.citylocal.com'
                ],
                'authority_score': 65,
                'submission_type': 'business_focused',
                'approval_time': '1-3 days',
                'category_based': False
            },
            'industry_directories': {
                'directories': [
                    'https://www.thomasnet.com',
                    'https://www.kompass.com',
                    'https://www.europages.com'
                ],
                'authority_score': 75,
                'submission_type': 'business_b2b',
                'approval_time': '1-2 weeks',
                'category_based': True
            }
        }
        
        # Common directory categories
        self.directory_categories = {
            'business': [
                'Business and Economy',
                'Companies',
                'Services',
                'Finance and Investment',
                'Marketing and Advertising'
            ],
            'technology': [
                'Computers and Technology',
                'Software',
                'Web Development',
                'Internet Services',
                'Tech Support'
            ],
            'health': [
                'Health and Medicine',
                'Fitness and Wellness',
                'Medical Services',
                'Healthcare',
                'Alternative Medicine'
            ],
            'education': [
                'Education and Training',
                'Online Learning',
                'Schools and Universities',
                'Courses and Tutorials',
                'Educational Resources'
            ],
            'lifestyle': [
                'Lifestyle and Culture',
                'Entertainment',
                'Travel and Tourism',
                'Food and Dining',
                'Sports and Recreation'
            ]
        }
        
        # Submission form field mappings
        self.form_field_mappings = {
            'url': ['url', 'website', 'site_url', 'web_address', 'link'],
            'title': ['title', 'site_title', 'business_name', 'name', 'company_name'],
            'description': ['description', 'site_description', 'summary', 'details', 'about'],
            'keywords': ['keywords', 'tags', 'key_words', 'meta_keywords'],
            'category': ['category', 'cat', 'section', 'topic', 'classification'],
            'contact_email': ['email', 'contact_email', 'admin_email', 'webmaster'],
            'contact_name': ['contact_name', 'admin_name', 'owner_name', 'webmaster_name']
        }
    
    async def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process URL for directory submissions"""
        if not await self.validate_url(url):
            return {
                'url': url,
                'method': 'directory_submission',
                'success': False,
                'error': 'Invalid URL format',
                'timestamp': datetime.now().isoformat()
            }
        
        # Analyze website for categorization
        site_analysis = await self.analyze_website_for_categorization(url)
        
        # Generate submission data
        submission_data = await self.generate_submission_data(url, site_analysis, metadata)
        
        # Find appropriate directories
        suitable_directories = await self.find_suitable_directories(site_analysis)
        
        results = []
        for directory_info in suitable_directories[:5]:  # Limit to top 5 directories
            try:
                result = await self.submit_to_directory(url, directory_info, submission_data)
                results.append(result)
                
                # Respect submission intervals
                await self.browser_manager.human_like_delay('slow')
                
            except Exception as e:
                self.logger.error(f"Failed to submit to directory {directory_info['url']}: {str(e)}")
                results.append({
                    'directory': directory_info['url'],
                    'success': False,
                    'error': str(e)
                })
        
        overall_success = any(result.get('success', False) for result in results)
        
        return {
            'url': url,
            'method': 'directory_submission',
            'success': overall_success,
            'directory_results': results,
            'site_category': site_analysis.get('category', 'general'),
            'submission_data': submission_data,
            'timestamp': datetime.now().isoformat()
        }
    
    async def analyze_website_for_categorization(self, url: str) -> Dict[str, Any]:
        """Analyze website to determine appropriate directory category"""
        analysis = {
            'category': 'business',  # default
            'title': '',
            'description': '',
            'keywords': [],
            'business_type': 'general',
            'contact_info': {}
        }
        
        try:
            driver = self.browser_manager.create_stealth_browser()
            driver.get(url)
            await asyncio.sleep(3)
            
            # Extract basic information
            try:
                analysis['title'] = driver.title or ''
                
                # Meta description
                meta_desc = driver.find_element("css selector", "meta[name='description']")
                analysis['description'] = meta_desc.get_attribute('content') or ''
                
                # Meta keywords
                try:
                    meta_keywords = driver.find_element("css selector", "meta[name='keywords']")
                    keywords_content = meta_keywords.get_attribute('content') or ''
                    analysis['keywords'] = [kw.strip() for kw in keywords_content.split(',') if kw.strip()]
                except:
                    pass
                
            except Exception as e:
                self.logger.debug(f"Meta extraction failed: {str(e)}")
            
            # Analyze content for category determination
            try:
                body_text = driver.find_element("tag name", "body").text.lower()
                
                # Category scoring
                category_scores = {
                    'technology': self._count_keywords(body_text, [
                        'software', 'technology', 'development', 'programming', 'digital',
                        'tech', 'app', 'platform', 'system', 'solution'
                    ]),
                    'business': self._count_keywords(body_text, [
                        'business', 'company', 'service', 'consulting', 'marketing',
                        'sales', 'corporate', 'professional', 'commercial'
                    ]),
                    'health': self._count_keywords(body_text, [
                        'health', 'medical', 'healthcare', 'fitness', 'wellness',
                        'doctor', 'clinic', 'treatment', 'therapy'
                    ]),
                    'education': self._count_keywords(body_text, [
                        'education', 'learning', 'course', 'training', 'tutorial',
                        'school', 'university', 'academic', 'study'
                    ]),
                    'lifestyle': self._count_keywords(body_text, [
                        'lifestyle', 'travel', 'food', 'entertainment', 'culture',
                        'recreation', 'hobby', 'fashion', 'art'
                    ])
                }
                
                if category_scores:
                    best_category = max(category_scores.items(), key=lambda x: x[1])
                    if best_category[1] > 0:
                        analysis['category'] = best_category[0]
                
            except Exception as e:
                self.logger.debug(f"Content analysis failed: {str(e)}")
            
            # Extract contact information
            try:
                contact_info = {}
                
                # Look for email addresses
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, driver.page_source)
                if emails:
                    contact_info['email'] = emails[0]
                
                # Look for phone numbers (simplified)
                phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
                phones = re.findall(phone_pattern, driver.page_source)
                if phones:
                    contact_info['phone'] = phones[0]
                
                analysis['contact_info'] = contact_info
                
            except Exception as e:
                self.logger.debug(f"Contact extraction failed: {str(e)}")
            
            driver.quit()
            
        except Exception as e:
            self.logger.error(f"Website analysis failed: {str(e)}")
        
        return analysis
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count occurrences of keywords in text"""
        return sum(1 for keyword in keywords if keyword in text)
    
    async def generate_submission_data(self, url: str, site_analysis: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, str]:
        """Generate submission data for directory forms"""
        metadata = metadata or {}
        
        # Extract domain name for default title
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        
        submission_data = {
            'url': url,
            'title': site_analysis.get('title') or metadata.get('title') or domain.title(),
            'description': site_analysis.get('description') or metadata.get('description') or 
                         f"Professional website offering quality services and solutions. Visit {domain} for more information.",
            'keywords': ', '.join(site_analysis.get('keywords', [])[:10]) or metadata.get('keywords', ''),
            'category': site_analysis.get('category', 'business'),
            'contact_email': site_analysis.get('contact_info', {}).get('email') or 
                           metadata.get('contact_email', f'admin@{domain}'),
            'contact_name': metadata.get('contact_name', 'Website Administrator')
        }
        
        # Ensure description is appropriate length (usually 25-250 characters)
        if len(submission_data['description']) < 25:
            submission_data['description'] = f"{submission_data['description']} Quality services and professional solutions available at {domain}."
        elif len(submission_data['description']) > 250:
            submission_data['description'] = submission_data['description'][:247] + '...'
        
        return submission_data
    
    async def find_suitable_directories(self, site_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find directories suitable for the website"""
        category = site_analysis.get('category', 'business')
        suitable_directories = []
        
        # Select directories based on category and quality
        for directory_type, directory_config in self.directory_platforms.items():
            for directory_url in directory_config['directories']:
                
                # Calculate suitability score
                suitability_score = directory_config['authority_score']
                
                # Bonus for category match
                if category in directory_type or 'niche' in directory_type:
                    suitability_score += 10
                
                suitable_directories.append({
                    'url': directory_url,
                    'type': directory_type,
                    'authority_score': directory_config['authority_score'],
                    'submission_type': directory_config['submission_type'],
                    'suitability_score': suitability_score,
                    'category_based': directory_config['category_based']
                })
        
        # Sort by suitability score
        suitable_directories.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        return suitable_directories
    
    async def submit_to_directory(self, url: str, directory_info: Dict[str, Any], submission_data: Dict[str, str]) -> Dict[str, Any]:
        """Submit website to a specific directory"""
        try:
            # In mock mode, just simulate the submission
            if hasattr(self.config, 'mock_mode') and self.config.mock_mode:
                await asyncio.sleep(random.uniform(2, 5))  # Simulate form filling time
                
                self.logger.info(f"[MOCK] Would submit to directory: {directory_info['url']}")
                return {
                    'directory': directory_info['url'],
                    'success': True,
                    'submission_type': directory_info['submission_type'],
                    'authority_score': directory_info['authority_score'],
                    'mock_mode': True,
                    'submission_data': submission_data
                }
            
            # Actual submission implementation would go here
            driver = self.browser_manager.create_stealth_browser()
            
            try:
                # Navigate to directory
                driver.get(directory_info['url'])
                await asyncio.sleep(random.uniform(2, 4))
                
                # Look for submission form or "Add URL" link
                submission_form = await self.find_submission_form(driver)
                
                if not submission_form:
                    return {
                        'directory': directory_info['url'],
                        'success': False,
                        'error': 'Submission form not found'
                    }
                
                # Fill and submit form
                success = await self.fill_submission_form(driver, submission_data, directory_info)
                
                return {
                    'directory': directory_info['url'],
                    'success': success,
                    'submission_type': directory_info['submission_type'],
                    'authority_score': directory_info['authority_score']
                }
                
            finally:
                driver.quit()
            
        except Exception as e:
            return {
                'directory': directory_info['url'],
                'success': False,
                'error': str(e)
            }
    
    async def find_submission_form(self, driver) -> bool:
        """Find and navigate to submission form"""
        try:
            # Common submission link texts
            submission_links = [
                'add url', 'submit site', 'add site', 'submit url',
                'add listing', 'submit listing', 'suggest site'
            ]
            
            # Look for submission links
            for link_text in submission_links:
                try:
                    link = driver.find_element("partial link text", link_text)
                    link.click()
                    await asyncio.sleep(2)
                    return True
                except:
                    try:
                        link = driver.find_element("partial link text", link_text.title())
                        link.click()
                        await asyncio.sleep(2)
                        return True
                    except:
                        continue
            
            # Look for form directly on page
            forms = driver.find_elements("tag name", "form")
            if forms:
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Form finding failed: {str(e)}")
            return False
    
    async def fill_submission_form(self, driver, submission_data: Dict[str, str], directory_info: Dict[str, Any]) -> bool:
        """Fill out the directory submission form"""
        try:
            # Find and fill form fields
            for data_key, value in submission_data.items():
                if not value:
                    continue
                
                possible_field_names = self.form_field_mappings.get(data_key, [data_key])
                
                field_filled = False
                for field_name in possible_field_names:
                    try:
                        # Try different field selectors
                        field_selectors = [
                            f"input[name='{field_name}']",
                            f"textarea[name='{field_name}']",
                            f"select[name='{field_name}']",
                            f"#{field_name}",
                            f".{field_name}"
                        ]
                        
                        for selector in field_selectors:
                            try:
                                field = driver.find_element("css selector", selector)
                                
                                if field.tag_name.lower() == 'select':
                                    # Handle select fields (categories)
                                    await self.handle_category_selection(field, value, submission_data.get('category'))
                                else:
                                    # Regular input/textarea
                                    field.clear()
                                    await self.browser_manager.human_like_typing(field, value)
                                
                                field_filled = True
                                break
                                
                            except:
                                continue
                        
                        if field_filled:
                            break
                            
                    except Exception as e:
                        continue
                
                # Brief pause between fields
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Submit form
            submit_buttons = [
                "input[type='submit']",
                "button[type='submit']",
                "input[value*='submit']",
                "button:contains('Submit')"
            ]
            
            for selector in submit_buttons:
                try:
                    submit_btn = driver.find_element("css selector", selector)
                    submit_btn.click()
                    await asyncio.sleep(3)
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Form filling failed: {str(e)}")
            return False
    
    async def handle_category_selection(self, select_element, value: str, category: str):
        """Handle category selection in dropdown"""
        try:
            from selenium.webdriver.support.ui import Select
            select = Select(select_element)
            
            # Get available options
            options = [option.text.lower() for option in select.options]
            
            # Find best matching category
            category_matches = self.directory_categories.get(category, [])
            
            best_match = None
            for cat_option in category_matches:
                for option_text in options:
                    if cat_option.lower() in option_text:
                        best_match = option_text
                        break
                if best_match:
                    break
            
            if best_match:
                select.select_by_visible_text(best_match)
            else:
                # Select first non-empty option
                if len(select.options) > 1:
                    select.select_by_index(1)
            
        except Exception as e:
            self.logger.debug(f"Category selection failed: {str(e)}")
    
    def get_directory_stats(self) -> Dict[str, Any]:
        """Get statistics about available directories"""
        total_directories = sum(
            len(config['directories']) 
            for config in self.directory_platforms.values()
        )
        
        avg_authority = sum(
            config['authority_score'] 
            for config in self.directory_platforms.values()
        ) / len(self.directory_platforms)
        
        return {
            'total_directories': total_directories,
            'directory_types': list(self.directory_platforms.keys()),
            'categories': list(self.directory_categories.keys()),
            'average_authority_score': avg_authority,
            'form_fields': list(self.form_field_mappings.keys())
        }