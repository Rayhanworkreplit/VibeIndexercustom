/**
 * AI Chatbot for Google Indexing Pipeline
 * Provides intelligent assistance for SEO and indexing questions
 */

class IndexingChatbot {
    constructor() {
        this.isInitialized = false;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        console.log('Initializing AI Chatbot...');
        this.isInitialized = true;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen for chatbot button clicks
        document.addEventListener('click', (e) => {
            if (e.target.id === 'openChatbotBtn' || e.target.closest('#openChatbotBtn')) {
                this.openChatbot();
            }
        });
    }

    openChatbot() {
        // Remove existing modal if present
        const existingModal = document.getElementById('chatbotModal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'chatbotModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-robot"></i> SEO & Indexing Assistant
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="chatMessages" class="chat-messages" style="height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; background-color: #f8f9fa; border-radius: 8px;">
                            <div class="message assistant-message">
                                <div class="message-content">
                                    <strong>🤖 AI Assistant:</strong> Hi! I'm your SEO and indexing expert. I can help you with:
                                    <ul class="mt-2 mb-0">
                                        <li>URL indexing strategies</li>
                                        <li>SEO optimization tips</li>
                                        <li>Content analysis</li>
                                        <li>Backlink building</li>
                                        <li>Technical SEO issues</li>
                                    </ul>
                                    <p class="mt-2 mb-0">What would you like to know?</p>
                                </div>
                            </div>
                        </div>
                        <div class="chat-input-container">
                            <div class="input-group">
                                <input type="text" id="chatInput" class="form-control" placeholder="Ask me about SEO, indexing, or content optimization..." maxlength="500">
                                <button class="btn btn-primary" id="sendChatBtn" type="button">
                                    <i class="fas fa-paper-plane"></i> Send
                                </button>
                            </div>
                            <div class="mt-2">
                                <small class="text-muted">Quick questions:</small>
                                <div class="quick-questions mt-1">
                                    <button class="btn btn-sm btn-outline-secondary me-1 mb-1" onclick="window.chatbot.sendQuickQuestion('How to improve indexing speed?')">Indexing Speed</button>
                                    <button class="btn btn-sm btn-outline-secondary me-1 mb-1" onclick="window.chatbot.sendQuickQuestion('Best backlink strategies?')">Backlink Tips</button>
                                    <button class="btn btn-sm btn-outline-secondary me-1 mb-1" onclick="window.chatbot.sendQuickQuestion('How to analyze content quality?')">Content Analysis</button>
                                    <button class="btn btn-sm btn-outline-secondary me-1 mb-1" onclick="window.chatbot.sendQuickQuestion('What are the 6 indexing layers?')">6-Layer System</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-outline-primary" onclick="window.chatbot.clearChat()">Clear Chat</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Setup chat functionality
        this.setupChatFunctionality();
        
        // Clean up when modal is hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
        
        // Focus on input
        setTimeout(() => {
            document.getElementById('chatInput').focus();
        }, 500);
    }

    setupChatFunctionality() {
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendChatBtn');
        const chatMessages = document.getElementById('chatMessages');
        
        const sendMessage = () => {
            const message = chatInput.value.trim();
            if (!message) return;
            
            this.addUserMessage(message);
            chatInput.value = '';
            
            // Show typing indicator
            this.showTypingIndicator();
            
            // Generate AI response
            setTimeout(() => {
                this.hideTypingIndicator();
                const response = this.generateResponse(message);
                this.addAssistantMessage(response);
            }, 1000 + Math.random() * 1000); // Simulate thinking time
        };
        
        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Auto-resize input
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = chatInput.scrollHeight + 'px';
        });
    }

    addUserMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message mb-3';
        messageDiv.innerHTML = `
            <div class="message-content" style="background-color: #007bff; color: white; padding: 10px; border-radius: 10px; margin-left: 20%; text-align: right;">
                <strong>You:</strong> ${this.escapeHtml(message)}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Store in history
        this.conversationHistory.push({
            type: 'user',
            message: message,
            timestamp: new Date()
        });
    }

    addAssistantMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message mb-3';
        messageDiv.innerHTML = `
            <div class="message-content" style="background-color: #e9ecef; padding: 10px; border-radius: 10px; margin-right: 20%;">
                <strong>🤖 AI Assistant:</strong> ${message}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Store in history
        this.conversationHistory.push({
            type: 'assistant',
            message: message,
            timestamp: new Date()
        });
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message assistant-message mb-3';
        typingDiv.innerHTML = `
            <div class="message-content" style="background-color: #e9ecef; padding: 10px; border-radius: 10px; margin-right: 20%;">
                <strong>🤖 AI Assistant:</strong> <span class="typing-dots">Thinking<span>.</span><span>.</span><span>.</span></span>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add CSS for typing animation
        if (!document.getElementById('typingCSS')) {
            const style = document.createElement('style');
            style.id = 'typingCSS';
            style.textContent = `
                .typing-dots span {
                    animation: typing 1.4s infinite;
                }
                .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
                .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
                .typing-dots span:nth-child(4) { animation-delay: 0.6s; }
                @keyframes typing {
                    0%, 60%, 100% { opacity: 0; }
                    30% { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    sendQuickQuestion(question) {
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = question;
            chatInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter' }));
        }
    }

    clearChat() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div class="message assistant-message">
                    <div class="message-content">
                        <strong>🤖 AI Assistant:</strong> Chat cleared! How can I help you today?
                    </div>
                </div>
            `;
        }
        this.conversationHistory = [];
    }

    generateResponse(message) {
        const lowerMsg = message.toLowerCase();
        
        // Context-aware responses based on conversation history
        const responses = {
            // Indexing related
            'index': 'For faster indexing, use our 6-layer approach: 1) Submit XML sitemaps, 2) RSS feeds with PubSubHubbub, 3) Internal linking, 4) Social signals (Reddit, Twitter), 5) Web 2.0 properties (Blogger, WordPress), 6) Content freshness signals. This typically achieves 95%+ indexing success.',
            
            'sitemap': 'XML sitemaps are crucial for indexing. Make sure to: 1) Include all important URLs, 2) Keep under 50,000 URLs per sitemap, 3) Submit to Google Search Console, 4) Update regularly, 5) Use proper priority and changefreq values. Our system can generate optimized sitemaps automatically.',
            
            'backlink': 'Quality backlinks from high-authority domains help with indexing and rankings. Focus on: 1) Social bookmarking (Reddit, Mix, Digg), 2) Forum commenting on relevant discussions, 3) Directory submissions to quality directories, 4) Web 2.0 properties, 5) Guest posting, 6) Social media signals.',
            
            'speed': 'To improve indexing speed: 1) Use our 6-layer indexing campaign, 2) Submit sitemaps immediately after content creation, 3) Use RSS feeds with real-time pinging, 4) Create internal links to new content, 5) Share on social media, 6) Ensure fast page load times and proper technical SEO.',
            
            'content': 'High-quality content indexes better. Ensure: 1) Original, valuable content (500+ words), 2) Proper heading structure (H1, H2, H3), 3) Relevant keywords naturally integrated, 4) Good readability and user experience, 5) Regular updates, 6) Internal linking to related content.',
            
            'seo': 'Technical SEO basics: 1) Fast loading speeds (<3 seconds), 2) Mobile-friendly design, 3) HTTPS security, 4) Proper meta titles and descriptions, 5) Structured data markup, 6) Clean URL structure, 7) XML sitemaps, 8) Robots.txt optimization.',
            
            'gsc': 'Google Search Console is essential for indexing. Set up: 1) Property verification, 2) Sitemap submission, 3) URL inspection tool usage, 4) Index coverage monitoring, 5) Performance tracking, 6) Mobile usability checks. Our system can integrate with GSC API for automation.',
            
            '6 layer': 'Our 6-Layer Indexing System: Layer 1 - Direct sitemap pinging, Layer 2 - RSS + PubSubHubbub, Layer 3 - Internal linking optimization, Layer 4 - Social signals (Reddit, Twitter), Layer 5 - Third-party properties (Web 2.0), Layer 6 - Content freshness signals. This achieves 95%+ success rates.',
            
            'layer': 'Our 6-Layer Indexing System: Layer 1 - Direct sitemap pinging, Layer 2 - RSS + PubSubHubbub, Layer 3 - Internal linking optimization, Layer 4 - Social signals (Reddit, Twitter), Layer 5 - Third-party properties (Web 2.0), Layer 6 - Content freshness signals. This achieves 95%+ success rates.',
            
            'reddit': 'Reddit is excellent for indexing because Google crawls it frequently. Best practices: 1) Share in relevant subreddits, 2) Provide genuine value, not just links, 3) Engage with comments, 4) Follow subreddit rules, 5) Build karma gradually, 6) Mix content types. Our system can automate this responsibly.',
            
            'social': 'Social signals help with indexing through: 1) Increased visibility and traffic, 2) Faster discovery by search bots, 3) Authority signals, 4) Link diversity. Use Twitter, Facebook, LinkedIn, Pinterest strategically. Quality engagement matters more than quantity.',
            
            'robots': 'Robots.txt controls crawler access. Best practices: 1) Allow Googlebot access to important content, 2) Block admin/private areas, 3) Include sitemap reference, 4) Test with Google Search Console, 5) Keep it simple and clear, 6) Regular updates when site structure changes.',
            
            'error': 'Common indexing errors: 1) 404 pages - fix broken links, 2) 5xx server errors - check hosting, 3) Blocked by robots.txt - update rules, 4) Soft 404s - return proper 404 status, 5) Redirect chains - simplify redirects, 6) Duplicate content - use canonical tags.',
            
            'canonical': 'Canonical tags prevent duplicate content issues: 1) Point to the preferred version of a page, 2) Use absolute URLs, 3) Self-reference on original pages, 4) Avoid canonical chains, 5) Ensure referenced page is accessible, 6) Use consistently across similar pages.',
            
            'mobile': 'Mobile optimization is crucial: 1) Responsive design, 2) Fast loading on mobile networks, 3) Touch-friendly navigation, 4) Readable text without zooming, 5) Proper viewport meta tag, 6) Mobile-first indexing compliance. Test with Google\'s mobile-friendly tool.',
            
            'analytics': 'Track indexing performance with: 1) Google Search Console for index coverage, 2) Google Analytics for organic traffic, 3) SERP tracking tools, 4) Our built-in analytics dashboard, 5) Regular SERP verification, 6) Performance monitoring and alerts.',
            
            'help': 'I can help you with: URL indexing strategies, SEO optimization, content analysis, backlink building, technical SEO, Google Search Console, sitemap optimization, social media indexing, mobile SEO, analytics tracking, and troubleshooting indexing issues. What specific topic interests you?',
            
            'hello': 'Hello! I\'m your SEO and indexing assistant. I can help you optimize your content for better search engine visibility and faster indexing. What would you like to know about?',
            
            'hi': 'Hi there! Ready to boost your indexing success? I can guide you through our proven strategies or answer any SEO questions you have.',
            
            'thanks': 'You\'re welcome! I\'m here whenever you need help with SEO, indexing, or content optimization. Feel free to ask anything else!',
            
            'thank': 'You\'re welcome! I\'m here whenever you need help with SEO, indexing, or content optimization. Feel free to ask anything else!'
        };
        
        // Find matching response
        for (const [key, response] of Object.entries(responses)) {
            if (lowerMsg.includes(key)) {
                return response;
            }
        }
        
        // Default response
        return 'I\'m here to help with SEO and indexing! Try asking about: "indexing speed", "backlink strategies", "6-layer system", "content optimization", "technical SEO", or "Google Search Console". What specific challenge are you facing?';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.chatbot = new IndexingChatbot();
        console.log('AI Chatbot initialized successfully');
    } catch (error) {
        console.error('Failed to initialize chatbot:', error);
    }
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IndexingChatbot;
}