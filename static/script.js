// Initialize Socket.IO with optimized settings for real-time performance
const socket = io({
    transports: ['websocket', 'polling'],
    upgrade: true,
    rememberUpgrade: true,
    timeout: 5000,
    forceNew: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    maxReconnectionAttempts: 10
});

// Real-time state management
let connectionStatus = 'connecting';
let typingUsers = new Set();
let typingTimer = null;
let heartbeatInterval = null;
let messageQueue = [];
let lastHeartbeat = Date.now();

// Get current user ID from the page context
let currentUserId = null;
let isAdmin = false;

// Show connection status immediately
document.addEventListener('DOMContentLoaded', function() {
    // Initialize connection status indicator first
    updateConnectionStatus();
});

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Try to get currentUserId from different sources
    const userIdElement = document.querySelector('[data-user-id]');
    if (userIdElement) {
        currentUserId = parseInt(userIdElement.getAttribute('data-user-id'));
    } else if (window.currentUserId) {
        currentUserId = window.currentUserId;
    }
    
    // Get admin status
    if (window.isAdmin) {
        isAdmin = window.isAdmin;
    }
    
    console.log('Current user ID:', currentUserId);
    console.log('Is admin:', isAdmin);
    
    // Initialize public chat if on main chat page
    initializePublicChat();
    
    // Initialize private chat if on private chat page
    initializePrivateChat();
    
    // Load messages on public chat page
    if (document.getElementById('messages')) {
        loadPublicMessages();
        if (isAdmin) {
            loadPinnedMessages();
        }
    }
    
    // Set up dark mode toggle
    setupDarkMode();
    
    // Initialize connection status indicator
    updateConnectionStatus();
    
    // Check if socket is already connected (for page refreshes)
    setTimeout(() => {
        if (socket.connected && connectionStatus !== 'connected') {
            console.log('🔄 Socket was already connected, updating status');
            connectionStatus = 'connected';
            updateConnectionStatus();
        }
    }, 1000); // Check after 1 second
});

// Initialize public chat functionality
function initializePublicChat() {
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('msgInput');
    
    if (messageForm && messageInput) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = messageInput.value.trim();
            if (message) {
                console.log('Sending public message:', message);
                
                // Instantly display message for immediate feedback
                const tempMessage = {
                    id: 'temp_' + Date.now(),
                    display_name: 'You',
                    text: message,
                    timestamp: new Date().toISOString(),
                    sender_id: currentUserId,
                    is_private: false,
                    profile_pic: 'default.jpg',
                    temp: true
                };
                
                // Display immediately for instant feedback
                displayPublicMessage(tempMessage);
                addToMessageQueue(tempMessage);
                
                socket.emit('send_message', {
                    text: message
                });
                
                messageInput.value = '';
                
                // Stop typing indicator
                sendTypingIndicator(false, 'public');
            }
        });
        
        // Handle typing indicators
        let typingTimeout;
        messageInput.addEventListener('input', function() {
            // Send typing started
            sendTypingIndicator(true, 'public');
            
            // Clear previous timeout
            clearTimeout(typingTimeout);
            
            // Set timeout to stop typing after 2 seconds of inactivity
            typingTimeout = setTimeout(() => {
                sendTypingIndicator(false, 'public');
            }, 2000);
        });
        
        // Stop typing when input loses focus
        messageInput.addEventListener('blur', function() {
            clearTimeout(typingTimeout);
            sendTypingIndicator(false, 'public');
        });
        
        // Handle Enter key for public messages
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

// Initialize private chat functionality  
function initializePrivateChat() {
    const privateMessageForm = document.getElementById('privateMessageForm');
    const privateMessageInput = document.getElementById('privateMsgInput');
    
    if (privateMessageForm && privateMessageInput) {
        privateMessageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = privateMessageInput.value.trim();
            const recipientId = document.getElementById('recipientId').value;
            
            if (message && recipientId) {
                console.log('Sending private message:', { recipient_id: recipientId, message: message });
                
                socket.emit('private_message', {
                    recipient_id: parseInt(recipientId),
                    message: message
                });
                
                privateMessageInput.value = '';
            }
        });
        
        // Handle Enter key for private messages
        privateMessageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                privateMessageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

