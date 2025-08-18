/**
 * Google Indexing Pipeline - Dashboard JavaScript
 * Handles real-time updates, charts, and interactive features
 */

// Global variables
let refreshInterval;
let statsChart;
let statusChart;

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startAutoRefresh();
});

/**
 * Initialize dashboard components
 */
function initializeDashboard() {
    console.log('Initializing Google Indexing Pipeline Dashboard');
    
    // Initialize tooltips
    initializeTooltips();
    
    // Load initial data
    loadDashboardStats();
    
    // Initialize charts if canvas elements exist
    if (document.getElementById('statusChart')) {
        initializeStatusChart();
    }
    
    if (document.getElementById('indexingChart')) {
        initializeIndexingChart();
    }
    
    // Initialize search functionality
    setupSearchFilters();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Process tasks button (check if exists first)
    const processTasksBtn = document.querySelector('[onclick="processBackgroundTasks()"]');
    if (processTasksBtn) {
        processTasksBtn.removeAttribute('onclick');
        processTasksBtn.addEventListener('click', processBackgroundTasks);
    }
    
    // Harvest GSC button (check if exists first)
    const harvestBtn = document.querySelector('[onclick="harvestGSCFeedback()"]') || document.getElementById('harvestGSCBtn');
    if (harvestBtn) {
        harvestBtn.removeAttribute('onclick');
        harvestBtn.addEventListener('click', harvestGSCFeedback);
    }
    
    // Advanced indexing button
    const advancedIndexingBtn = document.getElementById('startAdvancedIndexingBtn');
    if (advancedIndexingBtn) {
        advancedIndexingBtn.addEventListener('click', startAdvancedIndexing);
    }
    
    // Process tasks button
    const processTasksBtnNew = document.getElementById('processTasksBtn');
    if (processTasksBtnNew) {
        processTasksBtnNew.addEventListener('click', processBackgroundTasks);
    }
    
    // AI Agent button
    const aiAgentBtn = document.getElementById('openAIAgentBtn');
    if (aiAgentBtn) {
        aiAgentBtn.addEventListener('click', openAIAgent);
    }
    
    // Backlink dashboard button
    const backlinkBtn = document.getElementById('openBacklinkDashboardBtn');
    if (backlinkBtn) {
        backlinkBtn.addEventListener('click', openBacklinkDashboard);
    }
    
    // ML prediction test button
    const mlPredictionBtn = document.getElementById('testMLPredictionBtn');
    if (mlPredictionBtn) {
        mlPredictionBtn.addEventListener('click', testMLPrediction);
    }
    
    // Form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmission);
    });
    
    // URL checkboxes
    setupUrlCheckboxes();
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Setup URL checkbox functionality
 */
function setupUrlCheckboxes() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const urlCheckboxes = document.querySelectorAll('.url-checkbox');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            urlCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActions();
        });
    }
    
    urlCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectAllState();
            updateBulkActions();
        });
    });
}

/**
 * Update select all checkbox state based on individual checkbox states
 */
function updateSelectAllState() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const urlCheckboxes = document.querySelectorAll('.url-checkbox');
    
    if (!selectAllCheckbox || urlCheckboxes.length === 0) return;
    
    const checkedCount = document.querySelectorAll('.url-checkbox:checked').length;
    
    if (checkedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === urlCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

/**
 * Update bulk actions visibility and functionality
 */
function updateBulkActions() {
    const checkedBoxes = document.querySelectorAll('.url-checkbox:checked');
    const bulkActionsContainer = document.getElementById('bulkActions');
    const selectedCountElement = document.getElementById('selectedCount');
    
    if (bulkActionsContainer) {
        if (checkedBoxes.length > 0) {
            bulkActionsContainer.classList.remove('d-none');
            if (selectedCountElement) {
                selectedCountElement.textContent = checkedBoxes.length;
            }
        } else {
            bulkActionsContainer.classList.add('d-none');
        }
    }
}

/**
 * Update select all checkbox state
 */
function updateSelectAllState() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const urlCheckboxes = document.querySelectorAll('.url-checkbox');
    
    if (!selectAllCheckbox || urlCheckboxes.length === 0) return;
    
    const checkedCount = Array.from(urlCheckboxes).filter(cb => cb.checked).length;
    
    if (checkedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === urlCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

/**
 * Update bulk action buttons
 */
function updateBulkActions() {
    const checkedBoxes = document.querySelectorAll('.url-checkbox:checked');
    const bulkActions = document.querySelectorAll('.bulk-action');
    
    bulkActions.forEach(action => {
        action.disabled = checkedBoxes.length === 0;
    });
}

/**
 * Load dashboard statistics
 */
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to fetch stats');
        
        const stats = await response.json();
        updateStatsDisplay(stats);
        
    } catch (error) {
        console.warn('Failed to load dashboard stats:', error);
        showToast('Failed to load statistics', 'warning');
    }
}

