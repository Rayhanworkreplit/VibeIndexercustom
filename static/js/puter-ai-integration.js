/**
 * Puter.js AI Integration for Backlink Indexing System
 * Provides AI-powered content analysis and intelligent indexing requests
 */

class PuterAIAgent {
    constructor() {
        this.isInitialized = false;
        this.aiServices = null;
        this.storage = null;
        this.auth = null;
        this.init();
    }

    async init() {
        try {
            console.log('Initializing Puter.js AI Agent...');
            
            // Check if Puter.js is available
            if (typeof puter === 'undefined') {
                console.warn('Puter.js not loaded, using fallback mode');
                this.isInitialized = true;
                this.initializeUI();
                return;
            }
            
            // Initialize Puter.js
            await puter.init();
            
            // Get AI services
            this.aiServices = puter.ai;
            this.storage = puter.fs;
            this.auth = puter.auth;
            
            // Check authentication status (optional for basic functionality)
            try {
                const isLoggedIn = await this.auth.isSignedIn();
                if (!isLoggedIn) {
                    console.log('User not authenticated with Puter.js - some features may be limited');
                }
            } catch (error) {
                console.warn('Authentication check failed, continuing without auth:', error);
            }
            
            this.isInitialized = true;
            console.log('Puter.js AI Agent initialized successfully');
            
            // Initialize UI components
            this.initializeUI();
            
        } catch (error) {
            console.error('Failed to initialize Puter.js AI Agent:', error);
            // Continue with fallback mode
            this.isInitialized = true;
            this.initializeUI();
        }
    }

    async promptForAuth() {
        try {
            const authResult = await this.auth.signIn();
            console.log('Authentication successful:', authResult);
        } catch (error) {
            console.warn('Authentication failed or cancelled:', error);
        }
    }

    initializeUI() {
        // Add AI analysis button to existing interface
        const analysisButton = document.createElement('button');
        analysisButton.id = 'ai-analysis-btn';
        analysisButton.className = 'btn btn-info';
        analysisButton.innerHTML = '<i class="fas fa-brain"></i> AI Analysis';
        analysisButton.onclick = () => this.openAIAnalysisModal();

        // Add to dashboard if it exists
        const dashboardActions = document.querySelector('.dashboard-actions');
        if (dashboardActions) {
            dashboardActions.appendChild(analysisButton);
        }

        // Create AI analysis modal
        this.createAIAnalysisModal();
    }

