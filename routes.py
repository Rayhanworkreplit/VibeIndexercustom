import json
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, desc
from urllib.parse import urlparse

from app import app, db
from models import URL, CrawlResult, Sitemap, GSCFeedback, TaskQueue, Settings, IndexingStats
from services.url_discovery import discover_urls
from services.background_tasks import queue_validation_task, queue_sitemap_task, process_pending_tasks, queue_advanced_indexing_task
from utils.helpers import is_valid_url, get_domain_from_url

@app.route('/')
def dashboard():
    """Main dashboard showing indexing overview"""
    # Get current stats
    total_urls = URL.query.count()
    ready_urls = URL.query.filter_by(status='ready').count()
    indexed_urls = URL.query.filter_by(status='indexed').count()
    error_urls = URL.query.filter_by(status='error').count()
    pending_urls = URL.query.filter_by(status='pending').count()
    
    # Get recent activity
    recent_crawls = CrawlResult.query.order_by(desc(CrawlResult.created_at)).limit(10).all()
    recent_sitemaps = Sitemap.query.order_by(desc(Sitemap.created_at)).limit(5).all()
    
    # Get error summary
    error_summary = db.session.query(
        CrawlResult.validation_errors,
        func.count(CrawlResult.id).label('count')
    ).filter(
        CrawlResult.validation_errors.isnot(None)
    ).group_by(
        CrawlResult.validation_errors
    ).order_by(desc('count')).limit(10).all()
    
    # Get daily stats for chart (last 30 days)
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    daily_stats = IndexingStats.query.filter(
        IndexingStats.date >= thirty_days_ago
    ).order_by(IndexingStats.date).all()
    
    stats = {
        'total_urls': total_urls,
        'ready_urls': ready_urls,
        'indexed_urls': indexed_urls,
        'error_urls': error_urls,
        'pending_urls': pending_urls,
        'indexing_rate': round((indexed_urls / total_urls * 100) if total_urls > 0 else 0, 1)
    }
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_crawls=recent_crawls,
                         recent_sitemaps=recent_sitemaps,
                         error_summary=error_summary,
                         daily_stats=daily_stats)