/**
 * Update statistics display
 */
function updateStatsDisplay(stats) {
    const statElements = {
        'total_urls': stats.total_urls,
        'indexed_urls': stats.indexed_urls,
        'ready_urls': stats.ready_urls,
        'pending_urls': stats.pending_urls,
        'error_urls': stats.error_urls,
        'indexing_rate': stats.indexing_rate + '%'
    };
    
    Object.entries(statElements).forEach(([key, value]) => {
        const element = document.querySelector(`[data-stat="${key}"]`) || 
                       document.querySelector(`.stat-${key.replace('_', '-')}`);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Update chart data if charts exist
    if (statusChart) {
        updateStatusChart(stats);
    }
}

/**
 * Initialize status distribution chart
 */
function initializeStatusChart() {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;
    
    statusChart = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Indexed', 'Ready', 'Pending', 'Error'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'var(--bs-success)',
                    'var(--bs-info)',
                    'var(--bs-warning)',
                    'var(--bs-danger)'
                ],
                borderWidth: 2,
                borderColor: 'var(--bs-dark)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Update status chart data
 */
function updateStatusChart(stats) {
    if (!statusChart) return;
    
    statusChart.data.datasets[0].data = [
        stats.indexed_urls,
        stats.ready_urls,
        stats.pending_urls,
        stats.error_urls
    ];
    
    statusChart.update('none');
}

/**
 * Initialize indexing trends chart
 */
function initializeIndexingChart() {
    const ctx = document.getElementById('indexingChart');
    if (!ctx) return;
    
    statsChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total URLs',
                data: [],
                borderColor: 'var(--bs-primary)',
                backgroundColor: 'transparent',
                tension: 0.4,
                fill: false
            }, {
                label: 'Indexed URLs',
                data: [],
                borderColor: 'var(--bs-success)',
                backgroundColor: 'transparent',
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

/**
 * Process background tasks
 */
async function processBackgroundTasks() {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/process-tasks', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to process tasks');
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`Processed ${data.processed_count} tasks`, 'success');
            
            // Refresh stats after processing
            setTimeout(loadDashboardStats, 1000);
        } else {
            showToast(data.error || 'Error processing tasks', 'error');
        }
        
    } catch (error) {
        console.error('Error processing tasks:', error);
        showToast('Error processing tasks', 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

/**
 * Harvest GSC feedback
 */
async function harvestGSCFeedback() {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Harvesting...';
    button.disabled = true;
    
    try {
        // Queue GSC harvest task
        const response = await fetch('/api/process-tasks', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                task_type: 'harvest_gsc',
                limit: 100 
            })
        });
        
        if (response.ok) {
            showToast('GSC feedback harvest queued', 'success');
        } else {
            showToast('Error queuing GSC harvest', 'error');
        }
        
    } catch (error) {
        console.error('Error queuing GSC harvest:', error);
        showToast('Error queuing GSC harvest', 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

/**
 * Handle form submissions with loading states
 */
function handleFormSubmission(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
        submitButton.disabled = true;
        
        // Re-enable button after a delay (form will likely redirect)
        setTimeout(() => {
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        }, 5000);
    }
}

/**
 * Start automatic refresh of dashboard data
 */
function startAutoRefresh() {
    // Refresh every 30 seconds
    refreshInterval = setInterval(loadDashboardStats, 30000);
}

/**
 * Stop automatic refresh
 */
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 5000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1060';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastElement = document.createElement('div');
    toastElement.id = toastId;
    toastElement.className = `toast align-items-center text-white bg-${getBootstrapClass(type)} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas ${getToastIcon(type)} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                    data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Remove element after hiding
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Get Bootstrap class for toast type
 */
function getBootstrapClass(type) {
    const classMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'primary'
    };
    return classMap[type] || 'primary';
}

/**
 * Get icon for toast type
 */
function getToastIcon(type) {
    const iconMap = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return iconMap[type] || 'fa-info-circle';
}

/**
 * Format numbers for display
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Format duration for display
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return Math.round(seconds) + 's';
    } else if (seconds < 3600) {
        return Math.round(seconds / 60) + 'm';
    } else {
        return Math.round(seconds / 3600) + 'h';
    }
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

/**
 * Cleanup when page unloads
 */
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

/**
 * Start Advanced 6-Layer Indexing Campaign
 */
async function startAdvancedIndexing() {
    // Show configuration modal first
    showAdvancedIndexingModal();
}

/**
 * Show Advanced Indexing Configuration Modal
 */
function showAdvancedIndexingModal() {
    // Create modal if it doesn't exist
    let modal = document.getElementById('advancedIndexingModal');
    if (!modal) {
        modal = createAdvancedIndexingModal();
        document.body.appendChild(modal);
    }
    
    // Show the modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Make this function globally available
window.showAdvancedIndexingModal = showAdvancedIndexingModal;

/**
 * Create Advanced Indexing Configuration Modal
 */
function createAdvancedIndexingModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'advancedIndexingModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-rocket me-2"></i>
                        Configure 6-Layer Indexing Campaign
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="advancedIndexingForm">
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="fas fa-layer-group me-2"></i>Indexing Layers</h6>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer1" checked>
                                    <label class="form-check-label" for="layer1">
                                        <strong>Layer 1:</strong> Direct Sitemap Pinging
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer2" checked>
                                    <label class="form-check-label" for="layer2">
                                        <strong>Layer 2:</strong> RSS + PubSubHubbub
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer3" checked>
                                    <label class="form-check-label" for="layer3">
                                        <strong>Layer 3:</strong> Internal Linking Web
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer4" checked>
                                    <label class="form-check-label" for="layer4">
                                        <strong>Layer 4:</strong> Social Signal Injection
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer5" checked>
                                    <label class="form-check-label" for="layer5">
                                        <strong>Layer 5:</strong> Third-party Discovery
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="layer6" checked>
                                    <label class="form-check-label" for="layer6">
                                        <strong>Layer 6:</strong> Advanced Crawl Triggers
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="fas fa-cogs me-2"></i>Campaign Settings</h6>
                                <div class="mb-3">
                                    <label class="form-label">URLs to Process</label>
                                    <select class="form-select" id="urlSelection">
                                        <option value="ready">All Ready URLs</option>
                                        <option value="pending">All Pending URLs</option>
                                        <option value="all">All URLs</option>
                                        <option value="selected">Selected URLs Only</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Priority Level</label>
                                    <select class="form-select" id="priorityLevel">
                                        <option value="1">High Priority</option>
                                        <option value="2" selected>Normal Priority</option>
                                        <option value="3">Low Priority</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Delay Between Layers (minutes)</label>
                                    <input type="number" class="form-control" id="layerDelay" value="30" min="5" max="1440">
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="enableRetries" checked>
                                    <label class="form-check-label" for="enableRetries">
                                        Enable automatic retries for failed URLs
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Campaign Overview:</strong> This will execute a comprehensive 6-layer indexing strategy 
                                designed to achieve 95%+ Google indexing success rates through multiple proven methods.
                            </div>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-warning" onclick="startAdvancedIndexingCampaign()">
                        <i class="fas fa-rocket me-1"></i>
                        Launch Campaign
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return modal;
}

/**
 * Start the actual advanced indexing campaign
 */
async function startAdvancedIndexingCampaign() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('advancedIndexingModal'));
    const button = event.target;
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Starting...';
    button.disabled = true;
    
    try {
        // Collect form data
        const form = document.getElementById('advancedIndexingForm');
        const formData = new FormData(form);
        
        const config = {
            layers: {
                layer1: document.getElementById('layer1').checked,
                layer2: document.getElementById('layer2').checked,
                layer3: document.getElementById('layer3').checked,
                layer4: document.getElementById('layer4').checked,
                layer5: document.getElementById('layer5').checked,
                layer6: document.getElementById('layer6').checked
            },
            url_selection: document.getElementById('urlSelection').value,
            priority: parseInt(document.getElementById('priorityLevel').value),
            layer_delay: parseInt(document.getElementById('layerDelay').value),
            enable_retries: document.getElementById('enableRetries').checked
        };
        
        const response = await fetch('/api/advanced-indexing', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Failed to start advanced indexing');
        
        const data = await response.json();
        
        if (data.success) {
            modal.hide();
            showToast(`Advanced 6-layer indexing campaign started for ${data.url_count} URLs`, 'success');
            
            // Refresh stats after starting campaign
            setTimeout(loadDashboardStats, 2000);
        } else {
            showToast(data.error || 'Error starting campaign', 'error');
        }
        
    } catch (error) {
        console.error('Error starting advanced indexing:', error);
        showToast('Error starting advanced indexing campaign', 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

/**
 * Open AI Agent interface
 */
function openAIAgent() {
    // Navigate to AI agent page or open in modal
    window.location.href = '/ai-agent';
}

/**
 * Open Backlink Dashboard
 */
function openBacklinkDashboard() {
    // Navigate to backlink dashboard
    window.location.href = '/backlink';
}

/**
 * Test ML Prediction functionality
 */
async function testMLPrediction() {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Testing ML...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/ml-prediction-test', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to test ML prediction');
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`ML Prediction Test: ${data.prediction}% success rate predicted`, 'success');
        } else {
            showToast(data.error || 'Error testing ML prediction', 'error');
        }
        
    } catch (error) {
        console.error('Error testing ML prediction:', error);
        showToast('Error testing ML prediction', 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

/**
 * Handle bulk URL operations
 */
async function bulkAction(action) {
    const checkedBoxes = document.querySelectorAll('.url-checkbox:checked');
    if (checkedBoxes.length === 0) {
        showToast('Please select URLs first', 'warning');
        return;
    }
    
    const urlIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    try {
        const response = await fetch('/api/bulk-action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                url_ids: urlIds
            })
        });
        
        if (!response.ok) throw new Error('Failed to perform bulk action');
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${action} applied to ${urlIds.length} URLs`, 'success');
            setTimeout(loadDashboardStats, 1000);
        } else {
            showToast(data.error || 'Error performing bulk action', 'error');
        }
        
    } catch (error) {
        console.error('Error performing bulk action:', error);
        showToast('Error performing bulk action', 'error');
    }
}

