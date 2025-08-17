"""
Puter.js backend integration for AI-powered content analysis
Handles AI analysis requests and provides data to the frontend
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import trafilatura
import httpx
from flask import jsonify, request
from ..models import IndexingResult, IndexingMethod, URLRecord


class ContentAnalyzer:
    """Advanced content analyzer using web scraping and AI insights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def analyze_url_content(self, url: str) -> Dict[str, Any]:
        """Analyze URL content and extract insights for indexing optimization"""
        
        try:
            # Fetch and extract content
            content_data = await self._fetch_url_content(url)
            
            # Analyze content characteristics
            content_analysis = self._analyze_content_characteristics(content_data)
            
            # Generate SEO insights
            seo_insights = self._generate_seo_insights(url, content_analysis)
            
            # Predict indexing difficulty
            indexing_prediction = self._predict_indexing_difficulty(url, content_analysis)
            
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'content_analysis': content_analysis,
                'seo_insights': seo_insights,
                'indexing_prediction': indexing_prediction,
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Content analysis failed for {url}: {str(e)}")
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            }
    
    async def _fetch_url_content(self, url: str) -> Dict[str, Any]:
        """Fetch and extract clean content from URL"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()
                
                # Extract clean text content using trafilatura
                downloaded = response.text
                text_content = trafilatura.extract(downloaded)
                
                # Extract metadata
                metadata = trafilatura.extract_metadata(downloaded)
                
                return {
                    'html': downloaded[:5000],  # First 5K chars for analysis
                    'text_content': text_content or '',
                    'title': metadata.title if metadata else '',
                    'author': metadata.author if metadata else '',
                    'date': metadata.date if metadata else '',
                    'description': metadata.description if metadata else '',
                    'sitename': metadata.sitename if metadata else '',
                    'response_status': response.status_code,
                    'content_length': len(response.text)
                }
                
            except httpx.HTTPError as e:
                raise Exception(f"HTTP error fetching {url}: {str(e)}")
            except Exception as e:
                raise Exception(f"Error extracting content: {str(e)}")
    
    def _analyze_content_characteristics(self, content_data: Dict) -> Dict[str, Any]:
        """Analyze content characteristics for indexing optimization"""
        
        text_content = content_data.get('text_content', '')
        html_content = content_data.get('html', '')
        
        # Basic text analysis
        word_count = len(text_content.split()) if text_content else 0
        char_count = len(text_content) if text_content else 0
        
        # Content structure analysis
        heading_count = html_content.count('<h1>') + html_content.count('<h2>') + html_content.count('<h3>')
        link_count = html_content.count('<a href=')
        image_count = html_content.count('<img')
        
        # Content quality indicators
        avg_sentence_length = self._calculate_avg_sentence_length(text_content)
        readability_score = self._estimate_readability(text_content)
        keyword_density = self._analyze_keyword_density(text_content)
        
        # Content type classification
        content_type = self._classify_content_type(content_data, text_content)
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'heading_count': heading_count,
            'link_count': link_count,
            'image_count': image_count,
            'avg_sentence_length': avg_sentence_length,
            'readability_score': readability_score,
            'keyword_density': keyword_density,
            'content_type': content_type,
            'has_title': bool(content_data.get('title')),
            'has_description': bool(content_data.get('description')),
            'has_author': bool(content_data.get('author')),
            'has_date': bool(content_data.get('date'))
        }
    
    def _calculate_avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length"""
        if not text:
            return 0.0
        
        sentences = text.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        total_words = sum(len(sentence.split()) for sentence in sentences)
        return total_words / len(sentences)
    
    def _estimate_readability(self, text: str) -> float:
        """Estimate readability score (simplified Flesch-Kincaid)"""
        if not text:
            return 0.0
        
        sentences = text.split('.')
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Count syllables (simplified approximation)
        total_syllables = 0
        for word in words:
            syllables = max(1, len([char for char in word.lower() if char in 'aeiou']))
            total_syllables += syllables
        
        avg_syllables = total_syllables / len(words) if words else 0
        
        # Simplified Flesch-Kincaid formula
        readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        return max(0, min(100, readability))
    
    def _analyze_keyword_density(self, text: str) -> Dict[str, float]:
        """Analyze keyword density for top terms"""
        if not text:
            return {}
        
        words = text.lower().split()
        word_freq = {}
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        for word in words:
            word = word.strip('.,!?";()[]{}')
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        total_words = len(words)
        keyword_density = {}
        
        # Get top 10 keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for keyword, count in top_keywords:
            density = (count / total_words) * 100 if total_words > 0 else 0
            keyword_density[keyword] = density
        
        return keyword_density
    
    def _classify_content_type(self, content_data: Dict, text_content: str) -> str:
        """Classify the type of content"""
        
        title = content_data.get('title', '').lower()
        url_path = content_data.get('url', '').lower()
        
        # Classification based on URL patterns and title
        if any(keyword in url_path for keyword in ['blog', 'post', 'article', 'news']):
            return 'article'
        elif any(keyword in url_path for keyword in ['product', 'item', 'shop', 'buy']):
            return 'product'
        elif any(keyword in url_path for keyword in ['about', 'contact', 'team']):
            return 'page'
        elif any(keyword in url_path for keyword in ['category', 'tag', 'archive']):
            return 'listing'
        elif any(keyword in title for keyword in ['how to', 'guide', 'tutorial']):
            return 'tutorial'
        else:
            return 'general'
    
    def _generate_seo_insights(self, url: str, content_analysis: Dict) -> Dict[str, Any]:
        """Generate SEO insights and recommendations"""
        
        insights = {
            'seo_score': 0,
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        score = 0
        
        # Title analysis
        if content_analysis.get('has_title'):
            score += 15
            insights['strengths'].append('Has title tag')
        else:
            insights['weaknesses'].append('Missing title tag')
            insights['recommendations'].append('Add a descriptive title tag')
        
        # Description analysis
        if content_analysis.get('has_description'):
            score += 10
            insights['strengths'].append('Has meta description')
        else:
            insights['weaknesses'].append('Missing meta description')
            insights['recommendations'].append('Add a compelling meta description')
        
        # Content length analysis
        word_count = content_analysis.get('word_count', 0)
        if word_count >= 300:
            score += 20
            insights['strengths'].append(f'Sufficient content length ({word_count} words)')
        else:
            insights['weaknesses'].append('Content too short')
            insights['recommendations'].append('Expand content to at least 300 words')
        
        # Structure analysis
        heading_count = content_analysis.get('heading_count', 0)
        if heading_count > 0:
            score += 15
            insights['strengths'].append('Has heading structure')
        else:
            insights['weaknesses'].append('No heading structure')
            insights['recommendations'].append('Add H1, H2, H3 headings for better structure')
        
        # Readability analysis
        readability = content_analysis.get('readability_score', 0)
        if readability >= 60:
            score += 10
            insights['strengths'].append('Good readability')
        else:
            insights['weaknesses'].append('Poor readability')
            insights['recommendations'].append('Improve readability with shorter sentences')
        
        # URL analysis
        parsed_url = urlparse(url)
        if parsed_url.scheme == 'https':
            score += 10
            insights['strengths'].append('HTTPS enabled')
        else:
            insights['weaknesses'].append('Not using HTTPS')
            insights['recommendations'].append('Enable HTTPS for better security and SEO')
        
        # Internal linking
        link_count = content_analysis.get('link_count', 0)
        if link_count > 0:
            score += 10
            insights['strengths'].append('Has internal/external links')
        else:
            insights['weaknesses'].append('No links found')
            insights['recommendations'].append('Add relevant internal and external links')
        
        # Images
        image_count = content_analysis.get('image_count', 0)
        if image_count > 0:
            score += 10
            insights['strengths'].append('Contains images')
        else:
            insights['recommendations'].append('Add relevant images to enhance content')
        
        insights['seo_score'] = min(100, score)
        return insights
    
    def _predict_indexing_difficulty(self, url: str, content_analysis: Dict) -> Dict[str, Any]:
        """Predict indexing difficulty and success probability"""
        
        difficulty_score = 0
        factors = []
        
        # Domain authority factors (simplified)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Well-known domains get lower difficulty
        if any(tld in domain for tld in ['.edu', '.gov', '.org']):
            difficulty_score -= 20
            factors.append('Authoritative domain extension')
        
        # Content quality factors
        word_count = content_analysis.get('word_count', 0)
        if word_count < 300:
            difficulty_score += 15
            factors.append('Short content may be harder to index')
        elif word_count > 1000:
            difficulty_score -= 10
            factors.append('Comprehensive content')
        
        # Structure factors
        if content_analysis.get('heading_count', 0) == 0:
            difficulty_score += 10
            factors.append('No heading structure')
        
        # Technical factors
        if not content_analysis.get('has_title'):
            difficulty_score += 15
            factors.append('Missing title tag')
        
        if not content_analysis.get('has_description'):
            difficulty_score += 10
            factors.append('Missing meta description')
        
        # URL depth
        path_depth = len([p for p in parsed_url.path.split('/') if p])
        if path_depth > 4:
            difficulty_score += 5
            factors.append('Deep URL path')
        
        # Calculate success probability
        base_success_rate = 85  # Base rate for good content
        adjusted_success_rate = max(20, min(95, base_success_rate - difficulty_score))
        
        # Determine difficulty level
        if difficulty_score <= 10:
            difficulty = 'Easy'
        elif difficulty_score <= 25:
            difficulty = 'Medium'
        else:
            difficulty = 'Hard'
        
        return {
            'difficulty': difficulty,
            'difficulty_score': difficulty_score,
            'predicted_success_rate': adjusted_success_rate,
            'factors': factors,
            'recommended_methods': self._recommend_indexing_methods(difficulty_score, content_analysis)
        }
    
    def _recommend_indexing_methods(self, difficulty_score: int, content_analysis: Dict) -> List[Dict[str, Any]]:
        """Recommend optimal indexing methods based on analysis"""
        
        recommendations = []
        
        # High-success methods for all content
        recommendations.extend([
            {
                'method': 'rss_distribution',
                'priority': 1,
                'success_rate': 90,
                'reason': 'RSS feeds are quickly crawled by search engines'
            },
            {
                'method': 'social_bookmarking',
                'priority': 2,
                'success_rate': 85,
                'reason': 'Social bookmarking sites have high crawl rates'
            }
        ])
        
        # Content-specific recommendations
        content_type = content_analysis.get('content_type', 'general')
        
        if content_type in ['article', 'tutorial']:
            recommendations.append({
                'method': 'web2_posting',
                'priority': 3,
                'success_rate': 80,
                'reason': 'Articles perform well on Web 2.0 platforms'
            })
        
        if content_type == 'product':
            recommendations.append({
                'method': 'directory_submission',
                'priority': 3,
                'success_rate': 75,
                'reason': 'Product pages benefit from directory listings'
            })
        
        # Quality-based recommendations
        word_count = content_analysis.get('word_count', 0)
        if word_count > 500:
            recommendations.append({
                'method': 'forum_commenting',
                'priority': 4,
                'success_rate': 70,
                'reason': 'Long-form content suitable for forum discussions'
            })
        
        # Social signals for engaging content
        if content_analysis.get('image_count', 0) > 0:
            recommendations.append({
                'method': 'social_signals',
                'priority': 5,
                'success_rate': 80,
                'reason': 'Visual content performs well on social platforms'
            })
        
        # Adjust success rates based on difficulty
        difficulty_adjustment = max(-10, min(10, -difficulty_score // 3))
        for rec in recommendations:
            rec['adjusted_success_rate'] = max(50, min(95, rec['success_rate'] + difficulty_adjustment))
        
        return recommendations


# Initialize the content analyzer
content_analyzer = ContentAnalyzer()


def register_ai_routes(app):
    """Register AI analysis routes with the Flask app"""
    
    @app.route('/api/analyze-content', methods=['POST'])
    async def analyze_content():
        """Analyze URL content for AI-powered indexing optimization"""
        
        try:
            data = request.get_json()
            url = data.get('url')
            
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            # Analyze content
            analysis_result = await content_analyzer.analyze_url_content(url)
            
            return jsonify(analysis_result)
            
        except Exception as e:
            app.logger.error(f"Content analysis API error: {str(e)}")
            return jsonify({
                'error': 'Analysis failed',
                'message': str(e),
                'status': 'failed'
            }), 500
    
    @app.route('/api/ai/bulk-analyze', methods=['POST'])
    async def bulk_analyze_content():
        """Analyze multiple URLs for AI-powered optimization"""
        
        try:
            data = request.get_json()
            urls = data.get('urls', [])
            
            if not urls or not isinstance(urls, list):
                return jsonify({'error': 'URLs list is required'}), 400
            
            if len(urls) > 20:  # Limit bulk analysis
                return jsonify({'error': 'Maximum 20 URLs allowed per batch'}), 400
            
            # Analyze each URL
            results = []
            for url in urls:
                analysis_result = await content_analyzer.analyze_url_content(url)
                results.append(analysis_result)
            
            return jsonify({
                'results': results,
                'total_analyzed': len(results),
                'successful': len([r for r in results if r.get('status') == 'success']),
                'failed': len([r for r in results if r.get('status') == 'failed'])
            })
            
        except Exception as e:
            app.logger.error(f"Bulk analysis API error: {str(e)}")
            return jsonify({
                'error': 'Bulk analysis failed',
                'message': str(e)
            }), 500
    
    @app.route('/api/ai/recommendations', methods=['POST'])
    async def get_ai_recommendations():
        """Get AI-powered indexing method recommendations"""
        
        try:
            data = request.get_json()
            url = data.get('url')
            analysis_data = data.get('analysis_data')
            
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            # If analysis data not provided, analyze the URL
            if not analysis_data:
                analysis_result = await content_analyzer.analyze_url_content(url)
                if analysis_result.get('status') != 'success':
                    return jsonify(analysis_result), 400
                analysis_data = analysis_result
            
            # Generate detailed recommendations
            recommendations = content_analyzer._predict_indexing_difficulty(
                url, 
                analysis_data.get('content_analysis', {})
            )
            
            return jsonify({
                'url': url,
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app.logger.error(f"AI recommendations API error: {str(e)}")
            return jsonify({
                'error': 'Recommendations generation failed',
                'message': str(e)
            }), 500