"""
Configuration management for the backlink indexing system
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from pathlib import Path


@dataclass
class IndexingConfig:
    """Configuration for the backlink indexing system"""
    
    # Browser automation settings
    max_concurrent_browsers: int = 10
    browser_pool_size: int = 20
    headless_mode: bool = True
    mock_mode: bool = False  # For testing without browser automation
    
    # Anti-detection settings
    min_delay_between_actions: float = 2.0
    max_delay_between_actions: float = 8.0
    human_typing_speed_range: Tuple[float, float] = (0.05, 0.15)
    mouse_movement_probability: float = 0.3
    
    # Proxy and rotation settings
    enable_proxy_rotation: bool = True
    proxy_rotation_interval: int = 50  # requests
    user_agent_rotation_interval: int = 25
    proxy_pool: List[str] = field(default_factory=list)
    
    # Indexing method settings
    social_bookmarking_enabled: bool = True
    rss_distribution_enabled: bool = True
    web2_posting_enabled: bool = True
    forum_commenting_enabled: bool = True
    directory_submission_enabled: bool = True
    social_signals_enabled: bool = True
    
    # Performance settings
    batch_size: int = 100
    retry_attempts: int = 3
    success_threshold: float = 0.95  # 95% target success rate
    
    # Database settings
    database_path: str = "backlink_indexer.db"
    enable_analytics: bool = True
    
    # Platform-specific settings
    platform_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'reddit': {
            'enabled': True,
            'accounts': [],
            'rate_limit': 5,  # submissions per hour
            'authority_score': 95
        },
        'stumbleupon': {
            'enabled': True, 
            'accounts': [],
            'rate_limit': 10,
            'authority_score': 88
        },
        'blogger': {
            'enabled': True,
            'accounts': [],
            'rate_limit': 3,
            'authority_score': 85
        },
        'wordpress': {
            'enabled': True,
            'accounts': [],
            'rate_limit': 5,
            'authority_score': 90
        }
    })
    
    @classmethod
    def from_env(cls) -> 'IndexingConfig':
        """Create configuration from environment variables"""
        config = cls()
        
        # Load basic settings from environment
        config.max_concurrent_browsers = int(os.getenv('MAX_CONCURRENT_BROWSERS', '10'))
        config.headless_mode = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
        config.enable_proxy_rotation = os.getenv('ENABLE_PROXY_ROTATION', 'true').lower() == 'true'
        config.success_threshold = float(os.getenv('SUCCESS_THRESHOLD', '0.95'))
        
        # Load proxy pool from environment or file
        proxy_list = os.getenv('PROXY_LIST', '')
        if proxy_list:
            config.proxy_pool = proxy_list.split(',')
        elif os.path.exists('proxies.txt'):
            with open('proxies.txt', 'r') as f:
                config.proxy_pool = [line.strip() for line in f if line.strip()]
        
        return config
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        import json
        
        # Convert to dict, handling non-serializable types
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, tuple):
                config_dict[key] = list(value)
            else:
                config_dict[key] = value
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'IndexingConfig':
        """Load configuration from JSON file"""
        import json
        
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key):
                # Convert lists back to tuples where needed
                if key == 'human_typing_speed_range' and isinstance(value, list):
                    setattr(config, key, tuple(value))
                else:
                    setattr(config, key, value)
        
        return config


@dataclass 
class URLRecord:
    """Data model for tracking URL indexing status"""
    url: str
    status: str = "pending"
    methods_attempted: List[str] = field(default_factory=list)
    methods_successful: List[str] = field(default_factory=list)
    attempts: int = 0
    last_attempt: str = ""  # ISO format datetime string
    indexed_date: str = ""  # ISO format datetime string
    error_messages: List[str] = field(default_factory=list)
    success_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Configuration constants
PROVEN_INDEXING_PATTERNS = {
    'social_bookmarking': {
        'platforms': ['reddit', 'stumbleupon', 'digg', 'delicious'],
        'submission_frequency': '1-3 per day per platform',
        'content_variation': 'minimum 3 unique descriptions',
        'account_aging': 'minimum 30 days before use'
    },
    'web2_properties': {
        'platforms': ['blogger', 'wordpress', 'tumblr', 'medium'],
        'posting_frequency': '2-4 posts per week',
        'content_length': '300-800 words',
        'internal_linking': '2-3 contextual links per post'
    },
    'rss_distribution': {
        'feed_aggregators': ['feedburner', 'feedage', 'technorati'],
        'ping_services': ['ping-o-matic', 'pingler', 'feedshark'],
        'update_frequency': 'daily to weekly',
        'feed_quality': 'minimum 10 quality items'
    }
}

EXPECTED_SUCCESS_RATES = {
    'social_bookmarking': 0.75,
    'rss_distribution': 0.85,
    'web2_posting': 0.80,
    'forum_commenting': 0.65,
    'directory_submission': 0.70,
    'social_signals': 0.60
}