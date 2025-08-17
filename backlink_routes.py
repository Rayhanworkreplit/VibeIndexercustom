"""
Flask routes for the backlink indexer functionality
"""

import asyncio
import json
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify, flash, redirect, url_for
from backlink_indexer.core.config import IndexingConfig
from backlink_indexer.core.coordinator import BacklinkIndexingCoordinator

# Create blueprint for backlink routes
backlink_bp = Blueprint('backlink', __name__, url_prefix='/backlink')

# Global coordinator instance (will be initialized per request)
coordinator_instance = None


@backlink_bp.route('/')
def dashboard():
    """Backlink indexer dashboard"""
    return render_template('backlink/dashboard.html')


@backlink_bp.route('/config', methods=['GET', 'POST'])
def config():
    """Configure backlink indexer settings"""
    
    if request.method == 'POST':
        try:
            # Get form data and create config
            config_data = {
                'max_concurrent_browsers': int(request.form.get('max_concurrent_browsers', 10)),
                'headless_mode': request.form.get('headless_mode') == 'on',
                'social_bookmarking_enabled': request.form.get('social_bookmarking_enabled') == 'on',
                'rss_distribution_enabled': request.form.get('rss_distribution_enabled') == 'on',
                'web2_posting_enabled': request.form.get('web2_posting_enabled') == 'on',
                'success_threshold': float(request.form.get('success_threshold', 0.95)),
                'batch_size': int(request.form.get('batch_size', 100)),
                'min_delay_between_actions': float(request.form.get('min_delay_between_actions', 2.0)),
                'max_delay_between_actions': float(request.form.get('max_delay_between_actions', 8.0)),
            }
            
            # Save configuration
            config = IndexingConfig(**config_data)
            config.save_to_file('backlink_config.json')
            
            flash('Configuration saved successfully!', 'success')
            return redirect(url_for('backlink.config'))
            
        except Exception as e:
            flash(f'Error saving configuration: {str(e)}', 'error')
    
    # Load current configuration
    try:
        config = IndexingConfig.load_from_file('backlink_config.json')
    except:
        config = IndexingConfig()
    
    return render_template('backlink/config.html', config=config)


@backlink_bp.route('/submit', methods=['GET', 'POST'])
def submit_urls():
    """Submit URLs for backlink indexing"""
    
    if request.method == 'POST':
        try:
            urls_text = request.form.get('urls', '').strip()
            urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
            
            if not urls:
                flash('Please provide at least one URL', 'error')
                return redirect(url_for('backlink.submit_urls'))
            
            # Get metadata
            metadata = {
                'title': request.form.get('title', ''),
                'topic': request.form.get('topic', ''),
                'description': request.form.get('description', '')
            }
            
            # Start processing in background
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store task for background processing
            task_data = {
                'id': task_id,
                'urls': urls,
                'metadata': metadata,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            # Save task (in production, use Redis or database)
            with open(f'tasks/{task_id}.json', 'w') as f:
                json.dump(task_data, f)
            
            flash(f'Submitted {len(urls)} URLs for processing. Task ID: {task_id}', 'success')
            return redirect(url_for('backlink.status', task_id=task_id))
            
        except Exception as e:
            flash(f'Error submitting URLs: {str(e)}', 'error')
    
    return render_template('backlink/submit.html')


@backlink_bp.route('/status/<task_id>')
def status(task_id):
    """Check status of a backlink indexing task"""
    
    try:
        # Load task data
        with open(f'tasks/{task_id}.json', 'r') as f:
            task_data = json.load(f)
        
        return render_template('backlink/status.html', task=task_data)
        
    except FileNotFoundError:
        flash('Task not found', 'error')
        return redirect(url_for('backlink.dashboard'))
    except Exception as e:
        flash(f'Error loading task: {str(e)}', 'error')
        return redirect(url_for('backlink.dashboard'))


@backlink_bp.route('/api/process', methods=['POST'])
def api_process_urls():
    """API endpoint to process URLs"""
    
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        metadata = data.get('metadata', {})
        
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400
        
        # Load configuration
        try:
            config = IndexingConfig.load_from_file('backlink_config.json')
        except:
            config = IndexingConfig()
        
        # Process URLs synchronously (for API response)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        coordinator = None
        try:
            coordinator = BacklinkIndexingCoordinator(config)
            results = loop.run_until_complete(
                coordinator.process_url_collection(urls, metadata)
            )
            
            return jsonify({
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
            
        finally:
            if coordinator:
                loop.run_until_complete(coordinator.shutdown())
            loop.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@backlink_bp.route('/api/stats')
def api_stats():
    """Get system statistics"""
    
    try:
        # Load recent task results for statistics
        stats = {
            'total_processed': 0,
            'success_rate': 0.0,
            'recent_tasks': [],
            'method_performance': {}
        }
        
        # Calculate from recent task files
        import os
        task_dir = 'tasks'
        if os.path.exists(task_dir):
            for filename in os.listdir(task_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(task_dir, filename), 'r') as f:
                            task_data = json.load(f)
                            stats['recent_tasks'].append({
                                'id': task_data.get('id'),
                                'status': task_data.get('status'),
                                'created_at': task_data.get('created_at'),
                                'url_count': len(task_data.get('urls', []))
                            })
                    except:
                        continue
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backlink_bp.route('/test')
def test_system():
    """Test the backlink indexing system"""
    
    try:
        # Load configuration
        try:
            config = IndexingConfig.load_from_file('backlink_config.json')
        except:
            config = IndexingConfig()
        
        # Test URLs
        test_urls = [
            "https://example.com/test1",
            "https://example.com/test2"
        ]
        
        # Process URLs
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        coordinator = None
        try:
            coordinator = BacklinkIndexingCoordinator(config)
            results = loop.run_until_complete(
                coordinator.process_url_collection(
                    test_urls, 
                    metadata={'title': 'Test Article', 'topic': 'testing'}
                )
            )
            
            flash(f'Test completed! Success rate: {results["overall_success_rate"]:.1%}', 'success')
            return render_template('backlink/test_results.html', results=results)
            
        finally:
            if coordinator:
                loop.run_until_complete(coordinator.shutdown())
            loop.close()
            
    except Exception as e:
        flash(f'Test failed: {str(e)}', 'error')
        return redirect(url_for('backlink.dashboard'))


# Initialize tasks directory
import os
if not os.path.exists('tasks'):
    os.makedirs('tasks')