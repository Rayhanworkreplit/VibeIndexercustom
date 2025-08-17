"""
Pytest configuration and fixtures for backlink indexer tests
"""

import pytest
import os
import tempfile
from unittest.mock import Mock
from datetime import datetime
from backlink_indexer.core.config import IndexingConfig
from backlink_indexer.models import URLRecord, IndexingResult, IndexingMethod
from backlink_indexer.monitoring.success_tracker import SuccessTracker


@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    database_url = f"sqlite:///{temp_db.name}"
    
    yield database_url
    
    # Cleanup
    os.unlink(temp_db.name)


@pytest.fixture
def test_config():
    """Create a test configuration with mock mode enabled"""
    config = IndexingConfig()
    config.mock_mode = True
    config.headless_mode = True
    config.request_delay = 0.1  # Faster for tests
    config.max_concurrent_sessions = 2
    config.enable_proxy_rotation = False
    
    # Enable all methods for comprehensive testing
    config.social_bookmarking_enabled = True
    config.rss_distribution_enabled = True
    config.web2_posting_enabled = True
    config.forum_commenting_enabled = True
    config.directory_submission_enabled = True
    config.social_signals_enabled = True
    
    return config


@pytest.fixture
def sample_urls():
    """Provide sample URLs for testing"""
    return [
        "https://example.com/article-1",
        "https://example.com/blog/post-2",
        "https://test-site.com/product/item-3",
        "https://news-site.com/2023/breaking-news",
        "https://blog.example.org/category/tech/post-5"
    ]


@pytest.fixture
def sample_url_records(sample_urls):
    """Create sample URLRecord objects"""
    records = []
    for i, url in enumerate(sample_urls):
        record = URLRecord(
            url=url,
            priority=1 if i < 2 else 2,
            created_at=datetime.now(),
            source="test"
        )
        records.append(record)
    
    return records


@pytest.fixture
def sample_indexing_results(sample_urls):
    """Create sample IndexingResult objects"""
    results = []
    methods = list(IndexingMethod)
    
    for i, url in enumerate(sample_urls):
        for j, method in enumerate(methods):
            success = (i + j) % 3 != 0  # Mix of success and failure
            response_time = 2.0 + (i * 0.5)
            
            result = IndexingResult(
                url=url,
                method=method,
                success=success,
                timestamp=datetime.now(),
                response_time=response_time,
                status_code=200 if success else 400
            )
            results.append(result)
    
    return results


@pytest.fixture
def mock_browser_manager():
    """Create a mock browser manager for testing"""
    mock_manager = Mock()
    mock_browser = Mock()
    
    # Mock browser methods
    mock_browser.get.return_value = None
    mock_browser.find_element.return_value = Mock()
    mock_browser.find_elements.return_value = [Mock(), Mock()]
    mock_browser.execute_script.return_value = "mock_result"
    mock_browser.quit.return_value = None
    
    mock_manager.create_stealth_browser.return_value = mock_browser
    mock_manager.human_like_typing.return_value = None
    mock_manager.human_like_scroll.return_value = None
    mock_manager.wait_with_human_delay.return_value = None
    
    return mock_manager


@pytest.fixture
def success_tracker(temp_database):
    """Create a SuccessTracker instance with temporary database"""
    tracker = SuccessTracker(temp_database)
    return tracker


@pytest.fixture
def populated_success_tracker(success_tracker, sample_indexing_results):
    """Create a SuccessTracker populated with test data"""
    success_tracker.batch_record_results(sample_indexing_results)
    return success_tracker


@pytest.fixture
def mock_celery_task():
    """Create a mock Celery task for testing"""
    mock_task = Mock()
    mock_task.request.id = "test-task-123"
    mock_task.request.retries = 0
    mock_task.retry.side_effect = lambda countdown: None
    
    return mock_task


@pytest.fixture
def test_environment():
    """Set up test environment variables"""
    original_env = {}
    
    test_env_vars = {
        'DATABASE_URL': 'sqlite:///test.db',
        'REDIS_URL': 'redis://localhost:6379/15',  # Use test DB
        'SESSION_SECRET': 'test-secret-key',
        'MOCK_MODE': 'true',
        'LOG_LEVEL': 'DEBUG'
    }
    
    # Save original values
    for key in test_env_vars:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env_vars[key]
    
    yield test_env_vars
    
    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_response():
    """Create a mock HTTP response for testing"""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Mock response content</body></html>"
    mock_resp.json.return_value = {"status": "success", "data": "mock_data"}
    mock_resp.headers = {"Content-Type": "text/html"}
    
    return mock_resp


# Async test fixtures
@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Performance test fixtures
@pytest.fixture
def performance_config():
    """Configuration optimized for performance testing"""
    config = IndexingConfig()
    config.mock_mode = True  # Use mock for speed
    config.request_delay = 0.01  # Minimal delay
    config.max_concurrent_sessions = 10
    config.enable_proxy_rotation = False
    
    return config


# Mock external services
@pytest.fixture
def mock_captcha_solver():
    """Mock CAPTCHA solver for testing"""
    mock_solver = Mock()
    mock_solver.solve_recaptcha.return_value = "mock_captcha_solution"
    mock_solver.solve_hcaptcha.return_value = "mock_hcaptcha_solution"
    mock_solver.solve_text_captcha.return_value = "MOCK123"
    
    return mock_solver


@pytest.fixture
def mock_proxy_pool():
    """Mock proxy pool for testing"""
    from backlink_indexer.models import ProxyConfig
    
    proxies = [
        ProxyConfig(
            host="mock-proxy-1.com",
            port=8080,
            username="test_user",
            password="test_pass",
            proxy_type="http"
        ),
        ProxyConfig(
            host="mock-proxy-2.com",
            port=8080,
            proxy_type="https"
        )
    ]
    
    return proxies


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatically cleanup after each test"""
    yield
    # Add any cleanup logic here
    pass


# Markers for different test categories
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_chrome: mark test as requiring Chrome browser"
    )
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "requires_postgres: mark test as requiring PostgreSQL"
    )


# Skip tests based on available services
@pytest.fixture
def skip_if_no_chrome():
    """Skip test if Chrome is not available"""
    try:
        import undetected_chromedriver as uc
        # Try to create a browser instance
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        driver = uc.Chrome(options=options)
        driver.quit()
    except Exception:
        pytest.skip("Chrome browser not available")


@pytest.fixture
def skip_if_no_redis():
    """Skip test if Redis is not available"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=15)
        r.ping()
    except Exception:
        pytest.skip("Redis not available")


@pytest.fixture
def skip_if_no_postgres():
    """Skip test if PostgreSQL is not available"""
    try:
        import psycopg2
        # Try to connect to test database
        conn = psycopg2.connect(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        conn.close()
    except Exception:
        pytest.skip("PostgreSQL not available")


# Parameterized fixtures for comprehensive testing
@pytest.fixture(params=[
    IndexingMethod.SOCIAL_BOOKMARKING,
    IndexingMethod.RSS_DISTRIBUTION,
    IndexingMethod.WEB2_POSTING,
    IndexingMethod.FORUM_COMMENTING,
    IndexingMethod.DIRECTORY_SUBMISSION,
    IndexingMethod.SOCIAL_SIGNALS
])
def indexing_method(request):
    """Parameterized fixture for all indexing methods"""
    return request.param


@pytest.fixture(params=[1, 2, 3])
def priority_level(request):
    """Parameterized fixture for priority levels"""
    return request.param


@pytest.fixture(params=[True, False])
def success_status(request):
    """Parameterized fixture for success/failure scenarios"""
    return request.param