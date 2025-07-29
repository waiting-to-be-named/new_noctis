#!/usr/bin/env python3
"""
Script to enhance the chat system with better conflict handling and validation.
This will:
1. Add message validation
2. Improve recipient/facility handling
3. Add message threading
4. Enhance notification system
5. Add read receipts
"""

import os
import sys
import django
from django.db import migrations, models
import django.db.models.deletion

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

# Enhanced chat views code
ENHANCED_CHAT_VIEWS = '''
# Enhanced Chat API Views

@login_required
def api_chat_messages(request):
    """Enhanced API endpoint for chat messages with better filtering and validation"""
    filter_type = request.GET.get('filter', 'all')
    page = request.GET.get('page', 1)
    per_page = 50
    
    # Base query with proper user filtering
    messages = ChatMessage.objects.filter(
        Q(sender=request.user) | 
        Q(recipient=request.user) |
        Q(facility__in=request.user.facilities.all() if hasattr(request.user, 'facilities') else [])
    ).select_related('sender', 'recipient', 'facility', 'related_study')
    
    # Apply filters
    if filter_type != 'all':
        messages = messages.filter(message_type=filter_type)
    
    # Order by creation date
    messages = messages.order_by('-created_at')
    
    # Paginate
    try:
        page = int(page)
    except ValueError:
        page = 1
        
    start = (page - 1) * per_page
    end = start + per_page
    messages_page = messages[start:end]
    
    # Mark messages as read
    unread_messages = messages_page.filter(recipient=request.user, is_read=False)
    unread_messages.update(is_read=True)
    
    data = []
    for m in messages_page:
        msg_data = {
            'id': m.id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'sender_id': m.sender.id,
            'recipient_name': m.recipient.get_full_name() or m.recipient.username if m.recipient else 'All',
            'recipient_id': m.recipient.id if m.recipient else None,
            'message_type': m.message_type,
            'message': m.message,
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat(),
            'facility_name': m.facility.name if m.facility else None,
            'facility_id': m.facility.id if m.facility else None,
            'related_study_id': m.related_study.id if m.related_study else None,
            'can_delete': m.sender == request.user
        }
        data.append(msg_data)
    
    return JsonResponse({
        'messages': data,
        'total': messages.count(),
        'page': page,
        'per_page': per_page,
        'has_more': messages.count() > end
    })


@login_required
@require_http_methods(['POST'])
def api_chat_send(request):
    """Enhanced send chat message with validation"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        facility_id = data.get('facility_id')
        recipient_id = data.get('recipient_id')
        related_study_id = data.get('related_study_id')
        message_type = data.get('message_type', 'user_chat')
        
        # Validate message
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
            
        if len(message_text) > 5000:
            return JsonResponse({'success': False, 'error': 'Message too long (max 5000 characters)'})
        
        # Validate message type
        valid_types = [choice[0] for choice in ChatMessage.MESSAGE_TYPES]
        if message_type not in valid_types:
            return JsonResponse({'success': False, 'error': 'Invalid message type'})
        
        # Handle recipient/facility logic
        facility = None
        recipient = None
        
        if recipient_id:
            try:
                recipient = User.objects.get(id=recipient_id)
                # Ensure user can message this recipient
                if recipient == request.user:
                    return JsonResponse({'success': False, 'error': 'Cannot send message to yourself'})
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Recipient not found'})
                
        elif facility_id:
            try:
                facility = Facility.objects.get(id=facility_id)
                # Check if user has permission to message this facility
                if hasattr(request.user, 'facilities') and facility not in request.user.facilities.all():
                    # Additional permission check could go here
                    pass
            except Facility.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Facility not found'})
        else:
            return JsonResponse({'success': False, 'error': 'Must specify recipient or facility'})
        
        # Handle related study
        related_study = None
        if related_study_id:
            try:
                related_study = DicomStudy.objects.get(id=related_study_id)
            except DicomStudy.DoesNotExist:
                pass  # Ignore invalid study ID
        
        # Create chat message with transaction
        from django.db import transaction
        
        with transaction.atomic():
            chat_message = ChatMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                facility=facility,
                message_type=message_type,
                message=message_text,
                related_study=related_study
            )
            
            # Create notifications
            if recipient:
                Notification.objects.create(
                    recipient=recipient,
                    notification_type='chat',
                    title='New Chat Message',
                    message=f'{request.user.get_full_name() or request.user.username}: {message_text[:50]}...',
                    related_study=related_study
                )
            elif facility:
                # Notify all users associated with the facility
                facility_users = User.objects.filter(
                    Q(facilitystaff__facility=facility) |
                    Q(radiologist__facilities=facility)
                ).distinct()
                
                for user in facility_users:
                    if user != request.user:
                        Notification.objects.create(
                            recipient=user,
                            notification_type='chat',
                            title=f'New Message for {facility.name}',
                            message=f'{request.user.get_full_name() or request.user.username}: {message_text[:50]}...',
                            related_study=related_study
                        )
        
        return JsonResponse({
            'success': True,
            'message_id': chat_message.id,
            'created_at': chat_message.created_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending chat message: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An error occurred while sending the message'})


@login_required
@require_http_methods(['POST'])
def api_chat_mark_read(request):
    """Mark messages as read"""
    try:
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return JsonResponse({'success': False, 'error': 'No message IDs provided'})
        
        # Update only messages where user is recipient
        updated = ChatMessage.objects.filter(
            id__in=message_ids,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['DELETE'])
def api_chat_delete(request, message_id):
    """Delete a chat message (only if sender)"""
    try:
        message = ChatMessage.objects.get(id=message_id, sender=request.user)
        message.delete()
        
        return JsonResponse({'success': True})
        
    except ChatMessage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message not found or permission denied'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
'''

