"""
Success tracking and analytics for backlink indexing
Stores metrics in PostgreSQL and provides comprehensive reporting
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import create_model, Column, Integer, String, Boolean, Float, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from ..models import IndexingResult, IndexingMethod, MethodPerformance
import os

Base = declarative_base()


class IndexingResultRecord(Base):
    """SQLAlchemy model for indexing results"""
    __tablename__ = 'indexing_results'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False, index=True)
    method = Column(String(50), nullable=False, index=True)
    success = Column(Boolean, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    response_time = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    verification_url = Column(String(2048), nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string
    
    # Composite indexes for better query performance
    __table_args__ = (
        Index('idx_method_timestamp', 'method', 'timestamp'),
        Index('idx_success_timestamp', 'success', 'timestamp'),
        Index('idx_url_method', 'url', 'method'),
    )


class CampaignRecord(Base):
    """SQLAlchemy model for indexing campaigns"""
    __tablename__ = 'indexing_campaigns'
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, index=True)
    total_urls = Column(Integer, nullable=False)
    processed_urls = Column(Integer, default=0)
    successful_urls = Column(Integer, default=0)
    failed_urls = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    metadata = Column(Text, nullable=True)


class MethodPerformanceRecord(Base):
    """SQLAlchemy model for method performance tracking"""
    __tablename__ = 'method_performance'
    
    id = Column(Integer, primary_key=True)
    method = Column(String(50), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('idx_method_date', 'method', 'date'),
    )


class SuccessTracker:
    """
    Comprehensive success tracking and analytics system
    Provides real-time metrics and historical analysis
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///indexing_analytics.db')
        self.engine = None
        self.Session = None
        self.logger = logging.getLogger(__name__)
        
        self._initialize_database()
        
        # Cache for performance metrics
        self._performance_cache = {}
        self._cache_expiry = None
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            from sqlalchemy import create_engine
            
            self.engine = create_engine(
                self.database_url,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def record_result(self, result: IndexingResult):
        """Record an indexing result in the database"""
        session = self.Session()
        
        try:
            # Convert metadata to JSON string if present
            metadata_json = None
            if result.metadata:
                import json
                metadata_json = json.dumps(result.metadata)
            
            record = IndexingResultRecord(
                url=result.url,
                method=result.method.value,
                success=result.success,
                timestamp=result.timestamp,
                response_time=result.response_time,
                status_code=result.status_code,
                error_message=result.error_message,
                verification_url=result.verification_url,
                metadata=metadata_json
            )
            
            session.add(record)
            session.commit()
            
            # Update method performance cache
            self._update_method_performance(result.method, result.success, result.response_time)
            
            self.logger.debug(f"Recorded result for {result.url} using {result.method.value}")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error recording result: {str(e)}")
            raise
        finally:
            session.close()
    
    def batch_record_results(self, results: List[IndexingResult]):
        """Record multiple results in a single transaction"""
        session = self.Session()
        
        try:
            records = []
            for result in results:
                metadata_json = None
                if result.metadata:
                    import json
                    metadata_json = json.dumps(result.metadata)
                
                record = IndexingResultRecord(
                    url=result.url,
                    method=result.method.value,
                    success=result.success,
                    timestamp=result.timestamp,
                    response_time=result.response_time,
                    status_code=result.status_code,
                    error_message=result.error_message,
                    verification_url=result.verification_url,
                    metadata=metadata_json
                )
                records.append(record)
            
            session.add_all(records)
            session.commit()
            
            # Update performance metrics
            for result in results:
                self._update_method_performance(result.method, result.success, result.response_time)
            
            self.logger.info(f"Recorded {len(results)} results in batch")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error recording batch results: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_historical_data(self, start_date: datetime, end_date: datetime) -> List[IndexingResult]:
        """Retrieve historical indexing results within date range"""
        session = self.Session()
        
        try:
            records = session.query(IndexingResultRecord).filter(
                IndexingResultRecord.timestamp.between(start_date, end_date)
            ).order_by(IndexingResultRecord.timestamp).all()
            
            results = []
            for record in records:
                # Parse metadata if present
                metadata = None
                if record.metadata:
                    import json
                    try:
                        metadata = json.loads(record.metadata)
                    except json.JSONDecodeError:
                        pass
                
                result = IndexingResult(
                    url=record.url,
                    method=IndexingMethod(record.method),
                    success=record.success,
                    timestamp=record.timestamp,
                    response_time=record.response_time,
                    status_code=record.status_code,
                    error_message=record.error_message,
                    verification_url=record.verification_url,
                    metadata=metadata
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_method_performance(self, method: IndexingMethod = None, 
                              days_back: int = 30) -> Dict[str, MethodPerformance]:
        """Get performance metrics for indexing methods"""
        
        # Check cache first
        cache_key = f"{method}_{days_back}" if method else f"all_{days_back}"
        if self._cache_expiry and datetime.now() < self._cache_expiry:
            if cache_key in self._performance_cache:
                return self._performance_cache[cache_key]
        
        session = self.Session()
        
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Build query
            query = session.query(
                IndexingResultRecord.method,
                func.count(IndexingResultRecord.id).label('total_attempts'),
                func.sum(func.cast(IndexingResultRecord.success, Integer)).label('successful_attempts'),
                func.avg(IndexingResultRecord.response_time).label('avg_response_time')
            ).filter(
                IndexingResultRecord.timestamp >= start_date
            )
            
            if method:
                query = query.filter(IndexingResultRecord.method == method.value)
            
            results = query.group_by(IndexingResultRecord.method).all()
            
            performance_metrics = {}
            
            for row in results:
                method_enum = IndexingMethod(row.method)
                total_attempts = row.total_attempts or 0
                successful_attempts = row.successful_attempts or 0
                failed_attempts = total_attempts - successful_attempts
                avg_response_time = row.avg_response_time or 0.0
                success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0.0
                
                performance = MethodPerformance(
                    method=method_enum,
                    total_attempts=total_attempts,
                    successful_attempts=successful_attempts,
                    failed_attempts=failed_attempts,
                    average_response_time=avg_response_time,
                    success_rate=success_rate
                )
                
                performance_metrics[method_enum.value] = performance
            
            # Cache results
            self._performance_cache[cache_key] = performance_metrics
            self._cache_expiry = datetime.now() + timedelta(minutes=15)  # Cache for 15 minutes
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting method performance: {str(e)}")
            return {}
        finally:
            session.close()
    
    def _update_method_performance(self, method: IndexingMethod, success: bool, response_time: float):
        """Update cached method performance metrics"""
        # This is a simple in-memory cache update
        # In production, you might want to use Redis or similar
        pass
    
    def get_success_rates_by_timeframe(self, timeframe: str = 'daily', days_back: int = 30) -> Dict[str, Any]:
        """Get success rates aggregated by timeframe (daily, hourly)"""
        session = self.Session()
        
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            
            if timeframe == 'daily':
                date_format = func.date(IndexingResultRecord.timestamp)
            elif timeframe == 'hourly':
                date_format = func.date_trunc('hour', IndexingResultRecord.timestamp)
            else:
                raise ValueError("Timeframe must be 'daily' or 'hourly'")
            
            results = session.query(
                date_format.label('period'),
                IndexingResultRecord.method,
                func.count(IndexingResultRecord.id).label('total'),
                func.sum(func.cast(IndexingResultRecord.success, Integer)).label('successful')
            ).filter(
                IndexingResultRecord.timestamp >= start_date
            ).group_by(
                date_format, IndexingResultRecord.method
            ).order_by(date_format).all()
            
            # Process results
            timeframe_data = {}
            for row in results:
                period = row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period)
                method = row.method
                total = row.total
                successful = row.successful or 0
                success_rate = (successful / total * 100) if total > 0 else 0.0
                
                if period not in timeframe_data:
                    timeframe_data[period] = {}
                
                timeframe_data[period][method] = {
                    'total': total,
                    'successful': successful,
                    'success_rate': success_rate
                }
            
            return timeframe_data
            
        except Exception as e:
            self.logger.error(f"Error getting success rates by timeframe: {str(e)}")
            return {}
        finally:
            session.close()
    
    def get_analytics_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard"""
        
        session = self.Session()
        
        try:
            # Overall statistics (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            overall_stats = session.query(
                func.count(IndexingResultRecord.id).label('total_attempts'),
                func.sum(func.cast(IndexingResultRecord.success, Integer)).label('successful_attempts'),
                func.avg(IndexingResultRecord.response_time).label('avg_response_time'),
                func.count(func.distinct(IndexingResultRecord.url)).label('unique_urls')
            ).filter(
                IndexingResultRecord.timestamp >= thirty_days_ago
            ).first()
            
            total_attempts = overall_stats.total_attempts or 0
            successful_attempts = overall_stats.successful_attempts or 0
            overall_success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0.0
            
            # Method performance
            method_performance = self.get_method_performance(days_back=30)
            
            # Recent trends (last 7 days)
            recent_trends = self.get_success_rates_by_timeframe('daily', 7)
            
            # Top performing URLs
            top_urls = session.query(
                IndexingResultRecord.url,
                func.count(IndexingResultRecord.id).label('attempts'),
                func.sum(func.cast(IndexingResultRecord.success, Integer)).label('successes')
            ).filter(
                IndexingResultRecord.timestamp >= thirty_days_ago,
                IndexingResultRecord.success == True
            ).group_by(
                IndexingResultRecord.url
            ).order_by(
                func.count(IndexingResultRecord.id).desc()
            ).limit(10).all()
            
            # Error analysis
            error_analysis = session.query(
                IndexingResultRecord.error_message,
                func.count(IndexingResultRecord.id).label('count')
            ).filter(
                IndexingResultRecord.timestamp >= thirty_days_ago,
                IndexingResultRecord.success == False,
                IndexingResultRecord.error_message.isnot(None)
            ).group_by(
                IndexingResultRecord.error_message
            ).order_by(
                func.count(IndexingResultRecord.id).desc()
            ).limit(10).all()
            
            dashboard_data = {
                'overview': {
                    'total_attempts': total_attempts,
                    'successful_attempts': successful_attempts,
                    'overall_success_rate': overall_success_rate,
                    'unique_urls': overall_stats.unique_urls or 0,
                    'avg_response_time': overall_stats.avg_response_time or 0.0
                },
                'method_performance': {
                    method: {
                        'success_rate': perf.success_rate,
                        'total_attempts': perf.total_attempts,
                        'avg_response_time': perf.average_response_time
                    }
                    for method, perf in method_performance.items()
                },
                'recent_trends': recent_trends,
                'top_performing_urls': [
                    {
                        'url': row.url,
                        'attempts': row.attempts,
                        'successes': row.successes,
                        'success_rate': (row.successes / row.attempts * 100) if row.attempts > 0 else 0
                    }
                    for row in top_urls
                ],
                'error_analysis': [
                    {
                        'error_message': row.error_message[:100] + '...' if len(row.error_message or '') > 100 else row.error_message,
                        'count': row.count
                    }
                    for row in error_analysis
                ]
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {str(e)}")
            return {}
        finally:
            session.close()
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old tracking data to manage database size"""
        session = self.Session()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Delete old results
            deleted_count = session.query(IndexingResultRecord).filter(
                IndexingResultRecord.timestamp < cutoff_date
            ).delete()
            
            # Delete old performance records
            session.query(MethodPerformanceRecord).filter(
                MethodPerformanceRecord.date < cutoff_date
            ).delete()
            
            session.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} old tracking records")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error cleaning up old data: {str(e)}")
        finally:
            session.close()
    
    def export_data(self, start_date: datetime, end_date: datetime, 
                   format: str = 'csv') -> str:
        """Export tracking data in specified format"""
        
        results = self.get_historical_data(start_date, end_date)
        
        if format == 'csv':
            return self._export_to_csv(results)
        elif format == 'json':
            return self._export_to_json(results)
        else:
            raise ValueError("Supported formats: csv, json")
    
    def _export_to_csv(self, results: List[IndexingResult]) -> str:
        """Export results to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'URL', 'Method', 'Success', 'Timestamp', 'Response Time',
            'Status Code', 'Error Message', 'Verification URL'
        ])
        
        # Write data
        for result in results:
            writer.writerow([
                result.url,
                result.method.value,
                result.success,
                result.timestamp.isoformat(),
                result.response_time,
                result.status_code,
                result.error_message,
                result.verification_url
            ])
        
        return output.getvalue()
    
    def _export_to_json(self, results: List[IndexingResult]) -> str:
        """Export results to JSON format"""
        import json
        
        data = []
        for result in results:
            data.append({
                'url': result.url,
                'method': result.method.value,
                'success': result.success,
                'timestamp': result.timestamp.isoformat(),
                'response_time': result.response_time,
                'status_code': result.status_code,
                'error_message': result.error_message,
                'verification_url': result.verification_url,
                'metadata': result.metadata
            })
        
        return json.dumps(data, indent=2)