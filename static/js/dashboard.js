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
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Process tasks button
    const processTasksBtn = document.querySelector('[onclick="processBackgroundTasks()"]');
    if (processTasksBtn) {
        processTasksBtn.removeAttribute('onclick');
        processTasksBtn.addEventListener('click', processBackgroundTasks);
    }
    
    // Harvest GSC button
    const harvestBtn = document.querySelector('[onclick="harvestGSCFeedback()"]');
    if (harvestBtn) {
        harvestBtn.removeAttribute('onclick');
        harvestBtn.addEventListener('click', harvestGSCFeedback);
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

// Export functions for global access
window.processBackgroundTasks = processBackgroundTasks;
window.harvestGSCFeedback = harvestGSCFeedback;
window.showToast = showToast;