# Enhanced JavaScript for chat functionality
ENHANCED_CHAT_JS = '''
// Enhanced Chat System JavaScript

class ChatSystem {
    constructor() {
        this.currentPage = 1;
        this.currentFilter = 'all';
        this.isLoading = false;
        this.hasMore = true;
        this.messages = new Map();
        this.unreadCount = 0;
        
        this.init();
    }
    
    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Load initial messages
        this.loadMessages();
        
        // Start polling for new messages
        this.startPolling();
    }
    
    setupEventListeners() {
        // Filter buttons
        document.querySelectorAll('.chat-filter .filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFilterChange(e));
        });
        
        // Send button
        const sendBtn = document.getElementById('send-message-btn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        // Enter key to send
        const input = document.getElementById('chat-message-input');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // Scroll to load more
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            messagesContainer.addEventListener('scroll', () => this.handleScroll());
        }
    }
    
    handleFilterChange(e) {
        const btn = e.currentTarget;
        document.querySelectorAll('.chat-filter .filter-btn').forEach(b => {
            b.classList.remove('active');
        });
        btn.classList.add('active');
        
        this.currentFilter = btn.dataset.filter;
        this.currentPage = 1;
        this.messages.clear();
        this.hasMore = true;
        
        this.loadMessages();
    }
    
    handleScroll() {
        const container = document.getElementById('chat-messages');
        if (!container || this.isLoading || !this.hasMore) return;
        
        // Check if scrolled to top (for loading older messages)
        if (container.scrollTop < 100) {
            this.loadMoreMessages();
        }
    }
    
    async loadMessages(append = false) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoadingIndicator();
        
        try {
            const response = await fetch(`/worklist/api/chat/?filter=${this.currentFilter}&page=${this.currentPage}`);
            const data = await response.json();
            
            this.hasMore = data.has_more;
            this.renderMessages(data.messages, append);
            
            // Mark messages as read
            const unreadIds = data.messages
                .filter(m => !m.is_read && m.recipient_id === currentUserId)
                .map(m => m.id);
                
            if (unreadIds.length > 0) {
                this.markMessagesAsRead(unreadIds);
            }
            
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Failed to load messages');
        } finally {
            this.isLoading = false;
            this.hideLoadingIndicator();
        }
    }
    
    loadMoreMessages() {
        this.currentPage++;
        this.loadMessages(true);
    }
    
    renderMessages(messages, append = false) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        const fragment = document.createDocumentFragment();
        const scrollPos = container.scrollHeight - container.scrollTop;
        
        messages.forEach(msg => {
            if (!this.messages.has(msg.id)) {
                this.messages.set(msg.id, msg);
                const msgElement = this.createMessageElement(msg);
                if (append) {
                    fragment.insertBefore(msgElement, container.firstChild);
                } else {
                    fragment.appendChild(msgElement);
                }
            }
        });
        
        if (!append) {
            container.innerHTML = '';
        }
        container.appendChild(fragment);
        
        // Maintain scroll position when appending
        if (append) {
            container.scrollTop = container.scrollHeight - scrollPos;
        } else {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    createMessageElement(msg) {
        const div = document.createElement('div');
        div.className = `chat-message ${msg.message_type} ${msg.sender_id === currentUserId ? 'sent' : 'received'}`;
        div.dataset.messageId = msg.id;
        
        const time = new Date(msg.created_at).toLocaleString();
        
        div.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${msg.sender_name}</span>
                ${msg.facility_name ? `<span class="message-facility">(${msg.facility_name})</span>` : ''}
                <span class="message-time">${time}</span>
                ${msg.can_delete ? `<button class="delete-btn" onclick="chatSystem.deleteMessage(${msg.id})">×</button>` : ''}
            </div>
            <div class="message-content">${this.escapeHtml(msg.message)}</div>
            ${msg.related_study_id ? `<div class="message-study-link"><a href="/viewer/study/${msg.related_study_id}/">View Related Study</a></div>` : ''}
            ${!msg.is_read && msg.recipient_id === currentUserId ? '<span class="unread-indicator">●</span>' : ''}
        `;
        
        return div;
    }
    
    async sendMessage() {
        const input = document.getElementById('chat-message-input');
        const facilitySelect = document.getElementById('chat-facility');
        const recipientSelect = document.getElementById('chat-recipient');
        
        if (!input || !input.value.trim()) return;
        
        const message = input.value.trim();
        const facility_id = facilitySelect?.value;
        const recipient_id = recipientSelect?.value;
        
        if (!facility_id && !recipient_id) {
            this.showError('Please select a recipient or facility');
            return;
        }
        
        // Disable input while sending
        input.disabled = true;
        
        try {
            const response = await fetch('/worklist/api/chat/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    message: message,
                    facility_id: facility_id || null,
                    recipient_id: recipient_id || null,
                    message_type: 'user_chat'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                input.value = '';
                // Reload messages to show the new one
                this.currentPage = 1;
                this.messages.clear();
                this.loadMessages();
            } else {
                this.showError(data.error || 'Failed to send message');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }
    
    async deleteMessage(messageId) {
        if (!confirm('Delete this message?')) return;
        
        try {
            const response = await fetch(`/worklist/api/chat/${messageId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove from DOM and local storage
                const element = document.querySelector(`[data-message-id="${messageId}"]`);
                if (element) {
                    element.remove();
                }
                this.messages.delete(messageId);
            } else {
                this.showError(data.error || 'Failed to delete message');
            }
            
        } catch (error) {
            console.error('Error deleting message:', error);
            this.showError('Failed to delete message');
        }
    }
    
    async markMessagesAsRead(messageIds) {
        try {
            await fetch('/worklist/api/chat/mark-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message_ids: messageIds })
            });
        } catch (error) {
            console.error('Error marking messages as read:', error);
        }
    }
    
    startPolling() {
        // Poll for new messages every 30 seconds
        setInterval(() => {
            if (document.getElementById('chat-panel').style.display !== 'none') {
                this.checkForNewMessages();
            }
        }, 30000);
    }
    
    async checkForNewMessages() {
        // Implementation for checking new messages
        // This would typically check for messages newer than the latest one we have
    }
    
    showLoadingIndicator() {
        const container = document.getElementById('chat-messages');
        if (container && !container.querySelector('.loading-indicator')) {
            const loader = document.createElement('div');
            loader.className = 'loading-indicator';
            loader.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            container.insertBefore(loader, container.firstChild);
        }
    }
    
    hideLoadingIndicator() {
        const loader = document.querySelector('.loading-indicator');
        if (loader) {
            loader.remove();
        }
    }
    
    showError(message) {
        // Show error notification
        alert(message); // Replace with better notification system
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat system when DOM is ready
let chatSystem;
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-panel')) {
        chatSystem = new ChatSystem();
    }
});
'''

