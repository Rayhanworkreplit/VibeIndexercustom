from datetime import datetime
from app import db
from sqlalchemy import func

class URL(db.Model):
    """Main URL tracking table"""
    __tablename__ = 'urls'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(2048), unique=True, nullable=False, index=True)
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    priority = db.Column(db.Float, default=0.5)
    changefreq = db.Column(db.String(20), default='weekly')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_checked = db.Column(db.DateTime)
    last_modified = db.Column(db.DateTime)
    last_indexed = db.Column(db.DateTime)
    
    # Validation results
    last_error = db.Column(db.Text)
    validation_issues = db.Column(db.Text)  # JSON string of issues
    
    # SEO data
    title = db.Column(db.String(512))
    meta_description = db.Column(db.Text)
    content_hash = db.Column(db.String(32))  # MD5 hash of content
    
    # Relationships
    crawls = db.relationship('CrawlResult', backref='url', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<URL {self.url}>'
    
    @property
    def is_eligible(self):
        """Check if URL is eligible for sitemap inclusion"""
        return self.status == 'ready'
    
    @property
    def latest_crawl(self):
        """Get the most recent crawl result"""
        return self.crawls.order_by(CrawlResult.created_at.desc()).first()

class CrawlResult(db.Model):
    """Individual crawl results for tracking history"""
    __tablename__ = 'crawl_results'
    
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'), nullable=False, index=True)
    
    # HTTP response data
    status_code = db.Column(db.Integer)
    response_time = db.Column(db.Float)  # in seconds
    content_length = db.Column(db.Integer)
    content_type = db.Column(db.String(100))
    
    # Validation results
    robots_allowed = db.Column(db.Boolean)
    has_noindex = db.Column(db.Boolean)
    canonical_ok = db.Column(db.Boolean)
    canonical_url = db.Column(db.String(2048))
    
    # Content analysis
    content_hash = db.Column(db.String(32))
    word_count = db.Column(db.Integer)
    has_structured_data = db.Column(db.Boolean)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    validation_errors = db.Column(db.Text)  # JSON string of specific errors
    
    def __repr__(self):
        return f'<CrawlResult {self.url_id} - {self.status_code}>'

class Sitemap(db.Model):
    """Generated sitemap tracking"""
    __tablename__ = 'sitemaps'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    url_count = db.Column(db.Integer, default=0)
    
    # Status tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime)
    last_fetch_at = db.Column(db.DateTime)
    
    # GSC feedback
    submission_status = db.Column(db.String(50))  # submitted, processed, error
    fetch_status = db.Column(db.String(50))
    errors_count = db.Column(db.Integer, default=0)
    warnings_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Sitemap {self.filename}>'

class GSCFeedback(db.Model):
    """Google Search Console feedback data"""
    __tablename__ = 'gsc_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'), nullable=False, index=True)
    
    # Index status from GSC
    index_status = db.Column(db.String(100))  # e.g., 'Submitted and indexed', 'Discovered - not indexed'
    coverage_state = db.Column(db.String(100))
    last_crawled = db.Column(db.DateTime)
    
    # Issues from GSC
    blocking_issue = db.Column(db.String(255))
    warning_issue = db.Column(db.String(255))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    url = db.relationship('URL', backref='gsc_feedback')
    
    def __repr__(self):
        return f'<GSCFeedback {self.url_id} - {self.index_status}>'

class TaskQueue(db.Model):
    """Background task queue for processing"""
    __tablename__ = 'task_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False, index=True)  # validate, sitemap, gsc_harvest
    payload = db.Column(db.Text)  # JSON data for the task
    
    # Status tracking
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    priority = db.Column(db.Integer, default=5, index=True)  # Lower number = higher priority
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Results
    result = db.Column(db.Text)  # JSON result data
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    def __repr__(self):
        return f'<TaskQueue {self.task_type} - {self.status}>'

class Settings(db.Model):
    """Application settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Site configuration
    site_url = db.Column(db.String(255), nullable=False)
    gsc_property_url = db.Column(db.String(255), nullable=False)
    
    # Crawling settings
    max_crawl_rate = db.Column(db.Integer, default=50)  # URLs per hour
    crawl_delay = db.Column(db.Float, default=1.0)  # Seconds between requests
    
    # Sitemap settings
    sitemap_max_urls = db.Column(db.Integer, default=50000)
    auto_submit_sitemaps = db.Column(db.Boolean, default=True)
    
    # Notification settings
    slack_webhook_url = db.Column(db.String(500))
    email_alerts = db.Column(db.String(255))
    alert_on_deindex = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Settings {self.site_url}>'

class IndexingStats(db.Model):
    """Daily indexing statistics"""
    __tablename__ = 'indexing_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    
    # URL counts
    total_urls = db.Column(db.Integer, default=0)
    ready_urls = db.Column(db.Integer, default=0)
    indexed_urls = db.Column(db.Integer, default=0)
    error_urls = db.Column(db.Integer, default=0)
    pending_urls = db.Column(db.Integer, default=0)
    
    # Activity counts
    urls_crawled = db.Column(db.Integer, default=0)
    sitemaps_generated = db.Column(db.Integer, default=0)
    sitemaps_submitted = db.Column(db.Integer, default=0)
    
    # Performance metrics
    avg_response_time = db.Column(db.Float)
    success_rate = db.Column(db.Float)
    
    def __repr__(self):
        return f'<IndexingStats {self.date}>'
