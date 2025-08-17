import json
import logging
import time
from datetime import datetime
from typing import Dict, List

from app import db
from models import TaskQueue, URL
from services.url_validator import validate_single_url
from services.sitemap_generator import generate_sitemaps_for_urls
from services.gsc_client import submit_sitemap_to_gsc, harvest_gsc_feedback
import asyncio

logger = logging.getLogger(__name__)

class TaskProcessor:
    """Background task processor"""
    
    def __init__(self):
        self.processors = {
            'validate_url': self._process_validation_task,
            'generate_sitemap': self._process_sitemap_task,
            'submit_sitemap': self._process_sitemap_submission_task,
            'harvest_gsc': self._process_gsc_harvest_task,
            'advanced_indexing': self._process_advanced_indexing_task,
        }
    
    def process_tasks(self, limit: int = 10) -> int:
        """Process pending tasks"""
        # Get pending tasks ordered by priority and creation time
        tasks = TaskQueue.query.filter_by(status='pending').order_by(
            TaskQueue.priority.asc(),
            TaskQueue.created_at.asc()
        ).limit(limit).all()
        
        processed_count = 0
        
        for task in tasks:
            try:
                # Mark task as processing
                task.status = 'processing'
                task.started_at = datetime.utcnow()
                db.session.commit()
                
                # Process the task
                processor = self.processors.get(task.task_type)
                if processor:
                    result = processor(task)
                    
                    # Update task with result
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    task.result = json.dumps(result) if result else None
                    
                else:
                    # Unknown task type
                    task.status = 'failed'
                    task.error_message = f"Unknown task type: {task.task_type}"
                
                processed_count += 1
                
            except Exception as e:
                # Handle task failure
                task.status = 'failed'
                task.error_message = str(e)
                task.retry_count += 1
                
                # Retry if under max retries
                if task.retry_count < task.max_retries:
                    task.status = 'pending'
                    task.started_at = None
                    logger.warning(f"Task {task.id} failed, will retry: {str(e)}")
                else:
                    logger.error(f"Task {task.id} failed permanently: {str(e)}")
            
            finally:
                db.session.commit()
        
        return processed_count
    
    def _process_validation_task(self, task: TaskQueue) -> Dict:
        """Process URL validation task"""
        try:
            payload = json.loads(task.payload) if task.payload else {}
            url_id = payload.get('url_id')
            
            if not url_id:
                raise ValueError("Missing url_id in task payload")
            
            # Validate the URL
            result = validate_single_url(url_id)
            
            return {
                'url_id': url_id,
                'validation_result': result
            }
            
        except Exception as e:
            logger.error(f"Error processing validation task {task.id}: {str(e)}")
            raise
    
    def _process_sitemap_task(self, task: TaskQueue) -> Dict:
        """Process sitemap generation task"""
        try:
            payload = json.loads(task.payload) if task.payload else {}
            url_ids = payload.get('url_ids', [])
            
            if not url_ids:
                raise ValueError("Missing url_ids in task payload")
            
            # Generate sitemaps
            generated_files = generate_sitemaps_for_urls(url_ids)
            
            # Queue submission tasks for generated sitemaps
            for filename in generated_files:
                queue_sitemap_submission_task(filename)
            
            return {
                'url_ids': url_ids,
                'generated_files': generated_files
            }
            
        except Exception as e:
            logger.error(f"Error processing sitemap task {task.id}: {str(e)}")
            raise
    
    def _process_sitemap_submission_task(self, task: TaskQueue) -> Dict:
        """Process sitemap submission task"""
        try:
            payload = json.loads(task.payload) if task.payload else {}
            filename = payload.get('filename')
            
            if not filename:
                raise ValueError("Missing filename in task payload")
            
            # Submit sitemap to GSC
            success = submit_sitemap_to_gsc(filename)
            
            return {
                'filename': filename,
                'submitted': success
            }
            
        except Exception as e:
            logger.error(f"Error processing sitemap submission task {task.id}: {str(e)}")
            raise
    
    def _process_gsc_harvest_task(self, task: TaskQueue) -> Dict:
        """Process GSC feedback harvest task"""
        try:
            payload = json.loads(task.payload) if task.payload else {}
            limit = payload.get('limit', 100)
            
            # Harvest GSC feedback
            harvested_count = harvest_gsc_feedback(limit=limit)
            
            return {
                'harvested_count': harvested_count
            }
            
        except Exception as e:
            logger.error(f"Error processing GSC harvest task {task.id}: {str(e)}")
            raise
    
    def _process_advanced_indexing_task(self, task: TaskQueue) -> Dict:
        """Process advanced 6-layer indexing campaign task"""
        try:
            payload = json.loads(task.payload) if task.payload else {}
            url_ids = payload.get('url_ids', [])
            
            if not url_ids:
                raise ValueError("Missing url_ids in task payload")
            
            # Import here to avoid circular imports
            from services.advanced_indexing import execute_advanced_indexing_campaign
            
            # Execute the campaign (this is async, so we need to handle it)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(execute_advanced_indexing_campaign(url_ids))
            finally:
                loop.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing advanced indexing task {task.id}: {str(e)}")
            raise