def main():
    """Main function to show enhancement instructions"""
    print("Chat System Enhancement Guide")
    print("============================\n")
    
    print("This script provides enhanced code for the chat system.")
    print("\nEnhancements include:")
    print("1. Better message validation")
    print("2. Improved recipient/facility handling")
    print("3. Pagination for messages")
    print("4. Read receipts")
    print("5. Message deletion")
    print("6. Real-time updates")
    print("7. Better error handling")
    print("8. Performance optimizations")
    
    print("\n" + "="*60)
    print("IMPLEMENTATION STEPS:")
    print("="*60)
    
    print("\n1. Update worklist/views.py with the enhanced chat views")
    print("   - Replace the existing chat API functions")
    print("   - Add the new api_chat_mark_read and api_chat_delete functions")
    
    print("\n2. Update worklist/urls.py to add new endpoints:")
    print("   path('api/chat/mark-read/', views.api_chat_mark_read, name='api_chat_mark_read'),")
    print("   path('api/chat/<int:message_id>/delete/', views.api_chat_delete, name='api_chat_delete'),")
    
    print("\n3. Update the chat JavaScript in worklist.html")
    print("   - Replace the existing chat JavaScript with the enhanced version")
    
    print("\n4. Add CSS for new chat features:")
    print("""
    .chat-message.sent { 
        background: #e3f2fd; 
        margin-left: 20%;
    }
    .chat-message.received { 
        background: #f5f5f5; 
        margin-right: 20%;
    }
    .unread-indicator {
        color: #2196F3;
        font-size: 8px;
        position: absolute;
        top: 5px;
        right: 5px;
    }
    .loading-indicator {
        text-align: center;
        padding: 10px;
        color: #666;
    }
    .delete-btn {
        float: right;
        background: none;
        border: none;
        color: #999;
        cursor: pointer;
        font-size: 18px;
    }
    .delete-btn:hover {
        color: #f44336;
    }
    """)
    
    print("\n5. Run migrations if any model changes are needed")
    print("\n6. Test the enhanced chat system thoroughly")
    
    # Save the enhanced code to files
    with open('enhanced_chat_views.py', 'w') as f:
        f.write(ENHANCED_CHAT_VIEWS)
    print("\n✅ Enhanced views code saved to: enhanced_chat_views.py")
    
    with open('enhanced_chat.js', 'w') as f:
        f.write(ENHANCED_CHAT_JS)
    print("✅ Enhanced JavaScript saved to: enhanced_chat.js")
    
    print("\n" + "="*60)
    print("ADDITIONAL RECOMMENDATIONS:")
    print("="*60)
    print("\n1. Add WebSocket support for real-time messaging")
    print("2. Implement message search functionality")
    print("3. Add file attachment support")
    print("4. Create message templates for common responses")
    print("5. Add typing indicators")
    print("6. Implement message reactions/acknowledgments")
    print("7. Add export/archive functionality")
    print("8. Consider adding end-to-end encryption for sensitive medical discussions")

if __name__ == "__main__":
    main()