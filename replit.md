# Google Indexing Pipeline

## Overview

This is a production-grade Python web application that automates Google indexing through comprehensive URL discovery, validation, sitemap generation, and Google Search Console integration. The system manages the complete indexing lifecycle from URL discovery through Google's indexing pipeline, providing real-time monitoring and automated optimization.

The application serves as a centralized indexing management system that discovers URLs from multiple sources (sitemaps, crawling, manual input), validates each URL against Google's indexing requirements, generates optimized XML sitemaps, and monitors indexing status through Google Search Console API integration.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework Architecture
- **Flask-based web application** with SQLAlchemy ORM for database operations
- **Template-driven UI** using Jinja2 templates with Bootstrap for responsive design
- **Modular service architecture** separating concerns across discovery, validation, sitemap generation, and Google API integration
- **Background task processing** system for handling long-running operations like URL validation and sitemap generation

### Database Architecture
- **SQLAlchemy with SQLite** as the default database (configurable via DATABASE_URL environment variable)
- **URL-centric data model** with core entities: URL, CrawlResult, Sitemap, GSCFeedback, TaskQueue, Settings, and IndexingStats
- **Relationship mapping** between URLs and their crawl results, with cascade deletion for data integrity
- **Status tracking** system with defined states: pending, ready, indexed, error

### Service Layer Architecture
- **URL Discovery Service**: Discovers URLs from XML sitemaps, with support for sitemap indexes and regular sitemaps
- **URL Validation Service**: Performs comprehensive validation including robots.txt checking, HTTP status verification, content analysis, and SEO validation
- **Sitemap Generator**: Creates paginated XML sitemaps with configurable URL limits per sitemap file
- **Background Task Processor**: Queue-based system for processing validation, sitemap generation, and GSC operations asynchronously

### Authentication & Authorization
- **Google Service Account authentication** for Google Search Console API access
- **Session-based web authentication** with configurable secret keys
- **Environment-based credential management** supporting both JSON credentials and service account files

## External Dependencies

### Google Services Integration
- **Google Search Console API** (searchconsole v1) for sitemap submission and indexing feedback collection
- **Google OAuth2 service account authentication** for programmatic API access
- **Service account credentials** configured via GSC_SERVICE_ACCOUNT_FILE or GSC_SERVICE_ACCOUNT_JSON environment variables

### Third-Party Libraries
- **httpx** for HTTP client operations with timeout and redirect handling
- **BeautifulSoup** for HTML parsing and content extraction
- **trafilatura** for advanced content extraction and analysis
- **Chart.js** for dashboard visualization and analytics
- **Bootstrap** (via CDN) for responsive UI components
- **Font Awesome** for consistent iconography

### Development & Deployment
- **Flask development server** with debug mode for local development
- **ProxyFix middleware** for handling reverse proxy deployments
- **Environment variable configuration** for deployment flexibility
- **SQLite database** with connection pooling and health checks enabled

### API Dependencies
- **Google Search Console API scopes**: webmasters scope for property management
- **XML parsing** for sitemap processing and generation
- **robots.txt parsing** for crawl permission validation
- **Content hashing** (MD5) for change detection and duplicate content identification