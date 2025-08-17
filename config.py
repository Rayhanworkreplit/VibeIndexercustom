import os

class Config:
    # Google Search Console API settings
    GSC_SERVICE_ACCOUNT_FILE = os.environ.get('GSC_SERVICE_ACCOUNT_FILE', 'service-account.json')
    GSC_SCOPES = ['https://www.googleapis.com/auth/webmasters']
    
    # Crawling settings
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; CustomIndexer/1.0; +https://example.com/bot)'
    REQUEST_TIMEOUT = 10
    MAX_REDIRECTS = 5
    
    # Rate limiting
    REQUESTS_PER_SECOND = 2
    CONCURRENT_REQUESTS = 5
    
    # Sitemap settings
    SITEMAP_DIR = 'sitemaps'
    SITEMAP_BASE_URL = '/sitemaps/'
