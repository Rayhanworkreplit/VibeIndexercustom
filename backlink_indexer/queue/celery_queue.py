"""
Celery-based distributed task queue for backlink indexing
Handles priority queues, retry logic, and batch processing
"""

import time
import logging
from typing import List, Dict, Any, Optional
from celery import Celery, Task
from celery.exceptions import Retry
from datetime import datetime, timedelta
import redis
from ..models import URLRecord, IndexingTask, TaskStatus

# Initialize Celery app
celery_app = Celery(
    'backlink_indexer',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'backlink_indexer.queue.celery_queue.process_url_batch': {'queue': 'high_priority'},
        'backlink_indexer.queue.celery_queue.process_single_url': {'queue': 'normal_priority'},
        'backlink_indexer.queue.celery_queue.retry_failed_url': {'queue': 'retry_queue'},
    },
    task_annotations={
        'backlink_indexer.queue.celery_queue.process_url_batch': {'rate_limit': '10/m'},
        'backlink_indexer.queue.celery_queue.process_single_url': {'rate_limit': '50/m'},
    }
)

redis_client = redis.Redis(host='localhost', port=6379, db=0)


class IndexingTask(Task):
    """Base task class with retry logic and error handling"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False


@celery_app.task(base=IndexingTask, bind=True)
def process_url_batch(self, urls: List[str], method_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a batch of URLs with specified indexing methods
    High priority task for bulk operations
    """
    logger = logging.getLogger(__name__)
    results = {
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        from ..core.coordinator import BacklinkIndexingCoordinator
        from ..core.config import IndexingConfig
        
        # Create config from method_config
        config = IndexingConfig()
        for key, value in method_config.items():
            setattr(config, key, value)
        
        coordinator = BacklinkIndexingCoordinator(config)
        
        for url in urls:
            try:
                # Process each URL
                url_record = URLRecord(
                    url=url,
                    priority=method_config.get('priority', 1),
                    created_at=datetime.utcnow()
                )
                
                # Execute indexing methods
                success = coordinator.process_url(url_record)
                
                if success:
                    results['successful'] += 1
                    logger.info(f"Successfully processed URL: {url}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to process URL: {url}")
                    
                results['processed'] += 1
                
                # Add delay between requests to avoid rate limiting
                time.sleep(config.request_delay)
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {url}: {str(e)}")
                logger.error(f"Error processing URL {url}: {str(e)}")
        
        # Update task status in Redis
        task_key = f"task:{self.request.id}"
        redis_client.hset(task_key, mapping={
            'status': 'completed',
            'processed': results['processed'],
            'successful': results['successful'],
            'failed': results['failed'],
            'completed_at': datetime.utcnow().isoformat()
        })
        redis_client.expire(task_key, 86400)  # Expire after 24 hours
        
        return results
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        
        # Update task status as failed
        task_key = f"task:{self.request.id}"
        redis_client.hset(task_key, mapping={
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat()
        })
        
        # Retry with exponential backoff
        raise self.retry(countdown=2 ** self.request.retries)


@celery_app.task(base=IndexingTask, bind=True)
def process_single_url(self, url: str, method_config: Dict[str, Any], priority: int = 1) -> Dict[str, Any]:
    """
    Process a single URL with specified indexing methods
    Normal priority task for individual URLs
    """
    logger = logging.getLogger(__name__)
    
    try:
        from ..core.coordinator import BacklinkIndexingCoordinator
        from ..core.config import IndexingConfig
        
        # Create config
        config = IndexingConfig()
        for key, value in method_config.items():
            setattr(config, key, value)
        
        coordinator = BacklinkIndexingCoordinator(config)
        
        # Create URL record
        url_record = URLRecord(
            url=url,
            priority=priority,
            created_at=datetime.utcnow()
        )
        
        # Process the URL
        success = coordinator.process_url(url_record)
        
        result = {
            'url': url,
            'success': success,
            'processed_at': datetime.utcnow().isoformat(),
            'task_id': self.request.id
        }
        
        # Update Redis with result
        task_key = f"task:{self.request.id}"
        redis_client.hset(task_key, mapping={
            'status': 'completed',
            'success': success,
            'url': url,
            'completed_at': datetime.utcnow().isoformat()
        })
        redis_client.expire(task_key, 86400)
        
        if success:
            logger.info(f"Successfully processed URL: {url}")
        else:
            logger.warning(f"Failed to process URL: {url}")
            
        return result
        
    except Exception as e:
        logger.error(f"Single URL processing failed for {url}: {str(e)}")
        
        # Schedule for retry queue
        retry_failed_url.delay(url, method_config, priority, self.request.retries + 1)
        
        raise self.retry(countdown=2 ** self.request.retries)


@celery_app.task(base=IndexingTask, bind=True)
def retry_failed_url(self, url: str, method_config: Dict[str, Any], priority: int, attempt: int) -> Dict[str, Any]:
    """
    Retry failed URLs with exponential backoff
    Low priority retry queue
    """
    logger = logging.getLogger(__name__)
    
    if attempt > 5:  # Maximum retry attempts
        logger.error(f"URL {url} failed after maximum retry attempts")
        
        # Store in failed URLs pool
        failed_key = f"failed_urls:{datetime.utcnow().date()}"
        redis_client.sadd(failed_key, url)
        redis_client.expire(failed_key, 604800)  # Keep for 7 days
        
        return {
            'url': url,
            'status': 'permanently_failed',
            'final_attempt': attempt
        }
    
    try:
        # Wait before retry (exponential backoff)
        backoff_delay = min(300, (2 ** attempt) * 60)  # Cap at 5 minutes
        time.sleep(backoff_delay)
        
        # Retry processing
        result = process_single_url(url, method_config, priority)
        
        if result['success']:
            logger.info(f"URL {url} succeeded on retry attempt {attempt}")
        else:
            logger.warning(f"URL {url} failed on retry attempt {attempt}")
            
        return result
        
    except Exception as e:
        logger.error(f"Retry attempt {attempt} failed for {url}: {str(e)}")
        
        # Schedule next retry
        next_attempt = attempt + 1
        if next_attempt <= 5:
            retry_failed_url.apply_async(
                args=[url, method_config, priority, next_attempt],
                countdown=min(600, (2 ** next_attempt) * 120)  # Longer delays for subsequent retries
            )
        
        return {
            'url': url,
            'status': 'retry_scheduled',
            'attempt': attempt,
            'next_attempt': next_attempt if next_attempt <= 5 else None
        }


class TaskManager:
    """High-level task management interface"""
    
    def __init__(self):
        self.redis_client = redis_client
        
    def submit_batch(self, urls: List[str], method_config: Dict[str, Any]) -> str:
        """Submit a batch of URLs for processing"""
        task = process_url_batch.delay(urls, method_config)
        
        # Store batch info in Redis
        batch_key = f"batch:{task.id}"
        self.redis_client.hset(batch_key, mapping={
            'task_id': task.id,
            'url_count': len(urls),
            'submitted_at': datetime.utcnow().isoformat(),
            'status': 'submitted'
        })
        self.redis_client.expire(batch_key, 86400)
        
        return task.id
    
    def submit_single_url(self, url: str, method_config: Dict[str, Any], priority: int = 1) -> str:
        """Submit a single URL for processing"""
        task = process_single_url.delay(url, method_config, priority)
        return task.id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status from Redis"""
        task_key = f"task:{task_id}"
        status = self.redis_client.hgetall(task_key)
        
        if not status:
            return {'status': 'not_found'}
            
        # Convert bytes to strings
        return {k.decode(): v.decode() for k, v in status.items()}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            inspect = celery_app.control.inspect()
            
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            
            stats = {
                'active_tasks': sum(len(tasks) for tasks in (active_tasks or {}).values()),
                'scheduled_tasks': sum(len(tasks) for tasks in (scheduled_tasks or {}).values()),
                'reserved_tasks': sum(len(tasks) for tasks in (reserved_tasks or {}).values()),
                'failed_urls_today': self.redis_client.scard(f"failed_urls:{datetime.utcnow().date()}")
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"Error getting queue stats: {str(e)}")
            return {'error': str(e)}
    
    def get_failed_urls(self, date: Optional[str] = None) -> List[str]:
        """Get failed URLs for a specific date"""
        if not date:
            date = datetime.utcnow().date()
        
        failed_key = f"failed_urls:{date}"
        failed_urls = self.redis_client.smembers(failed_key)
        
        return [url.decode() for url in failed_urls]
    
    def retry_failed_urls(self, date: Optional[str] = None, method_config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Retry all failed URLs for a specific date"""
        failed_urls = self.get_failed_urls(date)
        
        if not method_config:
            method_config = {
                'social_bookmarking_enabled': True,
                'rss_distribution_enabled': True,
                'web2_posting_enabled': True
            }
        
        task_ids = []
        for url in failed_urls:
            task_id = self.submit_single_url(url, method_config, priority=0)  # Low priority
            task_ids.append(task_id)
            
        return task_ids


# Export the task manager instance
task_manager = TaskManager()