// Initialize Socket.IO
const socket = io();

// Get current user ID from the page context
let currentUserId = null;
let isAdmin = false;

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
                
                socket.emit('send_message', {
                    text: message
                });
                
                messageInput.value = '';
            }
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
    console.log('Connected to server');
    
    // Join user's personal room for notifications
    socket.emit('join_user_room');
    
    // Set user location
    if (window.location.pathname === '/') {
        socket.emit('user_location', { location: 'public_chat' });
    } else if (window.location.pathname.startsWith('/chat/')) {
        socket.emit('user_location', { location: 'private_chat' });
    }
});

// Handle receiving public messages
socket.on('receive_message', function(data) {
    console.log('Received public message:', data);
    displayPublicMessage(data);
});

// Handle receiving private messages
socket.on('receive_private_message', function(data) {
    console.log('Received private message:', data);
    displayPrivateMessage(data);
});

// Handle online users updates
socket.on('online_users', function(users) {
    updateOnlineUsers(users);
});

// Handle notifications
socket.on('notification', function(data) {
    console.log('Received notification:', data);
    showNotification(data);
});

// Display public message function
function displayPublicMessage(data) {
    const messagesContainer = document.getElementById('messages');
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
    
    // Pin button for admins
    let pinButton = '';
    if (isAdmin && !data.is_private) {
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