    createAIAnalysisModal() {
        const modalHTML = `
            <div class="modal fade" id="aiAnalysisModal" tabindex="-1" aria-labelledby="aiAnalysisModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="aiAnalysisModalLabel">
                                <i class="fas fa-brain"></i> AI-Powered Content Analysis
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>URL Analysis</h6>
                                    <div class="mb-3">
                                        <label for="urlInput" class="form-label">URL to Analyze</label>
                                        <input type="url" class="form-control" id="urlInput" placeholder="https://example.com/article">
                                    </div>
                                    <button class="btn btn-primary" onclick="puterAI.analyzeURL()">
                                        <i class="fas fa-search"></i> Analyze Content
                                    </button>
                                </div>
                                <div class="col-md-6">
                                    <h6>Bulk Analysis</h6>
                                    <div class="mb-3">
                                        <label for="urlListInput" class="form-label">URLs (one per line)</label>
                                        <textarea class="form-control" id="urlListInput" rows="5" 
                                                  placeholder="https://example.com/page1&#10;https://example.com/page2"></textarea>
                                    </div>
                                    <button class="btn btn-success" onclick="puterAI.analyzeBulkURLs()">
                                        <i class="fas fa-list"></i> Bulk Analyze
                                    </button>
                                </div>
                            </div>
                            
                            <hr>
                            
                            <div id="aiAnalysisResults" class="mt-4" style="display: none;">
                                <h6>Analysis Results</h6>
                                <div id="analysisContent"></div>
                            </div>
                            
                            <div id="aiRecommendations" class="mt-4" style="display: none;">
                                <h6>AI Recommendations</h6>
                                <div id="recommendationsContent"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="puterAI.implementRecommendations()">
                                Implement Recommendations
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    openAIAnalysisModal() {
        const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
        modal.show();
    }

    async analyzeURL() {
        if (!this.isInitialized) {
            this.showError('AI Agent not initialized');
            return;
        }

        const url = document.getElementById('urlInput').value.trim();
        if (!url) {
            this.showError('Please enter a URL to analyze');
            return;
        }

        this.showLoading('Analyzing URL content...');

        try {
            // Fetch URL content
            const contentAnalysis = await this.fetchAndAnalyzeContent(url);
            
            // Use Puter.js AI for content analysis
            const aiAnalysis = await this.performAIAnalysis(contentAnalysis);
            
            // Get indexing recommendations
            const recommendations = await this.generateIndexingRecommendations(url, aiAnalysis);
            
            // Display results
            this.displayAnalysisResults(url, aiAnalysis, recommendations);
            
        } catch (error) {
            console.error('URL analysis failed:', error);
            this.showError('Failed to analyze URL: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async fetchAndAnalyzeContent(url) {
        try {
            // Use the existing web scraping capability
            const response = await fetch('/api/analyze-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            throw new Error('Failed to fetch content: ' + error.message);
        }
    }

    async performAIAnalysis(contentData) {
        try {
            const prompt = `
                Analyze the following web content for SEO and indexing optimization:
                
                URL: ${contentData.url}
                Title: ${contentData.title}
                Content Length: ${contentData.content_length} characters
                Word Count: ${contentData.word_count}
                Content Type: ${contentData.content_type}
                
                Content Preview:
                ${contentData.content_preview}
                
                Please provide:
                1. Content quality assessment (1-10)
                2. SEO optimization level (1-10)
                3. Indexing priority (high/medium/low)
                4. Key topics and themes
                5. Potential indexing challenges
                6. Recommended improvements
            `;

            let aiResponse;
            
            if (this.aiServices && typeof this.aiServices.chat === 'function') {
                // Use Puter.js AI if available
                aiResponse = await this.aiServices.chat([
                    {
                        role: 'system',
                        content: 'You are an expert SEO analyst specializing in content optimization and search engine indexing strategies.'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ]);
            } else {
                // Fallback analysis
                aiResponse = this.generateFallbackAnalysis(contentData);
            }

            return {
                analysis: aiResponse,
                timestamp: new Date().toISOString(),
                url: contentData.url
            };

        } catch (error) {
            // Fallback to basic analysis if AI fails
            return {
                analysis: this.generateFallbackAnalysis(contentData),
                timestamp: new Date().toISOString(),
                url: contentData.url
            };
        }
    }
    
    generateFallbackAnalysis(contentData) {
        const wordCount = contentData.word_count;
        const contentLength = contentData.content_length;
        
        // Basic scoring based on content metrics
        let qualityScore = 5;
        let seoScore = 5;
        let priority = 'medium';
        
        if (wordCount > 1000) {
            qualityScore += 2;
            seoScore += 1;
        }
        if (wordCount > 2000) {
            qualityScore += 1;
            priority = 'high';
        }
        if (wordCount < 300) {
            qualityScore -= 2;
            priority = 'low';
        }
        
        return `Content Analysis Results:
        
1. Content Quality Assessment: ${Math.min(10, qualityScore)}/10
   - Word count: ${wordCount} (${wordCount > 1000 ? 'Excellent' : wordCount > 500 ? 'Good' : 'Needs improvement'})
   - Content length: ${contentLength} characters
   
2. SEO Optimization Level: ${Math.min(10, seoScore)}/10
   - Content depth: ${wordCount > 1000 ? 'Comprehensive' : 'Basic'}
   - Readability: Analysis pending
   
3. Indexing Priority: ${priority.toUpperCase()}
   - Based on content volume and potential value
   
4. Key Topics and Themes:
   - Analysis of main topics from content preview
   - Semantic relevance assessment needed
   
5. Potential Indexing Challenges:
   ${wordCount < 300 ? '- Content may be too short for effective indexing' : ''}
   - Technical SEO factors need review
   - Internal linking structure assessment needed
   
6. Recommended Improvements:
   ${wordCount < 500 ? '- Expand content to at least 500 words' : ''}
   - Optimize meta descriptions and title tags
   - Implement structured data markup
   - Enhance internal linking strategy
   - Use our 6-layer indexing campaign for maximum visibility`;
    }

    async generateIndexingRecommendations(url, aiAnalysis) {
        try {
            const recommendationPrompt = `
                Based on the following AI analysis, provide specific indexing method recommendations:
                
                ${aiAnalysis.analysis}
                
                Available indexing methods:
                1. Social Bookmarking (Reddit, Digg, Mix)
                2. RSS Distribution (feed syndication)
                3. Web 2.0 Posting (Blogger, WordPress)
                4. Forum Commenting (high DA forums)
                5. Directory Submission (web directories)
                6. Social Signals (Twitter, Pinterest, LinkedIn)
                
                Provide:
                1. Recommended method combination
                2. Priority order (1-6)
                3. Expected success rate
                4. Specific implementation notes
                5. Timeline recommendations
            `;

            const recommendationResponse = await this.aiServices.chat([
                {
                    role: 'system',
                    content: 'You are a technical SEO specialist with expertise in backlink indexing strategies and search engine algorithms.'
                },
                {
                    role: 'user',
                    content: recommendationPrompt
                }
            ]);

            return {
                recommendations: recommendationResponse,
                timestamp: new Date().toISOString(),
                url: url
            };

        } catch (error) {
            throw new Error('Failed to generate recommendations: ' + error.message);
        }
    }

    async analyzeBulkURLs() {
        const urlList = document.getElementById('urlListInput').value.trim();
        if (!urlList) {
            this.showError('Please enter URLs to analyze');
            return;
        }

        const urls = urlList.split('\n').filter(url => url.trim());
        if (urls.length === 0) {
            this.showError('No valid URLs found');
            return;
        }

        this.showLoading(`Analyzing ${urls.length} URLs...`);

        try {
            const batchResults = [];
            
            for (let i = 0; i < urls.length; i++) {
                const url = urls[i].trim();
                
                // Update progress
                this.updateLoadingProgress(`Analyzing ${i + 1}/${urls.length}: ${url}`, (i + 1) / urls.length);
                
                try {
                    const contentAnalysis = await this.fetchAndAnalyzeContent(url);
                    const aiAnalysis = await this.performAIAnalysis(contentAnalysis);
                    const recommendations = await this.generateIndexingRecommendations(url, aiAnalysis);
                    
                    batchResults.push({
                        url: url,
                        analysis: aiAnalysis,
                        recommendations: recommendations,
                        status: 'success'
                    });
                    
                } catch (error) {
                    console.error(`Failed to analyze ${url}:`, error);
                    batchResults.push({
                        url: url,
                        error: error.message,
                        status: 'failed'
                    });
                }
                
                // Add delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            this.displayBulkAnalysisResults(batchResults);
            
            // Save results to Puter.js storage
            await this.saveBulkAnalysisResults(batchResults);

        } catch (error) {
            console.error('Bulk analysis failed:', error);
            this.showError('Bulk analysis failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async saveBulkAnalysisResults(results) {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `bulk-analysis-${timestamp}.json`;
            
            await this.storage.write(filename, JSON.stringify(results, null, 2));
            console.log(`Bulk analysis results saved to: ${filename}`);
            
        } catch (error) {
            console.warn('Failed to save bulk analysis results:', error);
        }
    }

    displayAnalysisResults(url, aiAnalysis, recommendations) {
        const resultsDiv = document.getElementById('aiAnalysisResults');
        const analysisContent = document.getElementById('analysisContent');
        const recommendationsDiv = document.getElementById('aiRecommendations');
        const recommendationsContent = document.getElementById('recommendationsContent');

        // Display analysis
        analysisContent.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Content Analysis for: ${url}</h6>
                    <pre class="bg-light p-3 rounded">${aiAnalysis.analysis}</pre>
                    <small class="text-muted">Analysis completed: ${new Date(aiAnalysis.timestamp).toLocaleString()}</small>
                </div>
            </div>
        `;

        // Display recommendations
        recommendationsContent.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Indexing Recommendations</h6>
                    <pre class="bg-info bg-opacity-10 p-3 rounded">${recommendations.recommendations}</pre>
                    <small class="text-muted">Recommendations generated: ${new Date(recommendations.timestamp).toLocaleString()}</small>
                </div>
            </div>
        `;

        resultsDiv.style.display = 'block';
        recommendationsDiv.style.display = 'block';

        // Store for implementation
        this.lastAnalysis = { url, aiAnalysis, recommendations };
    }

    displayBulkAnalysisResults(results) {
        const successCount = results.filter(r => r.status === 'success').length;
        const failedCount = results.filter(r => r.status === 'failed').length;

        const resultsHTML = `
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">Bulk Analysis Complete</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="alert alert-success">
                                <strong>Successful:</strong> ${successCount} URLs
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="alert alert-warning">
                                <strong>Failed:</strong> ${failedCount} URLs
                            </div>
                        </div>
                    </div>
                    
                    <div class="accordion" id="bulkResultsAccordion">
                        ${results.map((result, index) => `
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="heading${index}">
                                    <button class="accordion-button collapsed" type="button" 
                                            data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                                        ${result.url} 
                                        <span class="badge ${result.status === 'success' ? 'bg-success' : 'bg-danger'} ms-2">
                                            ${result.status}
                                        </span>
                                    </button>
                                </h2>
                                <div id="collapse${index}" class="accordion-collapse collapse" 
                                     data-bs-parent="#bulkResultsAccordion">
                                    <div class="accordion-body">
                                        ${result.status === 'success' ? `
                                            <div class="mb-3">
                                                <h6>AI Analysis:</h6>
                                                <pre class="bg-light p-2 rounded small">${result.analysis.analysis}</pre>
                                            </div>
                                            <div class="mb-3">
                                                <h6>Recommendations:</h6>
                                                <pre class="bg-info bg-opacity-10 p-2 rounded small">${result.recommendations.recommendations}</pre>
                                            </div>
                                            <button class="btn btn-sm btn-primary" 
                                                    onclick="puterAI.implementSingleRecommendation('${result.url}', ${index})">
                                                Implement for this URL
                                            </button>
                                        ` : `
                                            <div class="alert alert-danger">
                                                <strong>Error:</strong> ${result.error}
                                            </div>
                                        `}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.getElementById('analysisContent').innerHTML = resultsHTML;
        document.getElementById('aiAnalysisResults').style.display = 'block';

        // Store for implementation
        this.lastBulkAnalysis = results;
    }

    async implementRecommendations() {
        if (!this.lastAnalysis && !this.lastBulkAnalysis) {
            this.showError('No analysis results to implement');
            return;
        }

        try {
            if (this.lastAnalysis) {
                await this.implementSingleRecommendation(this.lastAnalysis.url);
            } else if (this.lastBulkAnalysis) {
                await this.implementBulkRecommendations();
            }
        } catch (error) {
            console.error('Failed to implement recommendations:', error);
            this.showError('Failed to implement recommendations: ' + error.message);
        }
    }

    async implementSingleRecommendation(url, index = null) {
        let analysisData;
        
        if (index !== null && this.lastBulkAnalysis) {
            analysisData = this.lastBulkAnalysis[index];
        } else {
            analysisData = this.lastAnalysis;
        }

        if (!analysisData || analysisData.status === 'failed') {
            this.showError('No valid analysis data for this URL');
            return;
        }

        this.showLoading('Implementing AI recommendations...');

        try {
            // Parse AI recommendations to extract method preferences
            const methodConfig = this.parseRecommendationsToConfig(analysisData.recommendations.recommendations);
            
            // Submit to indexing queue
            const response = await fetch('/api/submit-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    method_config: methodConfig,
                    priority: this.extractPriority(analysisData.recommendations.recommendations),
                    ai_analysis: true,
                    analysis_data: analysisData
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            this.showSuccess(`URL submitted for indexing with AI-optimized configuration. Task ID: ${result.task_id}`);
            
            // Update the dashboard if available
            if (typeof updateDashboard === 'function') {
                updateDashboard();
            }

        } catch (error) {
            throw new Error('Failed to implement recommendation: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async implementBulkRecommendations() {
        const successfulResults = this.lastBulkAnalysis.filter(r => r.status === 'success');
        
        if (successfulResults.length === 0) {
            this.showError('No successful analyses to implement');
            return;
        }

        this.showLoading(`Implementing recommendations for ${successfulResults.length} URLs...`);

        try {
            const submissions = [];
            
            for (let i = 0; i < successfulResults.length; i++) {
                const result = successfulResults[i];
                
                this.updateLoadingProgress(
                    `Submitting ${i + 1}/${successfulResults.length}: ${result.url}`,
                    (i + 1) / successfulResults.length
                );

                const methodConfig = this.parseRecommendationsToConfig(result.recommendations.recommendations);
                
                const response = await fetch('/api/submit-url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: result.url,
                        method_config: methodConfig,
                        priority: this.extractPriority(result.recommendations.recommendations),
                        ai_analysis: true,
                        analysis_data: result
                    })
                });

                if (response.ok) {
                    const submissionResult = await response.json();
                    submissions.push({
                        url: result.url,
                        task_id: submissionResult.task_id,
                        status: 'submitted'
                    });
                } else {
                    submissions.push({
                        url: result.url,
                        error: `HTTP ${response.status}`,
                        status: 'failed'
                    });
                }

                // Add delay between submissions
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            const successfulSubmissions = submissions.filter(s => s.status === 'submitted').length;
            this.showSuccess(`Successfully submitted ${successfulSubmissions}/${successfulResults.length} URLs for AI-optimized indexing`);
            
            // Save submission results
            await this.saveSubmissionResults(submissions);

        } catch (error) {
            throw new Error('Bulk implementation failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    parseRecommendationsToConfig(recommendations) {
        // Parse AI recommendations text to extract method preferences
        const config = {
            social_bookmarking_enabled: false,
            rss_distribution_enabled: false,
            web2_posting_enabled: false,
            forum_commenting_enabled: false,
            directory_submission_enabled: false,
            social_signals_enabled: false
        };

        const lowercaseRec = recommendations.toLowerCase();

        // Look for method mentions and enable accordingly
        if (lowercaseRec.includes('social bookmarking') || lowercaseRec.includes('reddit') || lowercaseRec.includes('digg')) {
            config.social_bookmarking_enabled = true;
        }
        if (lowercaseRec.includes('rss') || lowercaseRec.includes('feed')) {
            config.rss_distribution_enabled = true;
        }
        if (lowercaseRec.includes('web 2.0') || lowercaseRec.includes('blogger') || lowercaseRec.includes('wordpress')) {
            config.web2_posting_enabled = true;
        }
        if (lowercaseRec.includes('forum') || lowercaseRec.includes('comment')) {
            config.forum_commenting_enabled = true;
        }
        if (lowercaseRec.includes('directory') || lowercaseRec.includes('submission')) {
            config.directory_submission_enabled = true;
        }
        if (lowercaseRec.includes('social signal') || lowercaseRec.includes('twitter') || lowercaseRec.includes('pinterest')) {
            config.social_signals_enabled = true;
        }

        // If no specific methods mentioned, enable high-success methods by default
        const enabledMethods = Object.values(config).filter(Boolean).length;
        if (enabledMethods === 0) {
            config.social_bookmarking_enabled = true;
            config.rss_distribution_enabled = true;
            config.web2_posting_enabled = true;
        }

        return config;
    }

    extractPriority(recommendations) {
        const lowercaseRec = recommendations.toLowerCase();
        
        if (lowercaseRec.includes('high priority') || lowercaseRec.includes('urgent')) {
            return 1;
        } else if (lowercaseRec.includes('low priority')) {
            return 3;
        } else {
            return 2; // Medium priority default
        }
    }

    async saveSubmissionResults(submissions) {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `ai-submissions-${timestamp}.json`;
            
            await this.storage.write(filename, JSON.stringify(submissions, null, 2));
            console.log(`AI submission results saved to: ${filename}`);
            
        } catch (error) {
            console.warn('Failed to save submission results:', error);
        }
    }

    showLoading(message) {
        // Remove existing loading if present
        this.hideLoading();
        
        const loadingHTML = `
            <div id="puterLoadingOverlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div class="card">
                    <div class="card-body text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div id="loadingMessage">${message}</div>
                        <div id="loadingProgress" class="progress mt-3" style="display: none;">
                            <div id="loadingProgressBar" class="progress-bar" style="width: 0%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
    }

    updateLoadingProgress(message, progress) {
        const messageEl = document.getElementById('loadingMessage');
        const progressEl = document.getElementById('loadingProgress');
        const progressBar = document.getElementById('loadingProgressBar');
        
        if (messageEl) messageEl.textContent = message;
        if (progressEl) progressEl.style.display = 'block';
        if (progressBar) {
            progressBar.style.width = `${Math.round(progress * 100)}%`;
            progressBar.setAttribute('aria-valuenow', Math.round(progress * 100));
        }
    }

    hideLoading() {
        const overlay = document.getElementById('puterLoadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    showError(message) {
        this.showToast(message, 'danger');
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showToast(message, type = 'info') {
        const toastHTML = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" 
                 style="position: fixed; top: 20px; right: 20px; z-index: 10000;">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.body.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Auto-remove after shown
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    handleInitError(error) {
        console.error('Puter.js initialization failed:', error);
        
        // Show fallback UI
        const fallbackHTML = `
            <div class="alert alert-warning" id="puterFallback">
                <h6><i class="fas fa-exclamation-triangle"></i> AI Agent Unavailable</h6>
                <p>The AI analysis features require Puter.js integration. Please check:</p>
                <ul>
                    <li>Internet connectivity</li>
                    <li>Puter.js service availability</li>
                    <li>Authentication status</li>
                </ul>
                <button class="btn btn-sm btn-primary" onclick="puterAI.init()">
                    <i class="fas fa-redo"></i> Retry Initialization
                </button>
            </div>
        `;
        
        // Add to dashboard if available
        const dashboard = document.querySelector('.dashboard-container');
        if (dashboard) {
            dashboard.insertAdjacentHTML('afterbegin', fallbackHTML);
        }
    }
}

// Initialize the Puter AI Agent when DOM is loaded
// Initialize AI agent immediately when script loads
try {
    console.log('Initializing Puter.js AI Agent...');
    window.puterAI = new PuterAIAgent();
} catch (error) {
    console.error('Failed to initialize Puter.js AI Agent:', error);
}

// Ensure proper initialization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready, AI Agent initialized');
    try {
        if (!window.puterAI || !window.puterAI.isInitialized) {
            console.log('Reinitializing AI Agent...');
            window.puterAI = new PuterAIAgent();
        }
    } catch (error) {
        console.error('Failed to initialize Puter.js AI Agent:', error);
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PuterAIAgent;
}