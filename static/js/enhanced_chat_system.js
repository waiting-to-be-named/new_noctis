// Enhanced Chat System for DICOM Viewer
// Created from today's enhancement discussions
// Provides real-time communication for medical teams

class EnhancedChatSystem {
    constructor() {
        this.isInitialized = false;
        this.currentUser = null;
        this.chatHistory = [];
        this.unreadCount = 0;
        this.isMinimized = false;
        this.autoRefresh = true;
        this.refreshInterval = 5000; // 5 seconds
        this.refreshTimer = null;
        
        // Chat types
        this.chatTypes = {
            SYSTEM_UPLOAD: 'system_upload',
            USER_CHAT: 'user_chat',
            SYSTEM_NOTIFICATION: 'system_notification',
            URGENT_MESSAGE: 'urgent_message'
        };
        
        this.init();
    }
    
    init() {
        this.createChatInterface();
        this.setupEventListeners();
        this.loadChatHistory();
        this.startAutoRefresh();
        this.isInitialized = true;
        console.log('✅ Enhanced Chat System initialized');
    }
    
    createChatInterface() {
        const chatHTML = `
            <div class="enhanced-chat-container" id="enhanced-chat-container">
                <div class="chat-header" id="chat-header">
                    <div class="chat-title">
                        <i class="fas fa-comments"></i>
                        <span>Team Chat</span>
                        <span class="unread-badge" id="unread-badge" style="display: none;">0</span>
                    </div>
                    <div class="chat-controls">
                        <button class="chat-btn" id="chat-minimize-btn" title="Minimize">
                            <i class="fas fa-minus"></i>
                        </button>
                        <button class="chat-btn" id="chat-clear-btn" title="Clear History">
                            <i class="fas fa-trash"></i>
                        </button>
                        <button class="chat-btn" id="chat-refresh-btn" title="Refresh">
                            <i class="fas fa-sync"></i>
                        </button>
                    </div>
                </div>
                
                <div class="chat-body" id="chat-body">
                    <div class="chat-messages" id="chat-messages">
                        <div class="loading-message">Loading chat history...</div>
                    </div>
                    
                    <div class="chat-input-area">
                        <div class="input-group">
                            <select class="message-type-selector" id="message-type">
                                <option value="user_chat">💬 Chat</option>
                                <option value="system_notification">📢 Notification</option>
                                <option value="urgent_message">🚨 Urgent</option>
                            </select>
                            <input 
                                type="text" 
                                class="chat-input" 
                                id="chat-input" 
                                placeholder="Type your message..."
                                maxlength="500"
                            >
                            <button class="send-btn" id="send-btn">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                        <div class="input-info">
                            <span id="char-count">0/500</span>
                            <button class="emoji-btn" id="emoji-btn" title="Insert Emoji">😊</button>
                        </div>
                    </div>
                </div>
                
                <div class="emoji-picker" id="emoji-picker" style="display: none;">
                    <div class="emoji-grid">
                        <span class="emoji-item">😊</span>
                        <span class="emoji-item">👍</span>
                        <span class="emoji-item">👎</span>
                        <span class="emoji-item">❤️</span>
                        <span class="emoji-item">🎉</span>
                        <span class="emoji-item">🔥</span>
                        <span class="emoji-item">💯</span>
                        <span class="emoji-item">🚨</span>
                        <span class="emoji-item">📋</span>
                        <span class="emoji-item">🩺</span>
                        <span class="emoji-item">🏥</span>
                        <span class="emoji-item">⚕️</span>
                    </div>
                </div>
            </div>
        `;
        
        // Add chat to the page
        const existingChat = document.getElementById('enhanced-chat-container');
        if (existingChat) {
            existingChat.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', chatHTML);
    }
    
    setupEventListeners() {
        // Minimize/maximize chat
        const minimizeBtn = document.getElementById('chat-minimize-btn');
        minimizeBtn?.addEventListener('click', () => {
            this.toggleMinimize();
        });
        
        // Clear chat history
        const clearBtn = document.getElementById('chat-clear-btn');
        clearBtn?.addEventListener('click', () => {
            this.clearChatHistory();
        });
        
        // Refresh chat
        const refreshBtn = document.getElementById('chat-refresh-btn');
        refreshBtn?.addEventListener('click', () => {
            this.loadChatHistory();
        });
        
        // Send message
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        
        sendBtn?.addEventListener('click', () => {
            this.sendMessage();
        });
        
        chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Character counter
        chatInput?.addEventListener('input', (e) => {
            const count = e.target.value.length;
            document.getElementById('char-count').textContent = `${count}/500`;
        });
        
        // Emoji picker
        const emojiBtn = document.getElementById('emoji-btn');
        const emojiPicker = document.getElementById('emoji-picker');
        
        emojiBtn?.addEventListener('click', () => {
            emojiPicker.style.display = emojiPicker.style.display === 'none' ? 'block' : 'none';
        });
        
        // Emoji selection
        document.querySelectorAll('.emoji-item').forEach(emoji => {
            emoji.addEventListener('click', () => {
                this.insertEmoji(emoji.textContent);
                emojiPicker.style.display = 'none';
            });
        });
        
        // Click outside to close emoji picker
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.emoji-picker') && !e.target.closest('.emoji-btn')) {
                emojiPicker.style.display = 'none';
            }
        });
        
        // Auto-scroll to bottom when new messages arrive
        const chatMessages = document.getElementById('chat-messages');
        chatMessages?.addEventListener('DOMNodeInserted', () => {
            this.scrollToBottom();
        });
    }
    
    async loadChatHistory() {
        try {
            const refreshBtn = document.getElementById('chat-refresh-btn');
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            }
            
            const response = await fetch('/worklist/api/chat/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.chatHistory = data.messages || [];
                this.renderChatHistory();
                this.updateUnreadCount();
            } else {
                throw new Error('Failed to load chat history');
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            this.showError('Failed to load chat history');
        } finally {
            const refreshBtn = document.getElementById('chat-refresh-btn');
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-sync"></i>';
            }
        }
    }
    
    renderChatHistory() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        if (this.chatHistory.length === 0) {
            chatMessages.innerHTML = '<div class="no-messages">No messages yet. Start the conversation!</div>';
            return;
        }
        
        const messagesHTML = this.chatHistory.map(message => {
            return this.createMessageHTML(message);
        }).join('');
        
        chatMessages.innerHTML = messagesHTML;
        this.scrollToBottom();
    }
    
    createMessageHTML(message) {
        const timestamp = this.formatTimestamp(message.timestamp);
        const messageClass = this.getMessageClass(message.message_type);
        const icon = this.getMessageIcon(message.message_type);
        
        return `
            <div class="chat-message ${messageClass}" data-id="${message.id}">
                <div class="message-header">
                    <span class="message-icon">${icon}</span>
                    <span class="message-sender">${message.user || 'System'}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                <div class="message-content">${this.formatMessageContent(message.message)}</div>
            </div>
        `;
    }
    
    getMessageClass(messageType) {
        switch (messageType) {
            case this.chatTypes.SYSTEM_UPLOAD:
                return 'system-message';
            case this.chatTypes.URGENT_MESSAGE:
                return 'urgent-message';
            case this.chatTypes.SYSTEM_NOTIFICATION:
                return 'notification-message';
            default:
                return 'user-message';
        }
    }
    
    getMessageIcon(messageType) {
        switch (messageType) {
            case this.chatTypes.SYSTEM_UPLOAD:
                return '📁';
            case this.chatTypes.URGENT_MESSAGE:
                return '🚨';
            case this.chatTypes.SYSTEM_NOTIFICATION:
                return '📢';
            default:
                return '💬';
        }
    }
    
    formatMessageContent(content) {
        // Convert URLs to links
        content = content.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" rel="noopener">$1</a>'
        );
        
        // Convert line breaks
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            return `${Math.floor(diff / 60000)}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            return `${Math.floor(diff / 3600000)}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const messageType = document.getElementById('message-type').value;
        const message = input?.value.trim();
        
        if (!message) return;
        
        try {
            const sendBtn = document.getElementById('send-btn');
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            sendBtn.disabled = true;
            
            const response = await fetch('/worklist/api/chat/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    message: message,
                    message_type: messageType
                })
            });
            
            if (response.ok) {
                input.value = '';
                document.getElementById('char-count').textContent = '0/500';
                this.loadChatHistory(); // Refresh to show new message
                this.showSuccess('Message sent');
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message');
        } finally {
            const sendBtn = document.getElementById('send-btn');
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            sendBtn.disabled = false;
        }
    }
    
    async clearChatHistory() {
        if (!confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch('/worklist/api/chat/clear/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.chatHistory = [];
                this.renderChatHistory();
                this.showSuccess('Chat history cleared');
            } else {
                throw new Error('Failed to clear chat history');
            }
        } catch (error) {
            console.error('Error clearing chat history:', error);
            this.showError('Failed to clear chat history');
        }
    }
    
    toggleMinimize() {
        const chatBody = document.getElementById('chat-body');
        const minimizeBtn = document.getElementById('chat-minimize-btn');
        
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            chatBody.style.display = 'none';
            minimizeBtn.innerHTML = '<i class="fas fa-plus"></i>';
            minimizeBtn.title = 'Maximize';
        } else {
            chatBody.style.display = 'block';
            minimizeBtn.innerHTML = '<i class="fas fa-minus"></i>';
            minimizeBtn.title = 'Minimize';
            this.scrollToBottom();
        }
    }
    
    insertEmoji(emoji) {
        const input = document.getElementById('chat-input');
        if (input) {
            const cursorPos = input.selectionStart;
            const textBefore = input.value.substring(0, cursorPos);
            const textAfter = input.value.substring(cursorPos);
            input.value = textBefore + emoji + textAfter;
            input.focus();
            input.setSelectionRange(cursorPos + emoji.length, cursorPos + emoji.length);
            
            // Update character count
            document.getElementById('char-count').textContent = `${input.value.length}/500`;
        }
    }
    
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    updateUnreadCount() {
        // This would typically track unread messages
        // For now, we'll just hide the badge
        const badge = document.getElementById('unread-badge');
        if (badge) {
            badge.style.display = 'none';
        }
    }
    
    startAutoRefresh() {
        if (this.autoRefresh && !this.refreshTimer) {
            this.refreshTimer = setInterval(() => {
                if (!this.isMinimized) {
                    this.loadChatHistory();
                }
            }, this.refreshInterval);
        }
    }
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `chat-notification ${type}`;
        notification.textContent = message;
        
        // Add to page
        const container = document.getElementById('enhanced-chat-container');
        if (container) {
            container.appendChild(notification);
            
            // Remove after 3 seconds
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }
    
    // Public API methods
    destroy() {
        this.stopAutoRefresh();
        const container = document.getElementById('enhanced-chat-container');
        if (container) {
            container.remove();
        }
        this.isInitialized = false;
    }
    
    setAutoRefresh(enabled) {
        this.autoRefresh = enabled;
        if (enabled) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }
    
    setRefreshInterval(ms) {
        this.refreshInterval = ms;
        if (this.refreshTimer) {
            this.stopAutoRefresh();
            this.startAutoRefresh();
        }
    }
}

