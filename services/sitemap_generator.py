import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urljoin
import uuid
import logging

from app import db
from models import URL, Sitemap, Settings
from config import Config

logger = logging.getLogger(__name__)

class SitemapGenerator:
    """XML sitemap generation service"""
    
    def __init__(self):
        self.settings = Settings.query.first()
        if not self.settings:
            raise ValueError("Application settings not configured")
        
        # Ensure sitemap directory exists
        os.makedirs(Config.SITEMAP_DIR, exist_ok=True)
    
    def generate_sitemaps(self, url_ids: list) -> list:
        """
        Generate XML sitemaps for the given URL IDs
        Returns list of generated sitemap filenames
        """
        if not url_ids:
            return []
        
        # Fetch URLs that are ready for sitemap inclusion
        urls = URL.query.filter(
            URL.id.in_(url_ids),
            URL.status == 'ready'
        ).all()
        
        if not urls:
            logger.warning("No ready URLs found for sitemap generation")
            return []
        
        # Split URLs into chunks based on max URLs per sitemap
        max_urls_per_sitemap = self.settings.sitemap_max_urls
        url_chunks = [urls[i:i + max_urls_per_sitemap] 
                     for i in range(0, len(urls), max_urls_per_sitemap)]
        
        generated_files = []
        
        for chunk in url_chunks:
            filename = self._generate_single_sitemap(chunk)
            if filename:
                generated_files.append(filename)
        
        # Generate sitemap index if multiple sitemaps
        if len(generated_files) > 1:
            index_file = self._generate_sitemap_index(generated_files)
            if index_file:
                generated_files.insert(0, index_file)
        
        return generated_files
    
    def _generate_single_sitemap(self, urls: list) -> str:
        """Generate a single XML sitemap file"""
        try:
            # Create XML structure
            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            
            for url_obj in urls:
                url_element = ET.SubElement(urlset, 'url')
                
                # Required: location
                loc = ET.SubElement(url_element, 'loc')
                loc.text = url_obj.url
                
                # Optional: last modification date
                if url_obj.last_modified:
                    lastmod = ET.SubElement(url_element, 'lastmod')
                    lastmod.text = url_obj.last_modified.strftime('%Y-%m-%d')
                else:
                    lastmod = ET.SubElement(url_element, 'lastmod')
                    lastmod.text = datetime.utcnow().strftime('%Y-%m-%d')
                
                # Optional: change frequency
                if url_obj.changefreq:
                    changefreq = ET.SubElement(url_element, 'changefreq')
                    changefreq.text = url_obj.changefreq
                
                # Optional: priority
                if url_obj.priority:
                    priority = ET.SubElement(url_element, 'priority')
                    priority.text = str(url_obj.priority)
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f'sitemap_{timestamp}_{unique_id}.xml'
            filepath = os.path.join(Config.SITEMAP_DIR, filename)
            
            # Write XML to file
            tree = ET.ElementTree(urlset)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            
            # Save sitemap record to database
            sitemap_record = Sitemap()
            sitemap_record.filename = filename
            sitemap_record.url_count = len(urls)
            sitemap_record.submission_status = 'pending'
            db.session.add(sitemap_record)
            db.session.commit()
            
            logger.info(f"Generated sitemap: {filename} with {len(urls)} URLs")
            return filename
            
        except Exception as e:
            logger.error(f"Error generating sitemap: {str(e)}")
            return None
    
    def _generate_sitemap_index(self, sitemap_files: list) -> str:
        """Generate sitemap index file"""
        try:
            # Create XML structure for sitemap index
            sitemapindex = ET.Element('sitemapindex')
            sitemapindex.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            
            for sitemap_file in sitemap_files:
                sitemap_element = ET.SubElement(sitemapindex, 'sitemap')
                
                # Location of the sitemap
                loc = ET.SubElement(sitemap_element, 'loc')
                sitemap_url = urljoin(
                    self.settings.site_url.rstrip('/') + '/',
                    f'sitemaps/{sitemap_file}'
                )
                loc.text = sitemap_url
                
                # Last modification date
                lastmod = ET.SubElement(sitemap_element, 'lastmod')
                lastmod.text = datetime.utcnow().strftime('%Y-%m-%d')
            
            # Generate index filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            index_filename = f'sitemap_index_{timestamp}.xml'
            index_filepath = os.path.join(Config.SITEMAP_DIR, index_filename)
            
            # Write XML to file
            tree = ET.ElementTree(sitemapindex)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            tree.write(index_filepath, encoding='utf-8', xml_declaration=True)
            
            # Save sitemap index record
            sitemap_record = Sitemap()
            sitemap_record.filename = index_filename
            sitemap_record.url_count = sum(self._get_sitemap_url_count(f) for f in sitemap_files)
            sitemap_record.submission_status = 'pending'
            db.session.add(sitemap_record)
            db.session.commit()
            
            logger.info(f"Generated sitemap index: {index_filename}")
            return index_filename
            
        except Exception as e:
            logger.error(f"Error generating sitemap index: {str(e)}")
            return None
    
    def _get_sitemap_url_count(self, filename: str) -> int:
        """Get URL count for a sitemap file"""
        sitemap = Sitemap.query.filter_by(filename=filename).first()
        return sitemap.url_count if sitemap else 0
    
    def get_sitemap_url(self, filename: str) -> str:
        """Get full URL for a sitemap file"""
        return urljoin(
            self.settings.site_url.rstrip('/') + '/',
            f'sitemaps/{filename}'
        )
    
    def cleanup_old_sitemaps(self, keep_days: int = 30) -> int:
        """Remove old sitemap files and database records"""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        old_sitemaps = Sitemap.query.filter(
            Sitemap.created_at < cutoff_date
        ).all()
        
        removed_count = 0
        
        for sitemap in old_sitemaps:
            # Remove file if it exists
            filepath = os.path.join(Config.SITEMAP_DIR, sitemap.filename)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"Removed old sitemap file: {sitemap.filename}")
            except Exception as e:
                logger.error(f"Error removing sitemap file {sitemap.filename}: {str(e)}")
            
            # Remove database record
            db.session.delete(sitemap)
            removed_count += 1
        
        db.session.commit()
        logger.info(f"Cleaned up {removed_count} old sitemaps")
        return removed_count

def generate_sitemaps_for_urls(url_ids: list) -> list:
    """Convenience function to generate sitemaps"""
    generator = SitemapGenerator()
    return generator.generate_sitemaps(url_ids)
