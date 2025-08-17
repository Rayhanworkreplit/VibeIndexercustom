"""
Data models for the backlink indexing system
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"


class IndexingMethod(Enum):
    """Available indexing methods"""
    SOCIAL_BOOKMARKING = "social_bookmarking"
    RSS_DISTRIBUTION = "rss_distribution"
    WEB2_POSTING = "web2_posting"
    FORUM_COMMENTING = "forum_commenting"
    DIRECTORY_SUBMISSION = "directory_submission"
    SOCIAL_SIGNALS = "social_signals"


@dataclass
class URLRecord:
    """Represents a URL to be indexed"""
    url: str
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    created_at: datetime = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class IndexingTask:
    """Represents an indexing task"""
    task_id: str
    url: str
    method: IndexingMethod
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    result_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class IndexingResult:
    """Result of an indexing operation"""
    url: str
    method: IndexingMethod
    success: bool
    timestamp: datetime
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    verification_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MethodPerformance:
    """Performance metrics for an indexing method"""
    method: IndexingMethod
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    average_response_time: float = 0.0
    success_rate: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
    
    def update_stats(self, success: bool, response_time: float):
        """Update performance statistics"""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
        
        # Update average response time
        self.average_response_time = (
            (self.average_response_time * (self.total_attempts - 1) + response_time)
            / self.total_attempts
        )
        
        # Update success rate
        self.success_rate = self.successful_attempts / self.total_attempts if self.total_attempts > 0 else 0.0
        
        self.last_updated = datetime.utcnow()


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"  # http, https, socks4, socks5
    active: bool = True
    last_used: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def proxy_url(self) -> str:
        """Generate proxy URL string"""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate proxy success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class BrowserFingerprint:
    """Browser fingerprint for anti-detection"""
    user_agent: str
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    timezone: str
    language: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SERPResult:
    """Search Engine Results Page verification result"""
    url: str
    query: str
    search_engine: str  # google, bing, yandex, etc.
    position: Optional[int] = None
    found: bool = False
    checked_at: datetime = None
    snippet: Optional[str] = None
    title: Optional[str] = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()


@dataclass
class MLPrediction:
    """Machine learning prediction for method selection"""
    url: str
    predicted_methods: List[IndexingMethod]
    confidence_scores: Dict[IndexingMethod, float]
    model_version: str
    prediction_timestamp: datetime = None
    
    def __post_init__(self):
        if self.prediction_timestamp is None:
            self.prediction_timestamp = datetime.utcnow()


@dataclass
class CaptchaChallenge:
    """CAPTCHA challenge information"""
    challenge_id: str
    challenge_type: str  # recaptcha, hcaptcha, text, image
    site_key: Optional[str] = None
    challenge_data: Optional[Dict[str, Any]] = None
    solution: Optional[str] = None
    solved: bool = False
    created_at: datetime = None
    solved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class IndexingCampaign:
    """Represents an indexing campaign with multiple URLs and methods"""
    campaign_id: str
    name: str
    urls: List[str]
    enabled_methods: List[IndexingMethod]
    priority: int = 1
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "created"
    progress: float = 0.0
    results: List[IndexingResult] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.results is None:
            self.results = []