# Task queue management functions

def queue_validation_task(url_id: int, priority: int = 5) -> TaskQueue:
    """Queue a URL validation task"""
    payload = json.dumps({'url_id': url_id})
    
    task = TaskQueue()
    task.task_type = 'validate_url'
    task.payload = payload
    task.priority = priority
    
    db.session.add(task)
    db.session.commit()
    
    logger.info(f"Queued validation task for URL {url_id}")
    return task

def queue_sitemap_task(url_ids: List[int], priority: int = 3) -> TaskQueue:
    """Queue a sitemap generation task"""
    payload = json.dumps({'url_ids': url_ids})
    
    task = TaskQueue()
    task.task_type = 'generate_sitemap'
    task.payload = payload
    task.priority = priority
    
    db.session.add(task)
    db.session.commit()
    
    logger.info(f"Queued sitemap generation task for {len(url_ids)} URLs")
    return task

def queue_sitemap_submission_task(filename: str, priority: int = 2) -> TaskQueue:
    """Queue a sitemap submission task"""
    payload = json.dumps({'filename': filename})
    
    task = TaskQueue()
    task.task_type = 'submit_sitemap'
    task.payload = payload
    task.priority = priority
    
    db.session.add(task)
    db.session.commit()
    
    logger.info(f"Queued sitemap submission task for {filename}")
    return task

def queue_gsc_harvest_task(limit: int = 100, priority: int = 4) -> TaskQueue:
    """Queue a GSC feedback harvest task"""
    payload = json.dumps({'limit': limit})
    
    task = TaskQueue()
    task.task_type = 'harvest_gsc'
    task.payload = payload
    task.priority = priority
    
    db.session.add(task)
    db.session.commit()
    
    logger.info("Queued GSC harvest task")
    return task


def queue_advanced_indexing_task(url_ids: List[int], priority: int = 1) -> TaskQueue:
    """Queue advanced 6-layer indexing campaign task"""
    payload = json.dumps({
        'url_ids': url_ids,
        'campaign_type': '6_layer_strategy'
    })
    
    task = TaskQueue()
    task.task_type = 'advanced_indexing'
    task.payload = payload
    task.priority = priority
    
    db.session.add(task)
    db.session.commit()
    
    logger.info(f"Queued advanced indexing campaign for {len(url_ids)} URLs")
    return task

def process_pending_tasks(limit: int = 10) -> int:
    """Process pending background tasks"""
    processor = TaskProcessor()
    return processor.process_tasks(limit=limit)

def cleanup_completed_tasks(keep_days: int = 7) -> int:
    """Clean up old completed/failed tasks"""
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
    
    old_tasks = TaskQueue.query.filter(
        TaskQueue.status.in_(['completed', 'failed']),
        TaskQueue.completed_at < cutoff_date
    ).all()
    
    count = len(old_tasks)
    
    for task in old_tasks:
        db.session.delete(task)
    
    db.session.commit()
    
    logger.info(f"Cleaned up {count} old tasks")
    return count

def get_task_stats() -> Dict:
    """Get task queue statistics"""
    stats = {
        'pending': TaskQueue.query.filter_by(status='pending').count(),
        'processing': TaskQueue.query.filter_by(status='processing').count(),
        'completed': TaskQueue.query.filter_by(status='completed').count(),
        'failed': TaskQueue.query.filter_by(status='failed').count(),
    }
    
    stats['total'] = sum(stats.values())
    return stats