// Socket event handlers
socket.on('connect', function() {
    console.log('✅ Connected to server - Real-time mode active');
    connectionStatus = 'connected';
    
    // Ensure DOM is ready before updating status
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateConnectionStatus);
    } else {
        updateConnectionStatus();
    }
    
    // Join user's personal room for notifications
    socket.emit('join_user_room');
    
    // Set user location
    if (window.location.pathname === '/') {
        socket.emit('user_location', { location: 'public_chat' });
    } else if (window.location.pathname.startsWith('/chat/')) {
        socket.emit('user_location', { location: 'private_chat' });
    }
    
    // Start heartbeat for connection monitoring
    startHeartbeat();
    
    // Process any queued messages
    processMessageQueue();
});

socket.on('disconnect', function() {
    console.log('❌ Disconnected from server');
    connectionStatus = 'disconnected';
    updateConnectionStatus();
    stopHeartbeat();
});

socket.on('reconnect', function() {
    console.log('🔄 Reconnected to server');
    connectionStatus = 'connected';
    updateConnectionStatus();
    startHeartbeat();
});

socket.on('connect_error', function(error) {
    console.error('❌ Connection error:', error);
    connectionStatus = 'error';
    updateConnectionStatus();
});

// Handle receiving public messages
socket.on('receive_message', function(data) {
    console.log('📩 Received public message:', data);
    displayPublicMessage(data);
    
    // Play notification sound for real-time feedback
    playNotificationSound();
    
    // Remove from message queue if it exists
    removeFromMessageQueue(data.id);
});

// Handle receiving private messages
socket.on('receive_private_message', function(data) {
    console.log('📩 Received private message:', data);
    displayPrivateMessage(data);
    playNotificationSound();
    removeFromMessageQueue(data.id);
});

// Handle online users updates
socket.on('online_users', function(users) {
    updateOnlineUsers(users);
});

// Handle typing indicators
socket.on('user_typing', function(data) {
    handleTypingIndicator(data);
});

// Handle heartbeat response
socket.on('heartbeat_response', function(data) {
    lastHeartbeat = Date.now();
    updateConnectionQuality();
});

// Handle notifications
socket.on('notification', function(data) {
    console.log('Received notification:', data);
    showNotification(data);
});

