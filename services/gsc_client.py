import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app import db
from models import Sitemap, GSCFeedback, URL, Settings
from config import Config

logger = logging.getLogger(__name__)

class GSCClient:
    """Google Search Console API client"""
    
    def __init__(self):
        self.settings = Settings.query.first()
        if not self.settings:
            raise ValueError("Application settings not configured")
        
        # Initialize Google API credentials
        self.credentials = self._get_credentials()
        self.service = build('searchconsole', 'v1', credentials=self.credentials)
    
    def _get_credentials(self):
        """Get Google API credentials from service account file"""
        try:
            # Try to get credentials from environment variable (JSON string)
            creds_json = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
            if creds_json:
                creds_info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=Config.GSC_SCOPES
                )
            else:
                # Fallback to service account file
                if os.path.exists(Config.GSC_SERVICE_ACCOUNT_FILE):
                    credentials = service_account.Credentials.from_service_account_file(
                        Config.GSC_SERVICE_ACCOUNT_FILE, scopes=Config.GSC_SCOPES
                    )
                else:
                    logger.warning("No GSC credentials found. Sitemap submission will be disabled.")
                    return None
            
            return credentials
        except Exception as e:
            logger.error(f"Error loading GSC credentials: {str(e)}")
            return None
    
    def submit_sitemap(self, sitemap_filename: str) -> bool:
        """Submit sitemap to Google Search Console"""
        if not self.credentials:
            logger.warning("GSC credentials not available, skipping sitemap submission")
            return False
        
        try:
            # Build sitemap URL
            sitemap_url = f"{self.settings.site_url.rstrip('/')}/sitemaps/{sitemap_filename}"
            
            # Submit sitemap
            self.service.sitemaps().submit(
                siteUrl=self.settings.gsc_property_url,
                feedpath=sitemap_url
            ).execute()
            
            # Update sitemap record
            sitemap = Sitemap.query.filter_by(filename=sitemap_filename).first()
            if sitemap:
                sitemap.submitted_at = datetime.utcnow()
                sitemap.submission_status = 'submitted'
                db.session.commit()
            
            logger.info(f"Successfully submitted sitemap: {sitemap_url}")
            return True
            
        except HttpError as e:
            error_details = json.loads(e.content.decode()) if e.content else {}
            error_message = error_details.get('error', {}).get('message', str(e))
            
            # Update sitemap record with error
            sitemap = Sitemap.query.filter_by(filename=sitemap_filename).first()
            if sitemap:
                sitemap.submission_status = 'error'
                db.session.commit()
            
            logger.error(f"Error submitting sitemap {sitemap_url}: {error_message}")
            return False
        
        except Exception as e:
            logger.error(f"Unexpected error submitting sitemap {sitemap_filename}: {str(e)}")
            return False
    
    def get_sitemap_status(self, sitemap_filename: str) -> Dict:
        """Get sitemap status from GSC"""
        if not self.credentials:
            return {'status': 'no_credentials'}
        
        try:
            sitemap_url = f"{self.settings.site_url.rstrip('/')}/sitemaps/{sitemap_filename}"
            
            response = self.service.sitemaps().get(
                siteUrl=self.settings.gsc_property_url,
                feedpath=sitemap_url
            ).execute()
            
            # Update sitemap record
            sitemap = Sitemap.query.filter_by(filename=sitemap_filename).first()
            if sitemap:
                sitemap.last_fetch_at = datetime.utcnow()
                sitemap.errors_count = len(response.get('errors', []))
                sitemap.warnings_count = len(response.get('warnings', []))
                
                if response.get('isPending'):
                    sitemap.fetch_status = 'pending'
                elif sitemap.errors_count > 0:
                    sitemap.fetch_status = 'error'
                else:
                    sitemap.fetch_status = 'success'
                
                db.session.commit()
            
            return {
                'status': 'success',
                'data': response
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                return {'status': 'not_found'}
            else:
                error_details = json.loads(e.content.decode()) if e.content else {}
                return {
                    'status': 'error',
                    'error': error_details.get('error', {}).get('message', str(e))
                }
        
        except Exception as e:
            logger.error(f"Error getting sitemap status for {sitemap_filename}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def harvest_url_inspection_data(self, urls: List[str] = None, limit: int = 100) -> int:
        """Harvest URL inspection data from GSC"""
        if not self.credentials:
            logger.warning("GSC credentials not available, skipping URL inspection harvest")
            return 0
        
        if not urls:
            # Get URLs that need inspection (recently crawled or haven't been checked)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            url_objects = URL.query.filter(
                db.or_(
                    URL.last_checked >= cutoff_date,
                    URL.last_indexed.is_(None)
                )
            ).limit(limit).all()
            urls = [url.url for url in url_objects]
        
        harvested_count = 0
        
        for url in urls:
            try:
                # Use URL Inspection API
                request_body = {
                    'inspectionUrl': url,
                    'siteUrl': self.settings.gsc_property_url
                }
                
                response = self.service.urlInspection().index().inspect(
                    body=request_body
                ).execute()
                
                # Parse inspection results
                inspection_result = response.get('inspectionResult', {})
                index_status_result = inspection_result.get('indexStatusResult', {})
                
                # Find corresponding URL in database
                url_obj = URL.query.filter_by(url=url).first()
                if not url_obj:
                    continue
                
                # Update or create GSC feedback record
                gsc_feedback = GSCFeedback.query.filter_by(url_id=url_obj.id).first()
                if not gsc_feedback:
                    gsc_feedback = GSCFeedback()
                    gsc_feedback.url_id = url_obj.id
                    db.session.add(gsc_feedback)
                
                # Update feedback data
                gsc_feedback.index_status = index_status_result.get('verdict', 'unknown')
                gsc_feedback.coverage_state = index_status_result.get('coverageState', 'unknown')
                
                if index_status_result.get('lastCrawlTime'):
                    gsc_feedback.last_crawled = datetime.fromisoformat(
                        index_status_result['lastCrawlTime'].replace('Z', '+00:00')
                    )
                
                # Update URL status based on GSC feedback
                if gsc_feedback.index_status in ['PASS', 'PARTIAL']:
                    url_obj.status = 'indexed'
                    url_obj.last_indexed = datetime.utcnow()
                elif gsc_feedback.index_status in ['FAIL']:
                    if url_obj.status == 'indexed':  # Was indexed, now failed
                        url_obj.status = 'error'
                        url_obj.last_error = f"GSC index status: {gsc_feedback.coverage_state}"
                
                gsc_feedback.updated_at = datetime.utcnow()
                harvested_count += 1
                
                # Commit every 10 records to avoid large transactions
                if harvested_count % 10 == 0:
                    db.session.commit()
                
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    logger.warning("Rate limit reached, stopping URL inspection harvest")
                    break
                else:
                    logger.warning(f"Error inspecting URL {url}: {str(e)}")
                    continue
            
            except Exception as e:
                logger.error(f"Unexpected error inspecting URL {url}: {str(e)}")
                continue
        
        # Final commit
        db.session.commit()
        logger.info(f"Harvested inspection data for {harvested_count} URLs")
        return harvested_count
    
    def get_search_analytics_data(self, start_date: datetime, end_date: datetime, 
                                 dimensions: List[str] = ['page']) -> List[Dict]:
        """Get search analytics data from GSC"""
        if not self.credentials:
            logger.warning("GSC credentials not available")
            return []
        
        try:
            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': dimensions,
                'rowLimit': 1000
            }
            
            response = self.service.searchanalytics().query(
                siteUrl=self.settings.gsc_property_url,
                body=request_body
            ).execute()
            
            return response.get('rows', [])
            
        except Exception as e:
            logger.error(f"Error getting search analytics data: {str(e)}")
            return []
    
    def list_sitemaps(self) -> List[Dict]:
        """List all sitemaps submitted to GSC"""
        if not self.credentials:
            return []
        
        try:
            response = self.service.sitemaps().list(
                siteUrl=self.settings.gsc_property_url
            ).execute()
            
            return response.get('sitemap', [])
            
        except Exception as e:
            logger.error(f"Error listing sitemaps: {str(e)}")
            return []

def submit_sitemap_to_gsc(sitemap_filename: str) -> bool:
    """Convenience function to submit a sitemap"""
    client = GSCClient()
    return client.submit_sitemap(sitemap_filename)

def harvest_gsc_feedback(limit: int = 100) -> int:
    """Convenience function to harvest GSC feedback"""
    client = GSCClient()
    return client.harvest_url_inspection_data(limit=limit)
