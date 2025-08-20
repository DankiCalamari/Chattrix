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

// File upload state
let selectedFile = null;
let selectedPrivateFile = null;

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
    
    // Initialize file upload functionality
    initializeFileUploads();
    
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
            
            // Send text message
            if (message) {
                console.log('Sending public message:', message);
                
                socket.emit('send_message', {
                    text: message
                });
                
                messageInput.value = '';
            }
            
            // Stop typing indicator
            sendTypingIndicator(false, 'public');
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
            
            // Check if there's a file selected
            if (selectedPrivateFile) {
                // Upload file
                uploadFile(selectedPrivateFile, recipientId);
            } else if (message && recipientId) {
                // Send text message
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
});

// Handle receiving private messages
socket.on('receive_private_message', function(data) {
    console.log('📩 Received private message:', data);
    displayPrivateMessage(data);
    playNotificationSound();
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

// Handle browser notifications (fallback)
socket.on('browser_notification', function(data) {
    console.log('Received browser notification:', data);
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
    
    // Handle profile picture with proper fallback
    let avatarHtml = '';
    
    // Check if we have a valid profile picture
    const hasValidProfilePic = data.profile_pic && 
                              data.profile_pic !== 'default.jpg' && 
                              data.profile_pic !== '/static/profile_pics/default.jpg' &&
                              !data.profile_pic.includes('default.jpg');
    
    if (hasValidProfilePic) {
        // Handle both full URLs and just filenames
        const profilePicUrl = data.profile_pic.startsWith('/static/') ? 
                             data.profile_pic : 
                             `/static/profile_pics/${data.profile_pic}`;
        avatarHtml = `<img src="${profilePicUrl}" alt="Profile" class="avatar-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                      <div class="avatar-fallback" style="display: none;">${(data.display_name || data.username || '?')[0].toUpperCase()}</div>`;
    } else {
        // Use first letter fallback
        const initial = (data.display_name || data.username || '?')[0].toUpperCase();
        avatarHtml = `<div class="avatar-fallback">${initial}</div>`;
    }
    
    // Pin button for admins
    let pinButton = '';
    if (isAdmin && !data.is_private && !data.system) {
        pinButton = `<button class="pin-btn" onclick="pinMessage(${data.id})" title="Pin message">📌</button>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            ${avatarHtml}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${data.display_name || data.username}</span>
                <span class="message-time">${new Date(data.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
                ${pinButton}
            </div>
            <div class="message-text">${processFileMessage(data.text)}</div>
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
    
    // Handle profile picture with proper fallback
    let avatarHtml = '';
    
    // Check if we have a valid profile picture
    const hasValidProfilePic = data.profile_pic && 
                              data.profile_pic !== 'default.jpg' && 
                              data.profile_pic !== '/static/profile_pics/default.jpg' &&
                              !data.profile_pic.includes('default.jpg');
    
    if (hasValidProfilePic) {
        // Handle both full URLs and just filenames
        const profilePicUrl = data.profile_pic.startsWith('/static/') ? 
                             data.profile_pic : 
                             `/static/profile_pics/${data.profile_pic}`;
        avatarHtml = `<img src="${profilePicUrl}" alt="Profile" class="avatar-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                      <div class="avatar-fallback" style="display: none;">${(data.display_name || data.username || '?')[0].toUpperCase()}</div>`;
    } else {
        // Use first letter fallback
        const initial = (data.display_name || data.username || '?')[0].toUpperCase();
        avatarHtml = `<div class="avatar-fallback">${initial}</div>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            ${avatarHtml}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${data.display_name || data.username}</span>
                <span class="message-time">${new Date(data.timestamp || Date.now()).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
            <div class="message-text">${processFileMessage(data.text || data.message)}</div>
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
                            <strong>${message.display_name}</strong>: ${processFileMessage(message.text)}
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
        
        // Handle profile picture for online users
        let userAvatarHtml = '';
        const hasValidProfilePic = user.profile_pic && 
                                  user.profile_pic !== 'default.jpg' && 
                                  user.profile_pic !== '/static/profile_pics/default.jpg' &&
                                  !user.profile_pic.includes('default.jpg');
        
        if (hasValidProfilePic) {
            const profilePicUrl = user.profile_pic.startsWith('/static/') ? 
                                 user.profile_pic : 
                                 `/static/profile_pics/${user.profile_pic}`;
            userAvatarHtml = `<img src="${profilePicUrl}" alt="Profile" class="online-user-avatar" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                             <div class="avatar-fallback online-user-avatar" style="display: none;">${(user.display_name || user.username || 'U')[0].toUpperCase()}</div>`;
        } else {
            userAvatarHtml = `<div class="avatar-fallback online-user-avatar">${(user.display_name || user.username || 'U')[0].toUpperCase()}</div>`;
        }
        
        userDiv.innerHTML = `
            ${userAvatarHtml}
            <div class="online-user-info">
                <span class="online-user-name">${user.display_name || user.username || 'Unknown User'}</span>
                <span class="online-status">Online</span>
            </div>
        `;
        onlineUsersList.appendChild(userDiv);
    });
}

// Show notification
function showNotification(data) {
    console.log('📢 Showing notification:', data);
    
    // Try browser notification first (works even without push subscription)
    if ('Notification' in window && Notification.permission === 'granted') {
        try {
            const notification = new Notification(data.title || 'Chattrix', {
                body: data.message || data.body || 'New message',
                icon: '/static/profile_pics/default.jpg',
                badge: '/static/profile_pics/default.jpg',
                tag: 'chattrix-notification',
                requireInteraction: false
            });
            
            notification.onclick = function() {
                window.focus();
                if (data.chat_url) {
                    window.location.href = data.chat_url;
                }
                notification.close();
            };
            
            // Auto close after 5 seconds
            setTimeout(() => notification.close(), 5000);
            
            console.log('✅ Browser notification shown successfully');
            return;
        } catch (error) {
            console.error('❌ Browser notification error:', error);
        }
    }
    
    // Fallback: show toast notification
    showToast(`${data.title || 'New Message'}: ${data.message || data.body}`, 'info');
    
    // Play notification sound
    playNotificationSound();
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
// function setupDarkMode() {
//     const darkModeToggle = document.getElementById('darkModeToggle');
//     if (!darkModeToggle) return;
    
//     // Load saved theme
//     const savedTheme = localStorage.getItem('darkMode');
//     if (savedTheme === 'true') {
//         document.body.classList.add('dark-mode');
//         darkModeToggle.textContent = '☀️';
//     }
    
//     // Toggle dark mode
//     darkModeToggle.addEventListener('click', function() {
//         document.body.classList.toggle('dark-mode');
//         const isDark = document.body.classList.contains('dark-mode');
        
//         localStorage.setItem('darkMode', isDark);
//         darkModeToggle.textContent = isDark ? '☀️' : '🌙';
//     });
// }

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

// Simple file upload functionality (keeping original styling)
function initializeFileUploads() {
    console.log('Initializing file uploads...');
    
    const fileInput = document.getElementById('file-input');
    const fileUploadBtn = document.querySelector('.file-upload-btn');
    
    if (fileInput) {
        // Handle file selection
        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                console.log('File selected:', file.name);
                uploadSingleFile(file);
            }
        });
    }
    
    if (fileUploadBtn) {
        // Handle upload button click
        fileUploadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            fileInput.click();
        });
    }
    
    console.log('File upload system initialized');
}

function uploadSingleFile(file) {
    console.log('Uploading file:', file.name);
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Get message text if any
    const messageInput = document.getElementById('msgInput');
    const messageText = messageInput ? messageInput.value.trim() : '';
    if (messageText) {
        formData.append('message', messageText);
    }
    
    // Show upload indicator
    showUploadStatus('Uploading ' + file.name + '...');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('File uploaded successfully:', data.filename);
            showUploadStatus('✅ File uploaded: ' + file.name, 'success');
            
            // Clear message input after successful upload
            if (messageInput) {
                messageInput.value = '';
            }
        } else {
            console.error('Upload failed:', data.error);
            showUploadStatus('❌ Upload failed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showUploadStatus('❌ Upload failed: ' + error.message, 'error');
    })
    .finally(() => {
        // Reset file input
        fileInput.value = '';
    });
}

function showUploadStatus(message, type = 'info') {
    // Simple status display using alert for now (keeping it simple)
    if (type === 'error') {
        alert('Error: ' + message);
    } else if (type === 'success') {
        alert('Success: ' + message);
    } else {
        console.log('Status:', message);
    }
}

// Simple send message function (keeping original functionality)
function sendMessage() {
    const messageInput = document.getElementById('msgInput');
    const messageText = messageInput ? messageInput.value.trim() : '';
    
    // Send regular text message
    if (messageText) {
        console.log('Sending text message:', messageText);
        
        socket.emit('send_message', {
            text: messageText
        });
        
        messageInput.value = '';
    }
}

// Make sure file uploads are initialized when page loads  
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing simple file uploads...');
    initializeFileUploads();
});

// Test function for debugging
function testFileUpload() {
    console.log('Test function called - simple upload system');
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.click();
    } else {
        console.error('File input not found!');
    }
}

// Handle public file selection (Discord-style preview)
function handleFileSelection(event) {
    console.log('File selection triggered:', event.target.files);
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('File selected:', file.name, file.type);
    selectedFile = file;
    showFilePreview(file, 'public');
}

// Handle private file selection (Discord-style preview)
function handlePrivateFileSelection(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    selectedPrivateFile = file;
    showFilePreview(file, 'private');
}

// Show file preview in the input area (Discord-style)  
function showFilePreview(file, chatType) {
    const isImage = file.type.startsWith('image/');
    const messageForm = chatType === 'public' ? 
        document.getElementById('messageForm') : 
        document.getElementById('privateMessageForm');
    
    if (!messageForm) return;
    
    // Remove existing preview
    const existingPreview = messageForm.querySelector('.file-preview');
    if (existingPreview) {
        existingPreview.remove();
    }
    
    // Create preview container
    const previewContainer = document.createElement('div');
    previewContainer.className = 'file-preview';
    
    if (isImage) {
        // Create image preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewContainer.innerHTML = `
                <div class="file-preview-content">
                    <div class="file-preview-image-container">
                        <img src="${e.target.result}" class="file-preview-image" alt="${file.name}">
                    </div>
                    <div class="file-preview-info">
                        <span class="file-preview-name">${file.name}</span>
                        <span class="file-preview-size">${formatFileSize(file.size)}</span>
                    </div>
                    <button type="button" class="file-preview-remove" onclick="removeFilePreview('${chatType}')">×</button>
                </div>
            `;
        };
        reader.readAsDataURL(file);
    } else {
        // Create file preview for non-images
        const fileIcon = getFileIcon(file.name.split('.').pop().toLowerCase());
        previewContainer.innerHTML = `
            <div class="file-preview-content">
                <div class="file-preview-file">
                    <span class="file-preview-icon">${fileIcon}</span>
                    <div class="file-preview-info">
                        <span class="file-preview-name">${file.name}</span>
                        <span class="file-preview-size">${formatFileSize(file.size)}</span>
                    </div>
                </div>
                <button type="button" class="file-preview-remove" onclick="removeFilePreview('${chatType}')">×</button>
            </div>
        `;
    }
    
    // Insert preview before the input row
    const inputRow = messageForm.querySelector('.message-input') || messageForm.querySelector('input[type="text"]');
    if (inputRow) {
        messageForm.insertBefore(previewContainer, inputRow);
    }
}

// Remove file preview
function removeFilePreview(chatType) {
    if (chatType === 'public') {
        selectedFile = null;
        document.getElementById('file-input').value = '';
        const preview = document.querySelector('#messageForm .file-preview');
        if (preview) preview.remove();
    } else {
        selectedPrivateFile = null;
        document.getElementById('private-file-input').value = '';
        const preview = document.querySelector('#privateMessageForm .file-preview');
        if (preview) preview.remove();
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Unified file upload function
function uploadFile(file, recipientId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (recipientId) {
        formData.append('recipient_id', recipientId);
    }
    
    // Show upload indicator
    showUploadProgress('Uploading file...');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideUploadProgress();
        if (data.success) {
            console.log('File uploaded successfully:', data.filename);
            
            // Clear the file selection and preview
            if (recipientId) {
                // Private chat
                removeFilePreview('private');
            } else {
                // Public chat
                removeFilePreview('public');
            }
        } else {
            showErrorMessage('Upload failed: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        hideUploadProgress();
        console.error('Upload error:', error);
        showErrorMessage('Upload failed: ' + error.message);
    });
}

// Show upload progress indicator
function showUploadProgress(message) {
    // Create or update upload indicator
    let indicator = document.getElementById('upload-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'upload-indicator';
        indicator.className = 'upload-indicator';
        indicator.innerHTML = `
            <div class="upload-content">
                <div class="upload-spinner"></div>
                <span class="upload-text">${message}</span>
            </div>
        `;
        document.body.appendChild(indicator);
    } else {
        indicator.querySelector('.upload-text').textContent = message;
    }
    indicator.style.display = 'flex';
}

// Hide upload progress indicator
function hideUploadProgress() {
    const indicator = document.getElementById('upload-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// Show error message
function showErrorMessage(message) {
    // Create or update error message
    let errorDiv = document.getElementById('error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'error-message';
        errorDiv.className = 'error-message';
        document.body.appendChild(errorDiv);
    }
    
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Process file messages for display
function processFileMessage(text) {
    // Check if this is a file message with format [FILE:filename:original_filename]
    const fileMatch = text.match(/^\[FILE:([^:]+):(.+)\]$/);
    if (fileMatch) {
        const [, filename, originalFilename] = fileMatch;
        const fileExtension = originalFilename.toLowerCase().split('.').pop();
        
        // Determine if it's an image
        const imageExtensions = ['png', 'jpg', 'jpeg', 'gif'];
        const isImage = imageExtensions.includes(fileExtension);
        
        if (isImage) {
            return `
                <div class="file-message image-message">
                    <img src="/static/uploads/${filename}" alt="${originalFilename}" class="uploaded-image" 
                         onclick="openImageModal(this.src, '${originalFilename}')">
                    <div class="file-info">
                        <span class="file-icon">🖼️</span>
                        <span class="file-name">${originalFilename}</span>
                    </div>
                </div>
            `;
        } else {
            // Non-image file
            const fileIcon = getFileIcon(fileExtension);
            return `
                <div class="file-message">
                    <a href="/static/uploads/${filename}" target="_blank" download="${originalFilename}" class="file-link">
                        <span class="file-icon">${fileIcon}</span>
                        <span class="file-name">${originalFilename}</span>
                        <span class="file-action">📥 Download</span>
                    </a>
                </div>
            `;
        }
    }
    
    return text; // Return original text if not a file message
}

// Get appropriate icon for file type
function getFileIcon(extension) {
    const iconMap = {
        'pdf': '📄',
        'txt': '📝',
        'docx': '📄',
        'doc': '📄',
        'mp4': '🎥',
        'avi': '🎥',
        'mov': '🎥',
        'zip': '📦',
        'rar': '📦'
    };
    
    return iconMap[extension] || '📎';
}

// Open image in modal
function openImageModal(src, filename) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('image-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'image-modal';
        modal.className = 'image-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close">&times;</span>
                <img class="modal-image" src="" alt="">
                <div class="modal-caption"></div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close modal on click
        modal.querySelector('.modal-close').onclick = () => modal.style.display = 'none';
        modal.onclick = (e) => {
            if (e.target === modal) modal.style.display = 'none';
        };
    }
    
    // Set image and show modal
    modal.querySelector('.modal-image').src = src;
    modal.querySelector('.modal-caption').textContent = filename;
    modal.style.display = 'block';
}

// Test function to verify JavaScript is working
function testFileUpload() {
    alert('JavaScript is working! File upload functions are loaded.');
    console.log('Testing file upload functionality...');
    
    // Test if file input exists
    const fileInput = document.getElementById('file-input');
    console.log('File input found:', fileInput);
    
    // Test if form exists
    const messageForm = document.getElementById('messageForm');
    console.log('Message form found:', messageForm);
    
    // Create a fake file object for testing
    const fakeFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    console.log('Created fake file:', fakeFile);
    
    // Test the preview function
    try {
        showFilePreview(fakeFile, 'public');
        console.log('Preview function executed successfully');
    } catch (error) {
        console.error('Error in preview function:', error);
    }
}

// =========================
// PUSH NOTIFICATIONS
// =========================

let serviceWorkerRegistration = null;
let pushSubscription = null;

// Initialize push notifications when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializePushNotifications();
    setupTestPushButton();
    setupFallbackNotifications();
});

// Initialize push notification service
async function initializePushNotifications() {
    console.log('🔧 Starting push notification initialization...');
    
    // Check if we're on HTTP (not HTTPS)
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        console.warn('⚠️ Push notifications require HTTPS in production');
        showToast('Push notifications require HTTPS to work properly', 'warning');
        return;
    }
    
    if (!('serviceWorker' in navigator)) {
        console.warn('⚠️ Service Workers not supported in this browser');
        showToast('Your browser does not support push notifications', 'warning');
        return;
    }
    
    if (!('PushManager' in window)) {
        console.warn('⚠️ Push messaging not supported in this browser');
        showToast('Your browser does not support push messaging', 'warning');
        return;
    }

    try {
        console.log('🔧 Registering service worker...');
        
        // Register service worker
        serviceWorkerRegistration = await navigator.serviceWorker.register('/static/sw.js', {
            scope: '/'
        });
        
        console.log('✅ Service Worker registered:', serviceWorkerRegistration);
        
        // Wait for service worker to be ready
        await navigator.serviceWorker.ready;
        console.log('✅ Service Worker ready');
        
        // Request notification permission
        const permissionGranted = await requestNotificationPermission();
        if (!permissionGranted) {
            console.warn('⚠️ Notification permission not granted, skipping subscription');
            return;
        }
        
        // Subscribe to push notifications
        await subscribeToPushNotifications();
        
    } catch (error) {
        console.error('❌ Error initializing push notifications:', error);
        
        if (error.message.includes('Only secure origins are allowed')) {
            showToast('Push notifications require HTTPS. They may not work on HTTP.', 'warning');
        } else {
            showToast('Failed to initialize push notifications: ' + error.message, 'error');
        }
    }
}

// Request notification permission from user
async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.warn('⚠️ This browser does not support notifications');
        return false;
    }

    let permission = Notification.permission;
    
    if (permission === 'default') {
        console.log('🔔 Requesting notification permission...');
        permission = await Notification.requestPermission();
    }
    
    if (permission === 'granted') {
        console.log('✅ Notification permission granted');
        return true;
    } else {
        console.warn('⚠️ Notification permission denied');
        return false;
    }
}

// Subscribe to push notifications
async function subscribeToPushNotifications() {
    if (!serviceWorkerRegistration) {
        console.error('❌ Service worker not registered');
        return;
    }

    try {
        console.log('🔑 Getting VAPID public key from server...');
        
        // Get VAPID public key from server
        const response = await fetch('/vapid-public-key');
        if (!response.ok) {
            throw new Error(`Failed to get VAPID key: ${response.status}`);
        }
        
        const vapidData = await response.json();
        const publicKey = vapidData.publicKey;
        
        console.log('🔑 VAPID public key received:', publicKey);
        
        // Check if already subscribed
        pushSubscription = await serviceWorkerRegistration.pushManager.getSubscription();
        
        if (pushSubscription) {
            console.log('✅ Already subscribed to push notifications');
            console.log('Existing subscription:', pushSubscription);
            await sendSubscriptionToServer(pushSubscription);
            return;
        }
        
        // Subscribe to push notifications
        console.log('📤 Creating new push subscription...');
        
        const applicationServerKey = urlBase64ToUint8Array(publicKey);
        console.log('🔑 Converted VAPID key to Uint8Array:', applicationServerKey);
        
        pushSubscription = await serviceWorkerRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey
        });
        
        console.log('✅ Push subscription created:', pushSubscription);
        console.log('📤 Subscription endpoint:', pushSubscription.endpoint);
        
        // Send subscription to server
        await sendSubscriptionToServer(pushSubscription);
        
    } catch (error) {
        console.error('❌ Error subscribing to push notifications:', error);
        
        // Show more specific error messages
        if (error.name === 'NotSupportedError') {
            showToast('Push notifications are not supported in this browser', 'error');
        } else if (error.name === 'NotAllowedError') {
            showToast('Push notifications were blocked. Please enable them in browser settings.', 'error');
        } else {
            showToast('Failed to setup push notifications: ' + error.message, 'error');
        }
    }
}

// Send push subscription to server
async function sendSubscriptionToServer(subscription) {
    try {
        console.log('📤 Sending subscription to server...');
        console.log('📤 Subscription object:', subscription.toJSON());
        
        const response = await fetch('/subscribe-push', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subscription: subscription.toJSON()
            })
        });
        
        const responseText = await response.text();
        console.log('📤 Server response:', response.status, responseText);
        
        if (response.ok) {
            console.log('✅ Push subscription sent to server successfully');
            showToast('Push notifications enabled successfully!', 'success');
        } else {
            console.error('❌ Failed to send subscription to server:', response.status, responseText);
            showToast('Failed to register for push notifications on server', 'error');
        }
        
    } catch (error) {
        console.error('❌ Error sending subscription to server:', error);
        showToast('Error communicating with server for push notifications', 'error');
    }
}

// Convert VAPID public key from base64 to Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Setup test push button functionality
function setupTestPushButton() {
    const testPushBtn = document.getElementById('testPushBtn');
    if (testPushBtn) {
        testPushBtn.addEventListener('click', async function() {
            if (!currentUserId) {
                alert('Error: User ID not found');
                return;
            }
            
            console.log('🧪 Testing push notification for user:', currentUserId);
            
            try {
                const response = await fetch(`/test-push/${currentUserId}`, {
                    method: 'GET'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    console.log('✅ Test notification sent successfully');
                    
                    // Show a confirmation message
                    showToast('Test push notification sent! Check your device for the notification.', 'success');
                } else {
                    console.error('❌ Failed to send test notification:', result.message);
                    showToast('Failed to send test notification: ' + result.message, 'error');
                }
                
            } catch (error) {
                console.error('❌ Error testing push notification:', error);
                showToast('Error testing push notification', 'error');
            }
        });
    }
    
    // Setup push status button
    const pushStatusBtn = document.getElementById('pushStatusBtn');
    if (pushStatusBtn) {
        pushStatusBtn.addEventListener('click', function() {
            window.checkPushStatus();
            
            // Show status in UI
            const hasSubscription = !!pushSubscription;
            const permission = Notification.permission;
            const isSecure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
            
            let statusMessage = `Push Status:\n`;
            statusMessage += `• Permission: ${permission}\n`;
            statusMessage += `• Subscription: ${hasSubscription ? 'Active' : 'None'}\n`;
            statusMessage += `• Secure Context: ${isSecure ? 'Yes' : 'No'}\n`;
            statusMessage += `• Service Worker: ${serviceWorkerRegistration ? 'Registered' : 'Not Registered'}`;
            
            if (!isSecure && location.protocol === 'http:') {
                statusMessage += '\n\n⚠️ Push notifications may not work on HTTP.\nTry Chrome with --unsafely-treat-insecure-origin-as-secure flag.';
            }
            
            alert(statusMessage);
        });
    }
    
    // Setup browser notification test button
    const testBrowserBtn = document.getElementById('testBrowserBtn');
    if (testBrowserBtn) {
        testBrowserBtn.addEventListener('click', function() {
            window.testBrowserNotification();
        });
    }
}

// Show toast notification (for feedback)
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        z-index: 10000;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        max-width: 300px;
        word-wrap: break-word;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// Test push notifications (callable from console)
window.testPushNotifications = async function() {
    console.log('🧪 Testing push notification system...');
    
    if (!currentUserId) {
        console.error('❌ Current user ID not found');
        return;
    }
    
    // Test service worker registration
    if (!serviceWorkerRegistration) {
        console.error('❌ Service worker not registered');
        await initializePushNotifications();
        return;
    }
    
    // Test subscription
    if (!pushSubscription) {
        console.error('❌ Push subscription not found');
        await subscribeToPushNotifications();
        return;
    }
    
    console.log('✅ Push notification system appears to be working');
    console.log('Service Worker:', serviceWorkerRegistration);
    console.log('Push Subscription:', pushSubscription);
    
    // Test notification
    try {
        const response = await fetch(`/test-push/${currentUserId}`);
        const result = await response.json();
        console.log('Test result:', result);
    } catch (error) {
        console.error('Test error:', error);
    }
};

// Function to check push notification status
window.checkPushStatus = function() {
    console.log('📊 Push Notification Status:');
    console.log('- Service Worker Registration:', serviceWorkerRegistration);
    console.log('- Push Subscription:', pushSubscription);
    console.log('- Current User ID:', currentUserId);
    console.log('- Notification Permission:', Notification.permission);
    console.log('- Protocol:', location.protocol);
    console.log('- Hostname:', location.hostname);
    console.log('- Browser Support:', {
        serviceWorker: 'serviceWorker' in navigator,
        pushManager: 'PushManager' in window,
        notifications: 'Notification' in window
    });
    
    // Show Chrome localhost instructions
    if (location.protocol === 'http:' && (location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
        console.log('💡 For Chrome localhost testing, try:');
        console.log('1. Chrome flags: chrome://flags/#unsafely-treat-insecure-origin-as-secure');
        console.log('2. Add: http://localhost:5000');
        console.log('3. Or use: chrome --unsafely-treat-insecure-origin-as-secure=http://localhost:5000 --user-data-dir=/tmp/foo');
    }
};

// Setup fallback browser notifications (works on localhost without HTTPS)
function setupFallbackNotifications() {
    console.log('🔧 Setting up fallback notifications...');
    
    // Request notification permission for browser notifications
    if ('Notification' in window) {
        if (Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('📋 Notification permission:', permission);
                if (permission === 'granted') {
                    console.log('✅ Browser notifications enabled (fallback)');
                    showToast('Browser notifications enabled!', 'success');
                    
                    // Register for fallback notifications on server
                    registerFallbackNotifications();
                }
            });
        } else if (Notification.permission === 'granted') {
            console.log('✅ Browser notifications already enabled');
            registerFallbackNotifications();
        }
    }
}

// Register for fallback notifications (server-side tracking)
async function registerFallbackNotifications() {
    if (!currentUserId) return;
    
    try {
        const response = await fetch('/register-fallback-notifications', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: currentUserId,
                browser_notifications: true
            })
        });
        
        if (response.ok) {
            console.log('✅ Registered for fallback notifications');
        }
    } catch (error) {
        console.error('❌ Error registering fallback notifications:', error);
    }
}

// Test browser notification (works without push subscription)
window.testBrowserNotification = function() {
    if ('Notification' in window && Notification.permission === 'granted') {
        const notification = new Notification('Test Notification', {
            body: 'This is a test browser notification from Chattrix!',
            icon: '/static/profile_pics/default.jpg',
            tag: 'test-notification'
        });
        
        notification.onclick = function() {
            window.focus();
            notification.close();
        };
        
        setTimeout(() => notification.close(), 5000);
        console.log('✅ Test browser notification sent');
    } else {
        console.error('❌ Browser notifications not available');
        alert('Browser notifications not available. Permission: ' + (Notification ? Notification.permission : 'Not supported'));
    }
};