// Enhanced message display with real-time features (replacing old function)
function displayPublicMessage(data) {
    const messagesContainer = document.getElementById('messages');
    if (!messagesContainer) return;
    
    // Check if message already exists (avoid duplicates)
    if (document.querySelector(`[data-message-id="${data.id}"]`)) {
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.setAttribute('data-message-id', data.id);
    
    if (data.temp) {
        messageDiv.setAttribute('data-temp-id', data.id);
        messageDiv.classList.add('temp-message');
    }
    
    const isOwnMessage = data.sender_id == currentUserId;
    messageDiv.className = `message ${isOwnMessage ? 'own-message' : 'other-message'}`;
    
    // Handle profile picture
    let avatarHtml = '';
    if (data.profile_pic && data.profile_pic !== 'default.jpg') {
        avatarHtml = `<img src="/static/profile_pics/${data.profile_pic}" alt="Profile" class="message-avatar">`;
    } else {
        const initial = (data.display_name || data.username || '?')[0].toUpperCase();
        avatarHtml = `<div class="message-avatar avatar-fallback">${initial}</div>`;
    }
    
    // Pin button for admins
    let pinButton = '';
    if (isAdmin && !data.is_private && !data.system) {
        pinButton = `<button class="pin-btn" onclick="pinMessage(${data.id})" title="Pin message">📌</button>`;
    }
    
    messageDiv.innerHTML = `
        ${avatarHtml}
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${data.display_name || data.username}</span>
                <span class="message-time">${new Date(data.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
                ${pinButton}
            </div>
            <div class="message-text">${data.text}</div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Add smooth animation for real-time feel
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(10px)';
    requestAnimationFrame(() => {
        messageDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    });
    
    // Add glow effect for new messages
    if (!data.temp) {
        messageDiv.classList.add('new-message');
        setTimeout(() => {
            messageDiv.classList.remove('new-message');
        }, 500);
    }
}

function displayPrivateMessage(data) {
    const messagesContainer = document.getElementById('privateMessages');
    if (!messagesContainer) return;
    
    const messageDiv = document.createElement('div');
    const isOwnMessage = data.sender_id == currentUserId;
    
    messageDiv.className = `message ${isOwnMessage ? 'own-message' : 'other-message'}`;
    
    // Handle profile picture
    let avatarHtml = '';
    if (data.profile_pic && data.profile_pic !== 'default.jpg') {
        avatarHtml = `<img src="/static/profile_pics/${data.profile_pic}" alt="Profile" class="message-avatar">`;
    } else {
        const initial = (data.display_name || data.username)[0].toUpperCase();
        avatarHtml = `<div class="message-avatar avatar-fallback">${initial}</div>`;
    }
    
    messageDiv.innerHTML = `
        ${avatarHtml}
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${data.display_name || data.username}</span>
                <span class="message-time">${new Date(data.timestamp || Date.now()).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
            <div class="message-text">${data.text || data.message}</div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Load public messages
function loadPublicMessages() {
    fetch('/messages')
        .then(response => response.json())
        .then(messages => {
            const messagesContainer = document.getElementById('messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
                messages.forEach(displayPublicMessage);
            }
        })
        .catch(error => console.error('Error loading messages:', error));
}

// Load pinned messages
function loadPinnedMessages() {
    fetch('/pinned_messages')
        .then(response => response.json())
        .then(messages => {
            const pinnedContainer = document.querySelector('#pinnedMessages .pinned-content');
            if (pinnedContainer) {
                pinnedContainer.innerHTML = '';
                messages.forEach(message => {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'pinned-message';
                    messageDiv.innerHTML = `
                        <div class="pinned-message-content">
                            <strong>${message.display_name}</strong>: ${message.text}
                            <button class="unpin-btn" onclick="unpinMessage(${message.id})">🗑️</button>
                        </div>
                    `;
                    pinnedContainer.appendChild(messageDiv);
                });
            }
        })
        .catch(error => console.error('Error loading pinned messages:', error));
}

// Update online users
function updateOnlineUsers(users) {
    const onlineUsersList = document.getElementById('onlineUsersList');
    if (!onlineUsersList) return;
    
    onlineUsersList.innerHTML = '';
    users.forEach(user => {
        const userDiv = document.createElement('div');
        userDiv.className = 'online-user';
        userDiv.innerHTML = `
            <div class="user-avatar">${(user.display_name || 'U')[0].toUpperCase()}</div>
            <span class="user-name">${user.display_name || 'Unknown User'}</span>
        `;
        onlineUsersList.appendChild(userDiv);
    });
}

// Show notification
function showNotification(data) {
    // You can implement browser notifications here
    console.log('Notification:', data);
}

// Pin message function
function pinMessage(messageId) {
    if (!isAdmin) return;
    
    socket.emit('pin_message', { message_id: messageId });
    console.log('Pinning message:', messageId);
}

// Unpin message function
function unpinMessage(messageId) {
    if (!isAdmin) return;
    
    socket.emit('unpin_message', { message_id: messageId });
    console.log('Unpinning message:', messageId);
}

// Setup dark mode toggle
function setupDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (!darkModeToggle) return;
    
    // Load saved theme
    const savedTheme = localStorage.getItem('darkMode');
    if (savedTheme === 'true') {
        document.body.classList.add('dark-mode');
        darkModeToggle.textContent = '☀️';
    }
    
    // Toggle dark mode
    darkModeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        
        localStorage.setItem('darkMode', isDark);
        darkModeToggle.textContent = isDark ? '☀️' : '🌙';
    });
}

// Handle pinned messages updates
socket.on('update_pinned', function() {
    if (isAdmin) {
        loadPinnedMessages();
    }
});

socket.on('update_unpinned', function() {
    if (isAdmin) {
        loadPinnedMessages();
    }
});

// Debug logging
socket.on('disconnect', () => console.log('Socket disconnected'));
socket.on('error', (error) => console.error('Socket error:', error));

// =========================
// REAL-TIME FEATURES
// =========================

// Send typing indicator
function sendTypingIndicator(isTyping, chatType, recipientId = null) {
    if (connectionStatus === 'connected') {
        socket.emit('typing', {
            is_typing: isTyping,
            chat_type: chatType,
            recipient_id: recipientId
        });
    }
}

// Handle typing indicators
function handleTypingIndicator(data) {
    if (data.user_id === currentUserId) return; // Don't show our own typing
    
    const typingContainer = document.getElementById('typingIndicator');
    if (!typingContainer) return;
    
    if (data.is_typing) {
        typingUsers.add(data.display_name || data.username);
    } else {
        typingUsers.delete(data.display_name || data.username);
    }
    
    updateTypingDisplay();
}

