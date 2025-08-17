/**
 * Settings Page JavaScript
 * Enhanced configuration management for Google Indexing Pipeline
 */

class SettingsManager {
    constructor() {
        this.init();
    }

    init() {
        console.log('Initializing Settings Manager...');
        this.setupFormValidation();
        this.setupRealTimeValidation();
        this.loadSettingsStatus();
        this.setupEventListeners();
    }

    setupFormValidation() {
        const form = document.querySelector('form');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                return false;
            }
            
            this.showSubmitIndicator();
        });
    }

    setupRealTimeValidation() {
        // Site URL validation
        const siteUrlInput = document.getElementById('site_url');
        if (siteUrlInput) {
            siteUrlInput.addEventListener('blur', () => {
                this.validateUrl(siteUrlInput, 'Site URL');
            });
        }

        // GSC URL validation
        const gscUrlInput = document.getElementById('gsc_property_url');
        if (gscUrlInput) {
            gscUrlInput.addEventListener('blur', () => {
                this.validateUrl(gscUrlInput, 'GSC Property URL');
            });
        }

        // Numeric inputs validation
        const numericInputs = ['max_crawl_rate', 'crawl_delay', 'sitemap_max_urls'];
        numericInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('blur', () => {
                    this.validateNumericInput(input);
                });
            }
        });
    }

    validateUrl(input, fieldName) {
        const url = input.value.trim();
        if (!url) return true;

        try {
            new URL(url);
            this.setInputValid(input);
            return true;
        } catch (error) {
            this.setInputInvalid(input, `${fieldName} must be a valid URL`);
            return false;
        }
    }

    validateNumericInput(input) {
        const value = parseFloat(input.value);
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);

        if (isNaN(value)) {
            this.setInputInvalid(input, 'Must be a valid number');
            return false;
        }

        if (min !== undefined && value < min) {
            this.setInputInvalid(input, `Must be at least ${min}`);
            return false;
        }

        if (max !== undefined && value > max) {
            this.setInputInvalid(input, `Must be no more than ${max}`);
            return false;
        }

        this.setInputValid(input);
        return true;
    }

    setInputValid(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        this.removeFeedback(input);
    }

    setInputInvalid(input, message) {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        this.showFeedback(input, message, 'invalid');
    }

    showFeedback(input, message, type) {
        this.removeFeedback(input);
        
        const feedback = document.createElement('div');
        feedback.className = `${type}-feedback`;
        feedback.textContent = message;
        
        input.parentNode.appendChild(feedback);
    }

    removeFeedback(input) {
        const existing = input.parentNode.querySelectorAll('.invalid-feedback, .valid-feedback');
        existing.forEach(el => el.remove());
    }

    validateForm() {
        let isValid = true;
        
        // Required fields
        const requiredFields = ['site_url', 'gsc_property_url'];
        requiredFields.forEach(fieldId => {
            const input = document.getElementById(fieldId);
            if (input && !input.value.trim()) {
                this.setInputInvalid(input, 'This field is required');
                isValid = false;
            }
        });

        // URL validation
        const urlFields = ['site_url', 'gsc_property_url'];
        urlFields.forEach(fieldId => {
            const input = document.getElementById(fieldId);
            if (input && input.value.trim()) {
                if (!this.validateUrl(input, input.labels[0]?.textContent || fieldId)) {
                    isValid = false;
                }
            }
        });

        return isValid;
    }

    showSubmitIndicator() {
        const submitBtn = document.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
            submitBtn.disabled = true;
            
            // Re-enable after a reasonable time
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 3000);
        }
    }

    async loadSettingsStatus() {
        try {
            await this.checkGSCStatus();
            await this.checkSystemStatus();
        } catch (error) {
            console.warn('Could not load all status information:', error);
        }
    }

    async checkGSCStatus() {
        try {
            const response = await fetch('/api/gsc-status');
            const data = await response.json();
            
            this.updateStatusBadge('gsc-status', data.credentials_available, 
                'Connected', 'Not Connected', 'Unknown');
            this.updateStatusBadge('gsc-env-status', data.credentials_available, 
                'Set', 'Missing', 'Unknown');
                
        } catch (error) {
            console.warn('Could not check GSC status:', error);
            this.updateStatusBadge('gsc-status', null, '', '', 'Unknown');
            this.updateStatusBadge('gsc-env-status', null, '', '', 'Unknown');
        }
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/api/system-status');
            const data = await response.json();
            
            // Update environment variable status
            Object.entries(data.environment).forEach(([key, value]) => {
                const badgeId = key.toLowerCase().replace('_', '-') + '-status';
                this.updateStatusBadge(badgeId, value, 'Set', 'Missing', 'Unknown');
            });
            
        } catch (error) {
            console.warn('Could not check system status:', error);
        }
    }

    updateStatusBadge(elementId, condition, successText, failText, unknownText) {
        const element = document.getElementById(elementId);
        if (!element) return;

        let badgeClass, text;
        
        if (condition === null || condition === undefined) {
            badgeClass = 'bg-secondary';
            text = unknownText;
        } else if (condition) {
            badgeClass = 'bg-success';
            text = successText;
        } else {
            badgeClass = 'bg-danger';
            text = failText;
        }
        
        element.innerHTML = `<span class="badge ${badgeClass}">${text}</span>`;
    }

    async testConfiguration() {
        const testBtn = document.getElementById('testConfigBtn');
        if (!testBtn) return;
        
        const originalText = testBtn.innerHTML;
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        testBtn.disabled = true;
        
        try {
            const response = await fetch('/api/test-config');
            const data = await response.json();
            
            if (data.all_valid) {
                this.showToast('Configuration test passed! All settings are valid.', 'success');
                this.highlightValidConfig();
            } else {
                const issues = [];
                if (!data.results.site_url_valid) issues.push('Invalid site URL');
                if (!data.results.gsc_url_valid) issues.push('Invalid GSC URL');
                if (!data.results.crawl_settings_valid) issues.push('Invalid crawl settings');
                if (!data.results.sitemap_settings_valid) issues.push('Invalid sitemap settings');
                
                this.showToast('Configuration issues: ' + issues.join(', '), 'error');
                this.highlightInvalidConfig(data.results);
            }
        } catch (error) {
            this.showToast('Failed to test configuration: ' + error.message, 'error');
        } finally {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        }
    }

    highlightValidConfig() {
        const inputs = document.querySelectorAll('.form-control, .form-select');
        inputs.forEach(input => {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        });
    }

    highlightInvalidConfig(results) {
        if (!results.site_url_valid) {
            this.setInputInvalid(document.getElementById('site_url'), 'Invalid URL format');
        }
        if (!results.gsc_url_valid) {
            this.setInputInvalid(document.getElementById('gsc_property_url'), 'Invalid URL format');
        }
        if (!results.crawl_settings_valid) {
            this.setInputInvalid(document.getElementById('max_crawl_rate'), 'Invalid crawl settings');
        }
        if (!results.sitemap_settings_valid) {
            this.setInputInvalid(document.getElementById('sitemap_max_urls'), 'Invalid sitemap settings');
        }
    }

    showToast(message, type) {
        // Create toast if it doesn't exist
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }

        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert">
                <div class="toast-header">
                    <strong class="me-auto text-${type === 'success' ? 'success' : 'danger'}">
                        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-1"></i>
                        ${type === 'success' ? 'Success' : 'Error'}
                    </strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">${message}</div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toast = new bootstrap.Toast(document.getElementById(toastId));
        toast.show();

        // Auto-remove after shown
        document.getElementById(toastId).addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    }

    setupEventListeners() {
        // Test configuration button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'testConfigBtn' || e.target.closest('#testConfigBtn')) {
                this.testConfiguration();
            }
        });

        // Auto-save draft functionality
        const inputs = document.querySelectorAll('.form-control, .form-select, .form-check-input');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.saveDraft();
            });
        });
    }

    saveDraft() {
        const formData = new FormData(document.querySelector('form'));
        const draftData = {};
        
        for (let [key, value] of formData.entries()) {
            draftData[key] = value;
        }
        
        localStorage.setItem('settingsDraft', JSON.stringify(draftData));
    }

    loadDraft() {
        const draftData = localStorage.getItem('settingsDraft');
        if (!draftData) return;

        try {
            const data = JSON.parse(draftData);
            Object.entries(data).forEach(([key, value]) => {
                const input = document.querySelector(`[name="${key}"]`);
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = value === 'on';
                    } else {
                        input.value = value;
                    }
                }
            });
        } catch (error) {
            console.warn('Could not load draft:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.settingsManager = new SettingsManager();
        console.log('Settings Manager initialized successfully');
    } catch (error) {
        console.error('Failed to initialize Settings Manager:', error);
    }
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsManager;
}