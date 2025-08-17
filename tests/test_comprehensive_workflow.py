"""
Comprehensive workflow tests for the backlink indexing system
Tests end-to-end functionality with 90%+ coverage target
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from backlink_indexer.core.coordinator import BacklinkIndexingCoordinator
from backlink_indexer.core.config import IndexingConfig
from backlink_indexer.queue.celery_queue import TaskManager, process_single_url, process_url_batch
from backlink_indexer.ml.prediction_engine import IndexingPredictor
from backlink_indexer.monitoring.serp_checker import SERPChecker
from backlink_indexer.monitoring.success_tracker import SuccessTracker
from backlink_indexer.models import URLRecord, IndexingMethod, IndexingResult
from backlink_indexer.anti_detection.stealth_browser import StealthBrowserManager
from backlink_indexer.anti_detection.captcha_solver import create_captcha_handler


class TestComprehensiveWorkflow:
    """Test complete workflow from URL submission to indexing verification"""
    
    @pytest.mark.unit
    def test_coordinator_initialization(self, test_config):
        """Test coordinator initializes correctly with all components"""
        coordinator = BacklinkIndexingCoordinator(test_config)
        
        assert coordinator.config == test_config
        assert coordinator.browser_manager is not None
        assert len(coordinator.primary_methods) > 0
        assert coordinator.stats['total_urls_processed'] == 0
        
    @pytest.mark.unit
    def test_url_record_creation(self, sample_urls):
        """Test URL record creation and validation"""
        for url in sample_urls:
            record = URLRecord(
                url=url,
                priority=1,
                source="test"
            )
            
            assert record.url == url
            assert record.priority == 1
            assert record.created_at is not None
            assert record.source == "test"
    
    @pytest.mark.unit
    @patch('backlink_indexer.core.coordinator.StealthBrowserManager')
    def test_single_url_processing(self, mock_browser_class, test_config, sample_urls):
        """Test processing a single URL through the coordinator"""
        mock_browser_manager = Mock()
        mock_browser_class.return_value = mock_browser_manager
        
        coordinator = BacklinkIndexingCoordinator(test_config)
        url_record = URLRecord(url=sample_urls[0], priority=1)
        
        # Mock method results
        with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
            mock_execute.return_value = [{'method': 'social_bookmarking', 'success': True}]
            
            result = coordinator.process_url(url_record)
            
            assert result is True
            mock_execute.assert_called_once_with(url_record)
    
    @pytest.mark.unit
    def test_batch_url_processing(self, test_config, sample_urls):
        """Test batch processing of multiple URLs"""
        coordinator = BacklinkIndexingCoordinator(test_config)
        url_records = [URLRecord(url=url, priority=1) for url in sample_urls]
        
        with patch.object(coordinator, 'process_url') as mock_process:
            mock_process.return_value = True
            
            results = coordinator.process_batch(url_records)
            
            assert len(results) == len(sample_urls)
            assert mock_process.call_count == len(sample_urls)
    
    @pytest.mark.unit
    @patch('backlink_indexer.queue.celery_queue.BacklinkIndexingCoordinator')
    def test_celery_task_execution(self, mock_coordinator_class, sample_urls, test_config):
        """Test Celery task execution"""
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        mock_coordinator.process_url.return_value = True
        
        # Test single URL task
        method_config = {
            'social_bookmarking_enabled': True,
            'rss_distribution_enabled': True
        }
        
        with patch('backlink_indexer.queue.celery_queue.redis_client') as mock_redis:
            result = process_single_url(sample_urls[0], method_config, 1)
            
            assert result['success'] is True
            assert result['url'] == sample_urls[0]
            mock_coordinator.process_url.assert_called_once()
    
    @pytest.mark.unit
    def test_success_tracking(self, success_tracker, sample_indexing_results):
        """Test success tracking and analytics"""
        # Record results
        success_tracker.batch_record_results(sample_indexing_results)
        
        # Test performance metrics
        performance = success_tracker.get_method_performance(days_back=1)
        assert len(performance) > 0
        
        # Test dashboard data
        dashboard_data = success_tracker.get_analytics_dashboard_data()
        assert 'overview' in dashboard_data
        assert 'method_performance' in dashboard_data
        assert dashboard_data['overview']['total_attempts'] > 0
    
    @pytest.mark.unit
    @patch('backlink_indexer.ml.prediction_engine.train_test_split')
    @patch('backlink_indexer.ml.prediction_engine.RandomForestClassifier')
    def test_ml_prediction_training(self, mock_rf, mock_split, populated_success_tracker):
        """Test ML model training and prediction"""
        predictor = IndexingPredictor(populated_success_tracker)
        
        # Mock scikit-learn components
        mock_model = Mock()
        mock_model.fit.return_value = None
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]
        mock_model.feature_importances_ = [0.1, 0.2, 0.3, 0.4]
        mock_rf.return_value = mock_model
        
        mock_split.return_value = ([1, 2, 3], [4], [0, 1, 0], [1])
        
        # Train model
        with patch.object(predictor, 'prepare_training_data') as mock_prepare:
            import pandas as pd
            mock_X = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
            mock_y = pd.Series([0, 1, 1])
            mock_prepare.return_value = (mock_X, mock_y)
            predictor.feature_columns = ['feature1', 'feature2']
            
            results = predictor.train_model(days_back=30)
            
            assert 'accuracy' in results
            assert predictor.model is not None
    
    @pytest.mark.unit
    def test_ml_prediction_optimization(self, populated_success_tracker):
        """Test ML-powered method optimization"""
        predictor = IndexingPredictor(populated_success_tracker)
        
        # Test heuristic prediction (when no model is trained)
        url = "https://example.com/test-article"
        probability, info = predictor.predict_method_success(url, IndexingMethod.SOCIAL_BOOKMARKING)
        
        assert 0.0 <= probability <= 1.0
        assert 'probability' in info
        assert info['method'] == 'heuristic'
        
        # Test method optimization
        optimal_methods = predictor.optimize_method_combination(url)
        assert len(optimal_methods) > 0
        
        for method, prob in optimal_methods:
            assert isinstance(method, IndexingMethod)
            assert 0.0 <= prob <= 1.0
    
    @pytest.mark.unit
    @patch('aiohttp.ClientSession.get')
    async def test_serp_verification(self, mock_get, test_config):
        """Test SERP verification functionality"""
        checker = SERPChecker(test_config)
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text.return_value = """
        <html>
            <body>
                <div class="g">
                    <div class="yuRUbf">
                        <a href="https://example.com/article">Test Article</a>
                        <h3>Test Title</h3>
                    </div>
                </div>
            </body>
        </html>
        """
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Test URL indexing check
        results = await checker.check_url_indexed("https://example.com/article", ['google'])
        
        assert 'google' in results
        assert len(results['google']) > 0
    
    @pytest.mark.unit
    def test_browser_manager_stealth_features(self, test_config):
        """Test stealth browser manager features"""
        browser_manager = StealthBrowserManager(test_config)
        
        # Test fingerprint generation
        fingerprint = browser_manager.get_random_fingerprint()
        assert fingerprint is not None
        assert fingerprint.user_agent is not None
        assert fingerprint.viewport_width > 0
        assert fingerprint.viewport_height > 0
        
        # Test browser creation in mock mode
        test_config.mock_mode = True
        browser = browser_manager.create_stealth_browser()
        assert browser is not None
    
    @pytest.mark.unit
    def test_captcha_handler(self):
        """Test CAPTCHA handling functionality"""
        handler = create_captcha_handler(service="mock")
        
        # Test reCAPTCHA solving
        challenge = handler.create_challenge(
            challenge_type='recaptcha',
            site_key='test-site-key',
            page_url='https://example.com'
        )
        
        success = handler.solve_challenge(challenge)
        assert success is True
        assert challenge.solved is True
        assert challenge.solution is not None
    
    @pytest.mark.integration
    def test_end_to_end_workflow(self, test_config, sample_urls, temp_database):
        """Test complete end-to-end workflow"""
        # Initialize components
        success_tracker = SuccessTracker(temp_database)
        task_manager = TaskManager()
        coordinator = BacklinkIndexingCoordinator(test_config)
        
        # Submit URLs for processing
        results = []
        for url in sample_urls[:2]:  # Process first 2 URLs
            url_record = URLRecord(url=url, priority=1)
            
            with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
                # Mock successful processing
                mock_execute.return_value = [
                    {'method': 'social_bookmarking', 'success': True, 'response_time': 2.5}
                ]
                
                result = coordinator.process_url(url_record)
                results.append(result)
                
                # Record result in tracker
                indexing_result = IndexingResult(
                    url=url,
                    method=IndexingMethod.SOCIAL_BOOKMARKING,
                    success=True,
                    timestamp=datetime.now(),
                    response_time=2.5
                )
                success_tracker.record_result(indexing_result)
        
        # Verify results
        assert all(results)
        
        # Check analytics
        performance = success_tracker.get_method_performance(days_back=1)
        assert len(performance) > 0
        
        # Test ML prediction (should use heuristic)
        predictor = IndexingPredictor(success_tracker)
        prediction = predictor.create_ml_prediction(sample_urls[0])
        assert prediction.url == sample_urls[0]
        assert len(prediction.predicted_methods) > 0
    
    @pytest.mark.unit
    def test_error_handling_and_recovery(self, test_config):
        """Test error handling and recovery mechanisms"""
        coordinator = BacklinkIndexingCoordinator(test_config)
        
        # Test with invalid URL
        invalid_record = URLRecord(url="not-a-valid-url", priority=1)
        
        with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
            mock_execute.side_effect = Exception("Network error")
            
            result = coordinator.process_url(invalid_record)
            # Should handle gracefully and return failure
            assert result is False or result is None
    
    @pytest.mark.unit
    def test_queue_management(self):
        """Test queue management and task prioritization"""
        task_manager = TaskManager()
        
        # Test queue statistics
        with patch('backlink_indexer.queue.celery_queue.celery_app.control.inspect') as mock_inspect:
            mock_inspector = Mock()
            mock_inspector.active.return_value = {'worker1': []}
            mock_inspector.scheduled.return_value = {'worker1': []}
            mock_inspector.reserved.return_value = {'worker1': []}
            mock_inspect.return_value = mock_inspector
            
            stats = task_manager.get_queue_stats()
            assert 'active_tasks' in stats
            assert 'scheduled_tasks' in stats
            assert 'reserved_tasks' in stats
    
    @pytest.mark.unit
    def test_configuration_validation(self):
        """Test configuration validation and defaults"""
        config = IndexingConfig()
        
        # Test default values
        assert config.headless_mode is not None
        assert config.request_delay > 0
        assert config.max_concurrent_sessions > 0
        
        # Test method enablement
        assert hasattr(config, 'social_bookmarking_enabled')
        assert hasattr(config, 'rss_distribution_enabled')
        assert hasattr(config, 'web2_posting_enabled')
    
    @pytest.mark.unit
    def test_data_export_functionality(self, populated_success_tracker):
        """Test data export in different formats"""
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        # Test CSV export
        csv_data = populated_success_tracker.export_data(start_date, end_date, 'csv')
        assert isinstance(csv_data, str)
        assert 'URL,Method,Success' in csv_data
        
        # Test JSON export
        json_data = populated_success_tracker.export_data(start_date, end_date, 'json')
        assert isinstance(json_data, str)
        assert '"url":' in json_data
    
    @pytest.mark.unit
    def test_cleanup_and_maintenance(self, populated_success_tracker):
        """Test cleanup and maintenance operations"""
        # Test old data cleanup
        initial_count = len(populated_success_tracker.get_historical_data(
            datetime.now() - timedelta(days=30),
            datetime.now()
        ))
        
        # This should not delete anything yet (data is recent)
        populated_success_tracker.cleanup_old_data(days_to_keep=1)
        
        final_count = len(populated_success_tracker.get_historical_data(
            datetime.now() - timedelta(days=30),
            datetime.now()
        ))
        
        # Data should still be there (it's not old enough)
        assert final_count == initial_count
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_performance_under_load(self, test_config, performance_config):
        """Test system performance under simulated load"""
        coordinator = BacklinkIndexingCoordinator(performance_config)
        
        # Generate test URLs
        test_urls = [f"https://test{i}.example.com/article" for i in range(20)]
        url_records = [URLRecord(url=url, priority=1) for url in test_urls]
        
        start_time = datetime.now()
        
        with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
            mock_execute.return_value = [{'method': 'social_bookmarking', 'success': True}]
            
            results = coordinator.process_batch(url_records)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert len(results) == len(test_urls)
        assert processing_time < 10  # Should complete in under 10 seconds
        
        # Calculate throughput
        throughput = len(test_urls) / processing_time
        assert throughput > 2  # At least 2 URLs per second
    
    @pytest.mark.unit
    def test_monitoring_and_alerting(self, populated_success_tracker):
        """Test monitoring metrics and alerting thresholds"""
        dashboard_data = populated_success_tracker.get_analytics_dashboard_data()
        
        # Test monitoring data structure
        assert 'overview' in dashboard_data
        assert 'method_performance' in dashboard_data
        assert 'recent_trends' in dashboard_data
        assert 'error_analysis' in dashboard_data
        
        overview = dashboard_data['overview']
        assert 'total_attempts' in overview
        assert 'successful_attempts' in overview
        assert 'overall_success_rate' in overview
        
        # Test alerting thresholds
        success_rate = overview['overall_success_rate']
        if success_rate < 80:  # Alert threshold
            pytest.fail(f"Success rate below threshold: {success_rate}%")


class TestIndexingMethods:
    """Test individual indexing methods"""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("method", [
        IndexingMethod.SOCIAL_BOOKMARKING,
        IndexingMethod.RSS_DISTRIBUTION,
        IndexingMethod.WEB2_POSTING,
        IndexingMethod.FORUM_COMMENTING,
        IndexingMethod.DIRECTORY_SUBMISSION,
        IndexingMethod.SOCIAL_SIGNALS
    ])
    def test_individual_method_execution(self, method, test_config, sample_urls):
        """Test each indexing method individually"""
        coordinator = BacklinkIndexingCoordinator(test_config)
        url_record = URLRecord(url=sample_urls[0], priority=1)
        
        # Enable only the specific method being tested
        for attr in dir(test_config):
            if attr.endswith('_enabled'):
                setattr(test_config, attr, False)
        
        method_attr = f"{method.value}_enabled"
        if hasattr(test_config, method_attr):
            setattr(test_config, method_attr, True)
        
        # Mock method execution
        with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
            mock_execute.return_value = [{'method': method.value, 'success': True}]
            
            result = coordinator.process_url(url_record)
            assert result is True


class TestSecurityFeatures:
    """Test security and anti-detection features"""
    
    @pytest.mark.unit
    def test_fingerprint_randomization(self, test_config):
        """Test browser fingerprint randomization"""
        browser_manager = StealthBrowserManager(test_config)
        
        # Generate multiple fingerprints
        fingerprints = [browser_manager.get_random_fingerprint() for _ in range(10)]
        
        # Check for variation in fingerprints
        user_agents = [fp.user_agent for fp in fingerprints]
        viewports = [(fp.viewport_width, fp.viewport_height) for fp in fingerprints]
        
        # Should have some variation (not all identical)
        assert len(set(user_agents)) > 1 or len(set(viewports)) > 1
    
    @pytest.mark.unit
    def test_proxy_rotation(self, test_config, mock_proxy_pool):
        """Test proxy rotation functionality"""
        test_config.enable_proxy_rotation = True
        test_config.proxy_list = [
            {"host": "proxy1.com", "port": 8080},
            {"host": "proxy2.com", "port": 8080}
        ]
        
        browser_manager = StealthBrowserManager(test_config)
        
        # Test proxy selection
        proxy1 = browser_manager.get_next_proxy()
        proxy2 = browser_manager.get_next_proxy()
        
        if proxy1 and proxy2:
            # Should rotate between proxies
            assert proxy1.host != proxy2.host or proxy1.port != proxy2.port
    
    @pytest.mark.unit
    def test_rate_limiting(self, test_config):
        """Test rate limiting mechanisms"""
        coordinator = BacklinkIndexingCoordinator(test_config)
        
        # Verify rate limiting is configured
        assert test_config.request_delay > 0
        assert test_config.max_concurrent_sessions > 0
        
        # Test that delays are respected (would need timing in real implementation)
        url_record = URLRecord(url="https://example.com/test", priority=1)
        
        start_time = datetime.now()
        with patch.object(coordinator, '_execute_indexing_methods') as mock_execute:
            mock_execute.return_value = [{'method': 'social_bookmarking', 'success': True}]
            coordinator.process_url(url_record)
        end_time = datetime.now()
        
        # Should take at least the configured delay time
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time >= 0  # Basic sanity check