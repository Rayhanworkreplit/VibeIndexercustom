"""
Success tracking and analytics for backlink indexing performance
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import sqlite3
import json


@dataclass
class IndexingAttempt:
    """Data class for tracking individual indexing attempts"""
    url: str
    method: str
    platform: str
    success: bool
    timestamp: datetime
    response_time: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for indexing methods"""
    method_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    success_rate: float = 0.0
    average_response_time: float = 0.0
    last_24h_attempts: int = 0
    last_24h_success_rate: float = 0.0
    platforms_used: List[str] = field(default_factory=list)


class SuccessTracker:
    """Advanced success tracking and analytics system"""
    
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        self.db_path = getattr(config, 'database_path', 'backlink_analytics.db')
        self.setup_database()
        
        # In-memory cache for recent metrics
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = {}
        
    def setup_logging(self):
        """Configure logging for success tracking"""
        self.logger = logging.getLogger(f"{__name__}.SuccessTracker")
    
    def setup_database(self):
        """Initialize SQLite database for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indexing_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    method TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    timestamp DATETIME NOT NULL,
                    response_time REAL DEFAULT 0.0,
                    error_message TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    method TEXT NOT NULL,
                    total_attempts INTEGER DEFAULT 0,
                    successful_attempts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    average_response_time REAL DEFAULT 0.0,
                    platforms_data TEXT DEFAULT '[]',
                    UNIQUE(date, method)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS method_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    method TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    success_rate REAL DEFAULT 0.0,
                    total_attempts INTEGER DEFAULT 0,
                    last_updated DATETIME NOT NULL,
                    UNIQUE(method, platform)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON indexing_attempts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_method ON indexing_attempts(method)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_success ON indexing_attempts(success)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database setup failed: {str(e)}")
    
    async def record_attempt(self, attempt: IndexingAttempt):
        """Record an indexing attempt in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO indexing_attempts 
                (url, method, platform, success, timestamp, response_time, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt.url,
                attempt.method,
                attempt.platform,
                attempt.success,
                attempt.timestamp.isoformat(),
                attempt.response_time,
                attempt.error_message,
                json.dumps(attempt.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Update daily summary
            await self.update_daily_summary(attempt)
            
            # Clear cache for this method
            if attempt.method in self.metrics_cache:
                del self.metrics_cache[attempt.method]
            
        except Exception as e:
            self.logger.error(f"Failed to record attempt: {str(e)}")
    
    async def update_daily_summary(self, attempt: IndexingAttempt):
        """Update daily summary statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_str = attempt.timestamp.date().isoformat()
            
            # Get current day's stats
            cursor.execute('''
                SELECT total_attempts, successful_attempts, platforms_data
                FROM daily_summaries 
                WHERE date = ? AND method = ?
            ''', (date_str, attempt.method))
            
            result = cursor.fetchone()
            
            if result:
                total_attempts, successful_attempts, platforms_data = result
                platforms = json.loads(platforms_data)
            else:
                total_attempts = 0
                successful_attempts = 0
                platforms = []
            
            # Update counts
            total_attempts += 1
            if attempt.success:
                successful_attempts += 1
            
            # Track platforms
            if attempt.platform not in platforms:
                platforms.append(attempt.platform)
            
            # Calculate success rate
            success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
            
            # Upsert daily summary
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summaries 
                (date, method, total_attempts, successful_attempts, success_rate, platforms_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                attempt.method,
                total_attempts,
                successful_attempts,
                success_rate,
                json.dumps(platforms)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update daily summary: {str(e)}")
    
    async def get_method_performance(self, method_name: str, days: int = 7) -> PerformanceMetrics:
        """Get performance metrics for a specific method"""
        # Check cache first
        cache_key = f"{method_name}_{days}"
        if (cache_key in self.metrics_cache and 
            cache_key in self.last_cache_update and
            (datetime.now() - self.last_cache_update[cache_key]).seconds < self.cache_ttl):
            return self.metrics_cache[cache_key]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                    AVG(response_time) as avg_response_time,
                    GROUP_CONCAT(DISTINCT platform) as platforms
                FROM indexing_attempts 
                WHERE method = ? AND timestamp >= ?
            ''', (method_name, start_date.isoformat()))
            
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                total_attempts, successful_attempts, avg_response_time, platforms_str = result
                success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
                platforms = platforms_str.split(',') if platforms_str else []
            else:
                total_attempts = 0
                successful_attempts = 0
                success_rate = 0.0
                avg_response_time = 0.0
                platforms = []
            
            # Get last 24h stats
            last_24h_start = datetime.now() - timedelta(hours=24)
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts
                FROM indexing_attempts 
                WHERE method = ? AND timestamp >= ?
            ''', (method_name, last_24h_start.isoformat()))
            
            last_24h_result = cursor.fetchone()
            
            if last_24h_result and last_24h_result[0] > 0:
                last_24h_attempts, last_24h_successful = last_24h_result
                last_24h_success_rate = last_24h_successful / last_24h_attempts if last_24h_attempts > 0 else 0.0
            else:
                last_24h_attempts = 0
                last_24h_success_rate = 0.0
            
            conn.close()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                method_name=method_name,
                total_attempts=total_attempts,
                successful_attempts=successful_attempts,
                success_rate=success_rate,
                average_response_time=avg_response_time or 0.0,
                last_24h_attempts=last_24h_attempts,
                last_24h_success_rate=last_24h_success_rate,
                platforms_used=platforms
            )
            
            # Cache the result
            self.metrics_cache[cache_key] = metrics
            self.last_cache_update[cache_key] = datetime.now()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get method performance: {str(e)}")
            return PerformanceMetrics(method_name=method_name)
    
    async def get_overall_performance(self, days: int = 7) -> Dict[str, Any]:
        """Get overall performance across all methods"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                    COUNT(DISTINCT method) as methods_used,
                    COUNT(DISTINCT platform) as platforms_used,
                    AVG(response_time) as avg_response_time
                FROM indexing_attempts 
                WHERE timestamp >= ?
            ''', (start_date.isoformat(),))
            
            overall = cursor.fetchone()
            
            # Method breakdown
            cursor.execute('''
                SELECT 
                    method,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                    AVG(response_time) as avg_response_time
                FROM indexing_attempts 
                WHERE timestamp >= ?
                GROUP BY method
                ORDER BY successful_attempts DESC
            ''', (start_date.isoformat(),))
            
            method_breakdown = cursor.fetchall()
            
            # Platform breakdown
            cursor.execute('''
                SELECT 
                    platform,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts
                FROM indexing_attempts 
                WHERE timestamp >= ?
                GROUP BY platform
                ORDER BY successful_attempts DESC
            ''', (start_date.isoformat(),))
            
            platform_breakdown = cursor.fetchall()
            
            # Daily trends
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts
                FROM indexing_attempts 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (start_date.isoformat(),))
            
            daily_trends = cursor.fetchall()
            
            conn.close()
            
            # Format results
            if overall and overall[0] > 0:
                total_attempts, successful_attempts, methods_used, platforms_used, avg_response_time = overall
                overall_success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
            else:
                total_attempts = successful_attempts = methods_used = platforms_used = 0
                overall_success_rate = avg_response_time = 0.0
            
            # Format method breakdown
            methods = []
            for method_data in method_breakdown:
                method, attempts, successes, avg_time = method_data
                methods.append({
                    'method': method,
                    'total_attempts': attempts,
                    'successful_attempts': successes,
                    'success_rate': successes / attempts if attempts > 0 else 0.0,
                    'average_response_time': avg_time or 0.0
                })
            
            # Format platform breakdown
            platforms = []
            for platform_data in platform_breakdown:
                platform, attempts, successes = platform_data
                platforms.append({
                    'platform': platform,
                    'total_attempts': attempts,
                    'successful_attempts': successes,
                    'success_rate': successes / attempts if attempts > 0 else 0.0
                })
            
            # Format daily trends
            trends = []
            for trend_data in daily_trends:
                date, attempts, successes = trend_data
                trends.append({
                    'date': date,
                    'total_attempts': attempts,
                    'successful_attempts': successes,
                    'success_rate': successes / attempts if attempts > 0 else 0.0
                })
            
            return {
                'overall': {
                    'total_attempts': total_attempts,
                    'successful_attempts': successful_attempts,
                    'success_rate': overall_success_rate,
                    'methods_used': methods_used,
                    'platforms_used': platforms_used,
                    'average_response_time': avg_response_time or 0.0
                },
                'method_breakdown': methods,
                'platform_breakdown': platforms,
                'daily_trends': trends,
                'period_days': days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get overall performance: {str(e)}")
            return {}
    
    async def get_failure_analysis(self, method_name: str = None, days: int = 7) -> Dict[str, Any]:
        """Analyze failure patterns and common errors"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Base query for failures
            base_query = '''
                FROM indexing_attempts 
                WHERE success = 0 AND timestamp >= ?
            '''
            params = [start_date.isoformat()]
            
            if method_name:
                base_query += ' AND method = ?'
                params.append(method_name)
            
            # Error message analysis
            cursor.execute(f'''
                SELECT error_message, COUNT(*) as count
                {base_query}
                AND error_message != ''
                GROUP BY error_message
                ORDER BY count DESC
                LIMIT 10
            ''', params)
            
            error_messages = cursor.fetchall()
            
            # Platform failure rates
            cursor.execute(f'''
                SELECT 
                    platform,
                    COUNT(*) as failed_attempts,
                    (SELECT COUNT(*) FROM indexing_attempts ia2 
                     WHERE ia2.platform = indexing_attempts.platform 
                     AND ia2.timestamp >= ? {"AND ia2.method = ?" if method_name else ""}) as total_attempts
                {base_query}
                GROUP BY platform
                ORDER BY failed_attempts DESC
            ''', params + params[:1 + (1 if method_name else 0)])
            
            platform_failures = cursor.fetchall()
            
            # Time-based failure analysis
            cursor.execute(f'''
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as failed_attempts
                {base_query}
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            ''', params)
            
            hourly_failures = cursor.fetchall()
            
            conn.close()
            
            # Format results
            common_errors = [
                {'error': error, 'count': count}
                for error, count in error_messages
            ]
            
            platform_analysis = []
            for platform, failed, total in platform_failures:
                failure_rate = failed / total if total > 0 else 0.0
                platform_analysis.append({
                    'platform': platform,
                    'failed_attempts': failed,
                    'total_attempts': total,
                    'failure_rate': failure_rate
                })
            
            hourly_analysis = [
                {'hour': int(hour), 'failed_attempts': count}
                for hour, count in hourly_failures
            ]
            
            return {
                'common_errors': common_errors,
                'platform_analysis': platform_analysis,
                'hourly_failure_pattern': hourly_analysis,
                'method': method_name,
                'period_days': days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze failures: {str(e)}")
            return {}
    
    async def get_success_predictions(self, method_name: str) -> Dict[str, Any]:
        """Predict success rates based on historical data"""
        try:
            # Get recent performance data
            metrics = await self.get_method_performance(method_name, days=30)
            
            # Simple trend analysis
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get daily success rates for trend analysis
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
                FROM indexing_attempts 
                WHERE method = ? AND timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (method_name,))
            
            daily_rates = cursor.fetchall()
            conn.close()
            
            if len(daily_rates) < 3:
                return {
                    'predicted_success_rate': metrics.success_rate,
                    'confidence': 'low',
                    'trend': 'stable',
                    'recommendation': 'insufficient_data'
                }
            
            # Calculate trend
            rates = [rate[1] for rate in daily_rates]
            recent_rates = rates[-7:]  # Last 7 days
            older_rates = rates[-14:-7] if len(rates) >= 14 else rates[:-7]
            
            if older_rates:
                recent_avg = sum(recent_rates) / len(recent_rates)
                older_avg = sum(older_rates) / len(older_rates)
                trend_direction = 'improving' if recent_avg > older_avg else 'declining' if recent_avg < older_avg else 'stable'
            else:
                trend_direction = 'stable'
            
            # Predict next success rate (simple moving average)
            predicted_rate = sum(recent_rates) / len(recent_rates) if recent_rates else metrics.success_rate
            
            # Confidence based on consistency
            rate_variance = sum((r - predicted_rate) ** 2 for r in recent_rates) / len(recent_rates) if recent_rates else 0
            confidence = 'high' if rate_variance < 0.05 else 'medium' if rate_variance < 0.15 else 'low'
            
            # Recommendation
            if predicted_rate > 0.8:
                recommendation = 'continue_current_strategy'
            elif predicted_rate > 0.5:
                recommendation = 'optimize_parameters'
            else:
                recommendation = 'review_and_adjust'
            
            return {
                'predicted_success_rate': predicted_rate,
                'confidence': confidence,
                'trend': trend_direction,
                'recommendation': recommendation,
                'recent_performance': recent_rates,
                'variance': rate_variance
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate predictions: {str(e)}")
            return {}
    
    def export_analytics_data(self, method_name: str = None, days: int = 30) -> str:
        """Export analytics data to JSON"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = '''
                SELECT * FROM indexing_attempts 
                WHERE timestamp >= ?
            '''
            params = [start_date.isoformat()]
            
            if method_name:
                query += ' AND method = ?'
                params.append(method_name)
            
            query += ' ORDER BY timestamp DESC'
            
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                record = dict(zip(columns, row))
                # Parse metadata JSON
                if record['metadata']:
                    try:
                        record['metadata'] = json.loads(record['metadata'])
                    except:
                        record['metadata'] = {}
                data.append(record)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'method_filter': method_name,
                'period_days': days,
                'total_records': len(data),
                'data': data
            }
            
            return json.dumps(export_data, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Failed to export data: {str(e)}")
            return json.dumps({'error': str(e)})