// Enhanced Chat CSS Styles
const chatCSS = `
.enhanced-chat-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 350px;
    max-height: 500px;
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
    border: 1px solid rgba(0, 255, 136, 0.3);
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    z-index: 1000;
    font-family: 'Segoe UI', sans-serif;
    display: flex;
    flex-direction: column;
}

.chat-header {
    background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
    padding: 12px 15px;
    border-radius: 10px 10px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: white;
    border-bottom: 2px solid #00ff88;
}

.chat-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: bold;
    font-size: 14px;
}

.unread-badge {
    background: #ff3333;
    color: white;
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
}

.chat-controls {
    display: flex;
    gap: 5px;
}

.chat-btn {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    padding: 5px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: background 0.2s;
}

.chat-btn:hover {
    background: rgba(255, 255, 255, 0.3);
}

.chat-body {
    display: flex;
    flex-direction: column;
    height: 400px;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    background: rgba(0, 0, 0, 0.1);
    border-radius: 0 0 10px 10px;
}

.chat-message {
    margin-bottom: 15px;
    padding: 10px;
    border-radius: 8px;
    border-left: 3px solid transparent;
}

.user-message {
    background: rgba(59, 130, 246, 0.1);
    border-left-color: #3b82f6;
}

.system-message {
    background: rgba(156, 163, 175, 0.1);
    border-left-color: #9ca3af;
}

.urgent-message {
    background: rgba(239, 68, 68, 0.1);
    border-left-color: #ef4444;
    animation: pulse 2s infinite;
}

.notification-message {
    background: rgba(0, 255, 136, 0.1);
    border-left-color: #00ff88;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.message-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 5px;
    font-size: 11px;
    color: #9ca3af;
}

.message-icon {
    font-size: 14px;
}

.message-sender {
    font-weight: bold;
    color: #e0e6ed;
}

.message-time {
    margin-left: auto;
}

.message-content {
    color: #e0e6ed;
    font-size: 13px;
    line-height: 1.4;
}

.message-content a {
    color: #3b82f6;
    text-decoration: none;
}

.message-content a:hover {
    text-decoration: underline;
}

.chat-input-area {
    padding: 15px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 0 0 10px 10px;
}

.input-group {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
}

.message-type-selector {
    background: #374151;
    border: 1px solid #4b5563;
    color: #e0e6ed;
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    min-width: 80px;
}

.chat-input {
    flex: 1;
    background: #374151;
    border: 1px solid #4b5563;
    color: #e0e6ed;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.chat-input:focus {
    border-color: #00ff88;
    box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2);
}

.send-btn {
    background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
    border: none;
    color: #0a0a0a;
    padding: 8px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: transform 0.2s;
}

.send-btn:hover {
    transform: translateY(-1px);
}

.send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

.input-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #9ca3af;
}

.emoji-btn {
    background: none;
    border: none;
    font-size: 16px;
    cursor: pointer;
    padding: 2px;
}

.emoji-picker {
    position: absolute;
    bottom: 80px;
    right: 15px;
    background: #374151;
    border: 1px solid #4b5563;
    border-radius: 8px;
    padding: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    z-index: 1001;
}

.emoji-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
}

.emoji-item {
    font-size: 18px;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
    text-align: center;
    transition: background 0.2s;
}

.emoji-item:hover {
    background: rgba(255, 255, 255, 0.1);
}

.loading-message, .no-messages {
    text-align: center;
    color: #9ca3af;
    font-style: italic;
    padding: 20px;
}

.chat-notification {
    position: absolute;
    top: -40px;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    z-index: 1002;
    animation: slideDown 0.3s ease;
}

.chat-notification.success {
    background: #00ff88;
    color: #0a0a0a;
}

.chat-notification.error {
    background: #ef4444;
    color: white;
}

@keyframes slideDown {
    from { transform: translateX(-50%) translateY(-20px); opacity: 0; }
    to { transform: translateX(-50%) translateY(0); opacity: 1; }
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
    width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
}

.chat-messages::-webkit-scrollbar-thumb {
    background: rgba(0, 255, 136, 0.3);
    border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 255, 136, 0.5);
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .enhanced-chat-container {
        width: calc(100vw - 40px);
        right: 20px;
        left: 20px;
    }
}
`;

// Inject CSS
if (!document.getElementById('enhanced-chat-css')) {
    const style = document.createElement('style');
    style.id = 'enhanced-chat-css';
    style.textContent = chatCSS;
    document.head.appendChild(style);
}

// Global initialization function
function initializeEnhancedChat() {
    if (!window.enhancedChat) {
        window.enhancedChat = new EnhancedChatSystem();
        console.log('✅ Enhanced Chat System initialized');
    }
    return window.enhancedChat;
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEnhancedChat);
} else {
    initializeEnhancedChat();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedChatSystem;
}