// Update typing display
function updateTypingDisplay() {
    const typingContainer = document.getElementById('typingIndicator');
    if (!typingContainer) return;
    
    if (typingUsers.size === 0) {
        typingContainer.innerHTML = '';
        typingContainer.style.display = 'none';
    } else {
        const userList = Array.from(typingUsers);
        let text = '';
        
        if (userList.length === 1) {
            text = `${userList[0]} is typing...`;
        } else if (userList.length === 2) {
            text = `${userList[0]} and ${userList[1]} are typing...`;
        } else {
            text = `${userList[0]} and ${userList.length - 1} others are typing...`;
        }
        
        typingContainer.innerHTML = `<div class="typing-indicator">${text}</div>`;
        typingContainer.style.display = 'block';
    }
}

// Connection status management
function updateConnectionStatus() {
    console.log('🔄 Updating connection status:', connectionStatus);
    
    const statusIndicator = document.getElementById('connectionStatus');
    if (!statusIndicator) {
        // Create status indicator if it doesn't exist
        const indicator = document.createElement('div');
        indicator.id = 'connectionStatus';
        indicator.className = 'connection-status';
        document.body.appendChild(indicator);
        console.log('✅ Created connection status indicator');
    }
    
    const indicator = document.getElementById('connectionStatus');
    indicator.className = `connection-status ${connectionStatus}`;
    
    switch (connectionStatus) {
        case 'connected':
            indicator.innerHTML = '🟢 Real-time';
            indicator.title = 'Connected - Real-time messaging active';
            break;
        case 'connecting':
            indicator.innerHTML = '🟡 Connecting...';
            indicator.title = 'Connecting to server...';
            break;
        case 'disconnected':
            indicator.innerHTML = '🔴 Offline';
            indicator.title = 'Disconnected - Messages will be sent when reconnected';
            break;
        case 'error':
            indicator.innerHTML = '⚠️ Error';
            indicator.title = 'Connection error - Attempting to reconnect...';
            break;
    }
    
    console.log('📊 Connection status updated to:', indicator.innerHTML);
}

// Heartbeat for connection monitoring
function startHeartbeat() {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    
    heartbeatInterval = setInterval(() => {
        if (connectionStatus === 'connected') {
            socket.emit('heartbeat');
        }
    }, 10000); // Every 10 seconds
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

function updateConnectionQuality() {
    const latency = Date.now() - lastHeartbeat;
    const qualityIndicator = document.getElementById('connectionQuality');
    
    if (qualityIndicator) {
        if (latency < 100) {
            qualityIndicator.innerHTML = '🔵 Excellent';
            qualityIndicator.className = 'quality excellent';
        } else if (latency < 300) {
            qualityIndicator.innerHTML = '🟢 Good';
            qualityIndicator.className = 'quality good';
        } else if (latency < 1000) {
            qualityIndicator.innerHTML = '🟡 Fair';
            qualityIndicator.className = 'quality fair';
        } else {
            qualityIndicator.innerHTML = '🔴 Poor';
            qualityIndicator.className = 'quality poor';
        }
    }
}

// Message queue management
function addToMessageQueue(message) {
    messageQueue.push(message);
}

function removeFromMessageQueue(messageId) {
    const tempElement = document.querySelector(`[data-temp-id="${messageId}"]`);
    if (tempElement) {
        tempElement.removeAttribute('data-temp-id');
        tempElement.classList.remove('temp-message');
    }
    messageQueue = messageQueue.filter(msg => msg.id !== messageId);
}

function processMessageQueue() {
    // Process any messages that were queued while disconnected
    messageQueue.forEach(msg => {
        if (msg.temp) {
            // Resend temporary messages
            if (msg.is_private) {
                socket.emit('send_private_message', {
                    text: msg.text,
                    recipient_id: msg.recipient_id
                });
            } else {
                socket.emit('send_message', {
                    text: msg.text
                });
            }
        }
    });
}

// Play notification sound
function playNotificationSound() {
    // Create a subtle notification sound
    const audioContext = window.AudioContext || window.webkitAudioContext;
    if (audioContext) {
        try {
            const context = new audioContext();
            const oscillator = context.createOscillator();
            const gainNode = context.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(context.destination);
            
            oscillator.frequency.setValueAtTime(800, context.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(400, context.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, context.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.1);
            
            oscillator.start(context.currentTime);
            oscillator.stop(context.currentTime + 0.1);
        } catch (e) {
            // Fallback: no sound
            console.log('Audio notification not available');
        }
    }
}