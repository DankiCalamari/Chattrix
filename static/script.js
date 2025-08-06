const socket = io();

// Set user location and join notification room
socket.on('connect', function() {
    console.log('Connected to server');
    socket.emit('user_location', { location: 'public_chat' });
    socket.emit('join_user_room');
});

// Receive public messages
socket.on('receive_message', function(data) {
    console.log('Received message:', data);
    displayMessage(data);
});

// Handle notifications
socket.on('notification', function(data) {
    showNotification(data);
});

function displayMessage(data) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.setAttribute('data-message-id', data.id);
    
    const avatarLetter = data.display_name ? data.display_name[0].toUpperCase() : 'U';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarLetter}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${data.display_name || data.username}</span>
                <span class="message-time">${new Date(data.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="message-text">${data.text}</div>
        </div>
    `;
    
    // Add pin button for admins
    if (typeof isAdmin !== 'undefined' && isAdmin && data.id) {
        const pinBtn = document.createElement('button');
        pinBtn.className = 'pin-btn';
        pinBtn.innerHTML = '📌';
        pinBtn.title = 'Pin message';
        pinBtn.onclick = function(e) {
            e.stopPropagation();
            socket.emit('pin_message', { message_id: data.id });
            console.log('Pinning message:', data.id);
        };
        messageDiv.appendChild(pinBtn);
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


socket.on('update_pinned', function() {
    console.log('Pinned messages updated');
    const pinnedMessages = document.getElementById('pinnedMessages');
    if (pinnedMessages && pinnedMessages.style.display !== 'none') {
        loadPinnedMessages();
    }
});

socket.on('update_unpinned', function() {
    console.log('Message unpinned, refreshing pinned messages');
    const pinnedMessages = document.getElementById('pinnedMessages');
    if (pinnedMessages && pinnedMessages.style.display !== 'none') {
        loadPinnedMessages();
    }
});

// Handle online users
socket.on('online_users', function(users) {
    const onlineUsersList = document.getElementById('onlineUsersList');
    if (onlineUsersList) {
        onlineUsersList.innerHTML = '';
        
        users.forEach(user => {
            const userDiv = document.createElement('div');
            userDiv.className = 'online-user';
            userDiv.innerHTML = `
                <div class="user-avatar">${user.display_name[0].toUpperCase()}</div>
                <span class="user-name">${user.display_name}</span>
            `;
            onlineUsersList.appendChild(userDiv);
        });
    }
});

function loadPinnedMessages() {
    fetch('/pinned_messages')
        .then(response => response.json())
        .then(messages => {
            const pinnedContent = document.querySelector('.pinned-content');
            if (pinnedContent) {
                pinnedContent.innerHTML = '';
                
                messages.forEach(message => {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'pinned-message';
                    messageDiv.setAttribute('data-message-id', message.id);
                    
                    messageDiv.innerHTML = `
                        <div class="message-content">
                            <div class="message-header">
                                <span class="message-author">${message.display_name}</span>
                                <span class="message-time">${new Date(message.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <div class="message-text">${message.text}</div>
                        </div>
                    `;
                    
                    // Add unpin button for admins
                    if (typeof isAdmin !== 'undefined' && isAdmin && message.id) {
                        const unpinBtn = document.createElement('button');
                        unpinBtn.className = 'unpin-btn';
                        unpinBtn.innerHTML = '📌❌';
                        unpinBtn.title = 'Unpin message';
                        unpinBtn.onclick = function(e) {
                            e.stopPropagation();
                            socket.emit('unpin_message', { message_id: message.id });
                            console.log('Unpinning message:', message.id);
                        };
                        messageDiv.appendChild(unpinBtn);
                    }
                    
                    pinnedContent.appendChild(messageDiv);
                });
            }
        })
        .catch(error => console.error('Error loading pinned messages:', error));
}

// ===========================
// NOTIFICATION SYSTEM
// ===========================

function showNotification(data) {
    console.log('Notification:', data);
    
    // Request permission first time
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Show browser notification if permission granted
    if (Notification.permission === 'granted') {
        const notification = new Notification(data.title, {
            body: data.message,
            icon: '/static/favicon.ico',
            badge: '/static/favicon.ico'
        });
        
        // Click to go to chat
        notification.onclick = function() {
            window.focus();
            window.location.href = data.chat_url;
            notification.close();
        };
        
        // Auto close after 5 seconds
        setTimeout(() => notification.close(), 5000);
    }
    
    // Show in-app notification
    showInAppNotification(data);
}

function showInAppNotification(data) {
    // Get or create notification container
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${data.type}`;
    
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-title">${data.title}</div>
            <div class="notification-message">${data.message}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Click to go to chat (except close button)
    notification.addEventListener('click', function(e) {
        if (!e.target.classList.contains('notification-close')) {
            window.location.href = data.chat_url;
        }
    });
    
    container.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
    
    // Add slide-in animation
    setTimeout(() => notification.classList.add('show'), 100);
}

// ===========================
// DOM CONTENT LOADED - SINGLE EVENT HANDLER
// ===========================

document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(function (permission) {
            if (permission === 'granted') {
                console.log('Notifications enabled');
            } else {
                console.log('Notifications denied');
            }
        });
    }
    
    // Load messages from server
    fetch('/messages')
        .then(response => response.json())
        .then(messages => {
            messages.forEach(message => {
                displayMessage(message);
            });
        })
        .catch(error => console.error('Error loading messages:', error));
    
    // Dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
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
    
    // Message form submission
    const messageForm = document.getElementById('messageForm');
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const messageInput = document.getElementById('msgInput');
            if (messageInput) {
                const message = messageInput.value.trim();
                if (message) {
                    console.log('Sending public message:', message);
                    socket.emit('send_message', { 'text': message });
                    messageInput.value = '';
                }
            }
        });
    }
    
    // Enter key support
    const msgInput = document.getElementById('msgInput');
    if (msgInput) {
        msgInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const form = document.getElementById('messageForm');
                if (form) {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        });
    }
    
    // File upload handling
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('File uploaded successfully');
                    } else {
                        console.error('Upload failed:', data.error);
                    }
                })
                .catch(error => console.error('Upload error:', error));
            }
        });
    }
    
    // Pinned messages toggle
    const togglePinnedBtn = document.getElementById('togglePinnedBtn');
    if (togglePinnedBtn) {
        togglePinnedBtn.addEventListener('click', function() {
            const pinnedMessages = document.getElementById('pinnedMessages');
            if (pinnedMessages) {
                const isVisible = pinnedMessages.style.display !== 'none';
                
                if (isVisible) {
                    pinnedMessages.style.display = 'none';
                    this.textContent = 'Show Pinned Messages';
                } else {
                    pinnedMessages.style.display = 'block';
                    this.textContent = 'Hide Pinned Messages';
                    loadPinnedMessages();
                }
            }
        });
    }
});

// ===========================
// ERROR HANDLING & DEBUG
// ===========================

socket.on('connect', () => console.log('✅ Socket connected'));
socket.on('disconnect', () => console.log('❌ Socket disconnected'));
socket.on('error', (error) => console.error('🚨 Socket error:', error));