@app.route('/urls')
def urls():
    """URL management page"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '')
    
    query = URL.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if search_query:
        query = query.filter(URL.url.contains(search_query))
    
    # Paginate results
    per_page = 50
    urls_page = query.order_by(desc(URL.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get status counts for filter tabs
    status_counts = {
        'all': URL.query.count(),
        'pending': URL.query.filter_by(status='pending').count(),
        'ready': URL.query.filter_by(status='ready').count(),
        'indexed': URL.query.filter_by(status='indexed').count(),
        'error': URL.query.filter_by(status='error').count(),
    }
    
    return render_template('urls.html',
                         urls=urls_page,
                         status_counts=status_counts,
                         current_status=status_filter,
                         search_query=search_query)

@app.route('/add-url', methods=['POST'])
def add_url():
    """Add a single URL for indexing"""
    url = request.form.get('url', '').strip()
    
    if not url:
        flash('URL is required', 'error')
        return redirect(url_for('urls'))
    
    if not is_valid_url(url):
        flash('Invalid URL format', 'error')
        return redirect(url_for('urls'))
    
    # Check if URL already exists
    existing_url = URL.query.filter_by(url=url).first()
    if existing_url:
        flash('URL already exists in the system', 'warning')
        return redirect(url_for('urls'))
    
    # Add new URL
    new_url = URL()
    new_url.url = url
    new_url.status = 'pending'
    db.session.add(new_url)
    db.session.commit()
    
    # Queue validation task
    queue_validation_task(new_url.id)
    
    flash(f'URL added successfully: {url}', 'success')
    return redirect(url_for('urls'))

@app.route('/bulk-add-urls', methods=['POST'])
def bulk_add_urls():
    """Add multiple URLs at once"""
    urls_text = request.form.get('urls', '').strip()
    
    if not urls_text:
        flash('No URLs provided', 'error')
        return redirect(url_for('urls'))
    
    # Parse URLs (one per line)
    urls = [line.strip() for line in urls_text.split('\n') if line.strip()]
    
    added_count = 0
    skipped_count = 0
    
    for url in urls:
        if not is_valid_url(url):
            skipped_count += 1
            continue
            
        # Check if URL already exists
        existing_url = URL.query.filter_by(url=url).first()
        if existing_url:
            skipped_count += 1
            continue
        
        # Add new URL
        new_url = URL()
        new_url.url = url
        new_url.status = 'pending'
        db.session.add(new_url)
        added_count += 1
    
    db.session.commit()
    
    # Queue validation tasks for all new URLs
    for url in URL.query.filter_by(status='pending').all():
        queue_validation_task(url.id)
    
    flash(f'Added {added_count} URLs, skipped {skipped_count} (duplicates/invalid)', 'success')
    return redirect(url_for('urls'))

@app.route('/discover-urls', methods=['POST'])
def discover_urls_route():
    """Discover URLs from various sources"""
    source = request.form.get('source', 'sitemap')
    source_url = request.form.get('source_url', '').strip()
    
    if not source_url and source != 'internal':
        flash('Source URL is required', 'error')
        return redirect(url_for('urls'))
    
    try:
        discovered_urls = discover_urls(source, source_url)
        added_count = 0
        
        for url in discovered_urls:
            if is_valid_url(url):
                existing_url = URL.query.filter_by(url=url).first()
                if not existing_url:
                    new_url = URL()
                    new_url.url = url
                    new_url.status = 'pending'
                    db.session.add(new_url)
                    added_count += 1
        
        db.session.commit()
        
        # Queue validation tasks
        for url in URL.query.filter_by(status='pending').all():
            queue_validation_task(url.id)
        
        flash(f'Discovered and added {added_count} new URLs from {source}', 'success')
    except Exception as e:
        flash(f'Error discovering URLs: {str(e)}', 'error')
    
    return redirect(url_for('urls'))

@app.route('/validate-urls', methods=['POST'])
def validate_urls():
    """Trigger validation for pending URLs"""
    pending_urls = URL.query.filter_by(status='pending').limit(100).all()
    
    for url in pending_urls:
        queue_validation_task(url.id)
    
    flash(f'Queued validation for {len(pending_urls)} URLs', 'success')
    return redirect(url_for('urls'))

@app.route('/generate-sitemap', methods=['POST'])
def generate_sitemap():
    """Generate and submit new sitemap"""
    ready_urls = URL.query.filter_by(status='ready').all()
    
    if not ready_urls:
        flash('No ready URLs to include in sitemap', 'warning')
        return redirect(url_for('dashboard'))
    
    # Queue sitemap generation task
    queue_sitemap_task([url.id for url in ready_urls])
    
    flash(f'Queued sitemap generation for {len(ready_urls)} URLs', 'success')
    return redirect(url_for('dashboard'))

@app.route('/url/<int:url_id>')
def url_detail(url_id):
    """Detailed view of a specific URL"""
    url = URL.query.get_or_404(url_id)
    crawl_history = url.crawls.order_by(desc(CrawlResult.created_at)).all()
    gsc_feedback = GSCFeedback.query.filter_by(url_id=url_id).order_by(desc(GSCFeedback.updated_at)).first()
    
    return render_template('url_detail.html',
                         url=url,
                         crawl_history=crawl_history,
                         gsc_feedback=gsc_feedback)

@app.route('/settings')
def settings():
    """Settings page"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        settings.site_url = "https://example.com"
        settings.gsc_property_url = "https://example.com"
        db.session.add(settings)
        db.session.commit()
    
    return render_template('settings.html', settings=settings)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    """Update application settings"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
    
    # Update settings from form
    settings.site_url = request.form.get('site_url', '').strip()
    settings.gsc_property_url = request.form.get('gsc_property_url', '').strip()
    settings.max_crawl_rate = int(request.form.get('max_crawl_rate', 50))
    settings.crawl_delay = float(request.form.get('crawl_delay', 1.0))
    settings.sitemap_max_urls = int(request.form.get('sitemap_max_urls', 50000))
    settings.auto_submit_sitemaps = request.form.get('auto_submit_sitemaps') == 'on'
    settings.slack_webhook_url = request.form.get('slack_webhook_url', '').strip()
    settings.email_alerts = request.form.get('email_alerts', '').strip()
    settings.alert_on_deindex = request.form.get('alert_on_deindex') == 'on'
    
    db.session.commit()
    flash('Settings updated successfully', 'success')
    return redirect(url_for('settings'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    stats = {
        'total_urls': URL.query.count(),
        'ready_urls': URL.query.filter_by(status='ready').count(),
        'indexed_urls': URL.query.filter_by(status='indexed').count(),
        'error_urls': URL.query.filter_by(status='error').count(),
        'pending_urls': URL.query.filter_by(status='pending').count(),
    }
    
    # Calculate indexing rate
    if stats['total_urls'] > 0:
        rate = (stats['indexed_urls'] / stats['total_urls'] * 100)
        stats['indexing_rate'] = round(rate, 1)
    else:
        stats['indexing_rate'] = 0.0
    
    return jsonify(stats)

@app.route('/api/process-tasks', methods=['POST'])
def api_process_tasks():
    """API endpoint to process background tasks"""
    try:
        processed_count = process_pending_tasks(limit=10)
        return jsonify({
            'success': True,
            'processed_count': processed_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/delete-url/<int:url_id>', methods=['POST'])
def delete_url(url_id):
    """Delete a URL from the system"""
    url = URL.query.get_or_404(url_id)
    db.session.delete(url)
    db.session.commit()
    
    flash(f'URL deleted: {url.url}', 'success')
    return redirect(url_for('urls'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


@app.route('/api/advanced-indexing', methods=['POST'])
def start_advanced_indexing():
    """Start advanced 6-layer indexing campaign"""
    try:
        data = request.get_json()
        url_ids = data.get('url_ids', [])
        
        if not url_ids:
            # Use all ready URLs if none specified
            urls = URL.query.filter_by(status='ready').all()
            url_ids = [url.id for url in urls]
        
        if not url_ids:
            return jsonify({
                'success': False, 
                'error': 'No URLs available for indexing'
            }), 400
        
        # Queue advanced indexing campaign
        task = queue_advanced_indexing_task(url_ids, priority=1)
        
        return jsonify({
            'success': True,
            'message': f'Advanced indexing campaign queued for {len(url_ids)} URLs',
            'task_id': task.id,
            'url_count': len(url_ids)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-content', methods=['POST'])
def analyze_content():
    """Analyze URL content for AI agent"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Use the web scraper to get content
        from services.url_discovery import get_website_text_content
        content = get_website_text_content(url)
        
        if not content:
            return jsonify({'error': 'Could not extract content from URL'}), 400
        
        # Basic content analysis
        word_count = len(content.split())
        content_length = len(content)
        content_preview = content[:500] + "..." if len(content) > 500 else content
        
        return jsonify({
            'url': url,
            'title': '',  # Could extract title if needed
            'content_length': content_length,
            'word_count': word_count,
            'content_preview': content_preview,
            'content_type': 'text/html',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
