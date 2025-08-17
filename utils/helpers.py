import re
import logging
from urllib.parse import urlparse, urlunparse, urljoin
from typing import Optional

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if URL is valid and HTTP/HTTPS"""
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url.strip())
        return (
            bool(parsed.scheme) and 
            bool(parsed.netloc) and
            parsed.scheme.lower() in ('http', 'https')
        )
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments, trailing slashes, etc."""
    if not url:
        return url
    
    try:
        parsed = urlparse(url.strip())
        
        # Remove fragment
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/') if parsed.path != '/' else parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        return normalized
    except Exception:
        return url

def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL"""
    if not is_valid_url(url):
        return None
    
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None

def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain"""
    domain1 = get_domain_from_url(url1)
    domain2 = get_domain_from_url(url2)
    
    return domain1 is not None and domain1 == domain2

def extract_base_url(url: str) -> Optional[str]:
    """Extract base URL (scheme + netloc)"""
    if not is_valid_url(url):
        return None
    
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None

def clean_text(text: str, max_length: int = None) -> str:
    """Clean and truncate text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length-3] + '...'
    
    return cleaned

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"

def extract_urls_from_text(text: str) -> list:
    """Extract URLs from text using regex"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    urls = url_pattern.findall(text)
    return [url for url in urls if is_valid_url(url)]

def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate string with suffix"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_url_path_parts(url: str) -> list:
    """Get URL path parts as list"""
    if not is_valid_url(url):
        return []
    
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return path.split('/') if path else []
    except Exception:
        return []

def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes"""
    if not text:
        return 0
    
    word_count = len(text.split())
    reading_time = max(1, round(word_count / words_per_minute))
    return reading_time

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system storage"""
    if not filename:
        return "untitled"
    
    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)  # Remove control characters
    sanitized = sanitized.strip('. ')  # Remove leading/trailing dots and spaces
    
    # Ensure not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized[:255]  # Limit length

def parse_sitemap_frequency(freq: str) -> int:
    """Convert sitemap changefreq to days"""
    freq_map = {
        'always': 0,
        'hourly': 0,
        'daily': 1,
        'weekly': 7,
        'monthly': 30,
        'yearly': 365,
        'never': 9999
    }
    
    return freq_map.get(freq.lower(), 7)  # Default to weekly

def calculate_url_priority(url: str, depth: int = None, content_length: int = None) -> float:
    """Calculate URL priority for sitemap (0.0 to 1.0)"""
    priority = 0.5  # Default priority
    
    # Adjust based on URL depth
    if depth is not None:
        if depth == 0:  # Homepage
            priority = 1.0
        elif depth == 1:  # Main sections
            priority = 0.8
        elif depth == 2:  # Sub-sections
            priority = 0.6
        else:  # Deep pages
            priority = 0.4
    
    # Adjust based on content length
    if content_length is not None:
        if content_length > 5000:  # Long content
            priority += 0.1
        elif content_length < 500:  # Short content
            priority -= 0.1
    
    # Ensure priority is within bounds
    return max(0.1, min(1.0, priority))

def is_indexable_url(url: str) -> bool:
    """Check if URL is generally indexable (basic heuristics)"""
    if not is_valid_url(url):
        return False
    
    # Check for common non-indexable patterns
    non_indexable_patterns = [
        r'/admin/', r'/login/', r'/logout/', r'/auth/',
        r'/api/', r'/ajax/', r'/json/', r'/xml/',
        r'/search/', r'/filter/', r'/sort/',
        r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|tar|gz)$',
        r'[?&]utm_', r'[?&]ref=', r'[?&]source=',
    ]
    
    for pattern in non_indexable_patterns:
        if re.search(pattern, url.lower()):
            return False
    
    return True