/**
 * Real-time search functionality
 */
function setupSearchFilters() {
    const searchInput = document.getElementById('searchUrls');
    const statusFilter = document.getElementById('statusFilter');
    
    if (searchInput) {
        const debouncedSearch = debounce(performSearch, 300);
        searchInput.addEventListener('input', debouncedSearch);
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', performSearch);
    }
}

/**
 * Perform search with current filters
 */
async function performSearch() {
    const searchInput = document.getElementById('searchUrls');
    const statusFilter = document.getElementById('statusFilter');
    const resultsContainer = document.getElementById('searchResults');
    
    if (!searchInput || !resultsContainer) return;
    
    const query = searchInput.value.trim();
    const status = statusFilter ? statusFilter.value : '';
    
    try {
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (status) params.append('status', status);
        
        const response = await fetch(`/api/search-urls?${params}`);
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        updateSearchResults(data.urls);
        
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed', 'error');
    }
}

/**
 * Update search results display
 */
function updateSearchResults(urls) {
    const resultsContainer = document.getElementById('searchResults');
    if (!resultsContainer) return;
    
    if (urls.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted">No results found</p>';
        return;
    }
    
    const resultsHTML = urls.map(url => `
        <div class="list-group-item">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${url.url}</h6>
                    <small class="text-muted">Status: ${url.status}</small>
                </div>
                <span class="badge bg-${getStatusBadgeClass(url.status)}">${url.status}</span>
            </div>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = resultsHTML;
}

/**
 * Get Bootstrap badge class for status
 */
function getStatusBadgeClass(status) {
    const statusMap = {
        'indexed': 'success',
        'ready': 'info',
        'pending': 'warning',
        'error': 'danger'
    };
    return statusMap[status] || 'secondary';
}

/**
 * Add safer null checks for addEventListener
 */
function safeAddEventListener(selector, event, handler) {
    const element = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (element && typeof element.addEventListener === 'function') {
        element.addEventListener(event, handler);
        return true;
    }
    return false;
}

// Export functions for global access
window.processBackgroundTasks = processBackgroundTasks;
window.harvestGSCFeedback = harvestGSCFeedback;
window.startAdvancedIndexing = startAdvancedIndexing;
window.startAdvancedIndexingCampaign = startAdvancedIndexingCampaign;
window.openAIAgent = openAIAgent;
window.openBacklinkDashboard = openBacklinkDashboard;
window.testMLPrediction = testMLPrediction;
window.bulkAction = bulkAction;
window.showToast = showToast;
