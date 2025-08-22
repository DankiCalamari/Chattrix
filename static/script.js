/**
 * Chattrix Real-Time Messaging Client
 * Initializes Socket.IO with optimized settings for real-time performance
 */
const objSocket = io({
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

/**
 * Global State Management Variables
 * Using Hungarian notation for type clarity
 */
let strConnectionStatus = 'connecting';           // Connection state indicator
let setTypingUsers = new Set();                  // Active typing users collection
let nTypingTimer = null;                         // Typing indicator timer reference
let nHeartbeatInterval = null;                   // Heartbeat interval reference
let arrMessageQueue = [];                        // Queued messages for offline handling
let nLastHeartbeat = Date.now();                 // Timestamp of last heartbeat

/**
 * User Context Variables
 * Current user identification and permissions
 */
let nCurrentUserId = null;                       // Current authenticated user ID
let bIsAdmin = false;                            // Admin privileges flag

/**
 * File Upload State Variables
 * File selection state for public and private uploads
 */
let objSelectedFile = null;                      // Selected file for public upload
let objSelectedPrivateFile = null;               // Selected file for private upload

/**
 * Initial Connection Status Display
 * Shows connection status immediately when DOM loads
 */
document.addEventListener('DOMContentLoaded', function() {
    updateConnectionStatus();
});

/**
 * Main Application Initialization
 * Initializes all components when DOM is fully loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Extract current user ID from DOM data attributes or global variables
    const elemUserIdContainer = document.querySelector('[data-user-id]');
    if (elemUserIdContainer) {
        nCurrentUserId = parseInt(elemUserIdContainer.getAttribute('data-user-id'));
    } else if (window.currentUserId) {
        nCurrentUserId = window.currentUserId;
    }
    
    // Extract admin status from global scope
    if (window.isAdmin) {
        bIsAdmin = window.isAdmin;
    }
    
    console.log('Current user ID:', nCurrentUserId);
    console.log('Is admin:', bIsAdmin);
    
    // Initialize chat components based on current page context
    initializePublicChat();
    initializePrivateChat();
    
    // Load messages for public chat interface
    const elemMessages = document.getElementById('messages');
    if (elemMessages) {
        loadPublicMessages();
        if (bIsAdmin) {
            loadPinnedMessages();
        }
    }
    
    // Initialize UI components
    setupDarkMode();
    updateConnectionStatus();
    initializeFileUploads();
    
    // Handle post-load socket connection verification
    setTimeout(() => {
        if (objSocket.connected && strConnectionStatus !== 'connected') {
            console.log('🔄 Socket was already connected, updating status');
            strConnectionStatus = 'connected';
            updateConnectionStatus();
        }
    }, 1000);
});

/**
 * Initialize Public Chat Functionality
 * Sets up event handlers for public message sending and typing indicators
 */
function initializePublicChat() {
    const elemMessageForm = document.getElementById('messageForm');
    const elemMessageInput = document.getElementById('msgInput');
    
    if (elemMessageForm && elemMessageInput) {
        // Handle form submission for sending messages
        elemMessageForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const strMessage = elemMessageInput.value.trim();
            
            // Send text message if content exists
            if (strMessage) {
                console.log('Sending public message:', strMessage);
                
                objSocket.emit('send_message', {
                    text: strMessage
                });
                
                elemMessageInput.value = '';
            }
            
            // Clear typing indicator
            sendTypingIndicator(false, 'public');
        });
        
        // Handle typing indicators with debouncing
        let nTypingTimeout;
        elemMessageInput.addEventListener('input', function() {
            // Signal typing started
            sendTypingIndicator(true, 'public');
            
            // Clear previous timeout to prevent multiple signals
            clearTimeout(nTypingTimeout);
            
            // Auto-stop typing indicator after 2 seconds of inactivity
            nTypingTimeout = setTimeout(() => {
                sendTypingIndicator(false, 'public');
            }, 2000);
        });
        
        // Clear typing indicator when input loses focus
        elemMessageInput.addEventListener('blur', function() {
            clearTimeout(nTypingTimeout);
            sendTypingIndicator(false, 'public');
        });
        
        // Handle Enter key submission for public messages
        elemMessageInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                elemMessageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

/**
 * Initialize Private Chat Functionality
 * Sets up event handlers for private message sending and file uploads
 */
function initializePrivateChat() {
    const elemPrivateMessageForm = document.getElementById('privateMessageForm');
    const elemPrivateMessageInput = document.getElementById('privateMsgInput');
    
    if (elemPrivateMessageForm && elemPrivateMessageInput) {
        // Handle form submission for private messages
        elemPrivateMessageForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const strMessage = elemPrivateMessageInput.value.trim();
            const strRecipientId = document.getElementById('recipientId').value;
            
            // Handle file upload if file is selected
            if (objSelectedPrivateFile) {
                uploadFile(objSelectedPrivateFile, strRecipientId);
            } else if (strMessage && strRecipientId) {
                // Send text message
                console.log('Sending private message:', { 
                    recipient_id: strRecipientId, 
                    message: strMessage 
                });
                
                objSocket.emit('private_message', {
                    recipient_id: parseInt(strRecipientId),
                    message: strMessage
                });
                
                elemPrivateMessageInput.value = '';
            }
        });
        
        // Handle Enter key submission for private messages
        elemPrivateMessageInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                elemPrivateMessageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

/**
 * Socket Event Handlers
 * Real-time communication event management
 */

/**
 * Handle Socket Connection Event
 * Establishes connection and initializes user presence
 */
objSocket.on('connect', function() {
    console.log('✅ Connected to server - Real-time mode active');
    strConnectionStatus = 'connected';
    
    // Ensure DOM is ready before updating connection status
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateConnectionStatus);
    } else {
        updateConnectionStatus();
    }
    
    // Join user's personal notification room
    objSocket.emit('join_user_room');
    
    // Set user location context for targeted notifications
    const strCurrentPath = window.location.pathname;
    if (strCurrentPath === '/') {
        objSocket.emit('user_location', { location: 'public_chat' });
    } else if (strCurrentPath.startsWith('/chat/')) {
        objSocket.emit('user_location', { location: 'private_chat' });
    }
    
    // Start heartbeat monitoring for connection health
    startHeartbeat();
    
    // Process any queued messages from offline state
    processMessageQueue();
});

/**
 * Handle Socket Disconnection Event
 * Updates UI and stops heartbeat monitoring
 */
objSocket.on('disconnect', function() {
    console.log('❌ Disconnected from server');
    strConnectionStatus = 'disconnected';
    updateConnectionStatus();
    stopHeartbeat();
});

/**
 * Handle Socket Reconnection Event
 * Re-establishes connection state and monitoring
 */
objSocket.on('reconnect', function() {
    console.log('🔄 Reconnected to server');
    strConnectionStatus = 'connected';
    updateConnectionStatus();
    startHeartbeat();
});

/**
 * Handle Socket Connection Error Event
 * Displays error state in UI
 */
objSocket.on('connect_error', function(objError) {
    console.error('❌ Connection error:', objError);
    strConnectionStatus = 'error';
    updateConnectionStatus();
});

/**
 * Handle Incoming Public Messages
 * Displays public chat messages with audio notification
 */
objSocket.on('receive_message', function(objData) {
    console.log('📩 Received public message:', objData);
    displayPublicMessage(objData);
    
    // Provide audio feedback for real-time interaction
    playNotificationSound();
});

/**
 * Handle Incoming Private Messages
 * Displays private chat messages with audio notification
 */
objSocket.on('receive_private_message', function(objData) {
    console.log('📩 Received private message:', objData);
    displayPrivateMessage(objData);
    playNotificationSound();
});

/**
 * Handle Online Users Updates
 * Updates the online users list display
 */
objSocket.on('online_users', function(arrUsers) {
    updateOnlineUsers(arrUsers);
});

/**
 * Handle Typing Indicators
 * Shows/hides typing status for other users
 */
objSocket.on('user_typing', function(objData) {
    handleTypingIndicator(objData);
});

/**
 * Handle Heartbeat Response
 * Updates connection quality metrics
 */
objSocket.on('heartbeat_response', function(objData) {
    nLastHeartbeat = Date.now();
    updateConnectionQuality();
});

/**
 * Handle Notification Events
 * Displays browser notifications for messages and alerts
 */
objSocket.on('notification', function(objData) {
    console.log('Received notification:', objData);
    showNotification(objData);
});

/**
 * Handle Browser Notification Fallback
 * Alternative notification method for compatibility
 */
objSocket.on('browser_notification', function(objData) {
    console.log('Received browser notification:', objData);
    showNotification(objData);
});

/**
 * Display Public Message Function
 * Enhanced message display with real-time features and duplicate prevention
 * @param {Object} objData - Message data object containing all message information
 */
function displayPublicMessage(objData) {
    const elemMessagesContainer = document.getElementById('messages');
    if (!elemMessagesContainer) return;
    
    // Prevent duplicate message display by checking existing message IDs
    if (document.querySelector(`[data-message-id="${objData.id}"]`)) {
        return;
    }
    
    const elemMessageDiv = document.createElement('div');
    elemMessageDiv.setAttribute('data-message-id', objData.id);
    
    // Handle temporary messages (for optimistic UI updates)
    if (objData.temp) {
        elemMessageDiv.setAttribute('data-temp-id', objData.id);
        elemMessageDiv.classList.add('temp-message');
    }
    
    const bIsOwnMessage = objData.sender_id == nCurrentUserId;
    elemMessageDiv.className = `message ${bIsOwnMessage ? 'own-message' : 'other-message'}`;
    
    // Handle profile picture with intelligent fallback system
    let strAvatarHtml = '';
    
    // Validate profile picture availability and authenticity
    const bHasValidProfilePic = objData.profile_pic && 
                               objData.profile_pic !== 'default.jpg' && 
                               objData.profile_pic !== '/static/profile_pics/default.jpg' &&
                               !objData.profile_pic.includes('default.jpg');
    
    if (bHasValidProfilePic) {
        // Normalize profile picture URL format
        const strProfilePicUrl = objData.profile_pic.startsWith('/static/') ? 
                                objData.profile_pic : 
                                `/static/profile_pics/${objData.profile_pic}`;
        strAvatarHtml = `<img src="${strProfilePicUrl}" alt="Profile" class="avatar-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="avatar-fallback" style="display: none;">${(objData.display_name || objData.username || '?')[0].toUpperCase()}</div>`;
    } else {
        // Generate initial-based avatar fallback
        const strInitial = (objData.display_name || objData.username || '?')[0].toUpperCase();
        strAvatarHtml = `<div class="avatar-fallback">${strInitial}</div>`;
    }
    
    // Generate admin pin button for message management
    let strPinButton = '';
    if (bIsAdmin && !objData.is_private && !objData.system) {
        strPinButton = `<button class="pin-btn" onclick="pinMessage(${objData.id})" title="Pin message">📌</button>`;
    }
    
    // Construct complete message HTML structure
    elemMessageDiv.innerHTML = `
        <div class="message-avatar">
            ${strAvatarHtml}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${objData.display_name || objData.username}</span>
                <span class="message-time">${new Date(objData.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
                ${strPinButton}
            </div>
            <div class="message-text">${processFileMessage(objData.text)}</div>
        </div>
    `;
    
    // Append message to container and auto-scroll to latest
    elemMessagesContainer.appendChild(elemMessageDiv);
    elemMessagesContainer.scrollTop = elemMessagesContainer.scrollHeight;
    
    // Add smooth entrance animation for enhanced user experience
    elemMessageDiv.style.opacity = '0';
    elemMessageDiv.style.transform = 'translateY(10px)';
    requestAnimationFrame(() => {
        elemMessageDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        elemMessageDiv.style.opacity = '1';
        elemMessageDiv.style.transform = 'translateY(0)';
    });
    
    // Add visual highlight for new messages
    if (!objData.temp) {
        elemMessageDiv.classList.add('new-message');
        setTimeout(() => {
            elemMessageDiv.classList.remove('new-message');
        }, 500);
    }
}

/**
 * Display Private Message Function
 * Renders private chat messages with avatar fallback system
 * @param {Object} objData - Private message data object
 */
function displayPrivateMessage(objData) {
    const elemMessagesContainer = document.getElementById('privateMessages');
    if (!elemMessagesContainer) return;
    
    const elemMessageDiv = document.createElement('div');
    const bIsOwnMessage = objData.sender_id == nCurrentUserId;
    
    elemMessageDiv.className = `message ${bIsOwnMessage ? 'own-message' : 'other-message'}`;
    
    // Handle profile picture with intelligent fallback system
    let strAvatarHtml = '';
    
    // Validate profile picture availability and authenticity
    const bHasValidProfilePic = objData.profile_pic && 
                               objData.profile_pic !== 'default.jpg' && 
                               objData.profile_pic !== '/static/profile_pics/default.jpg' &&
                               !objData.profile_pic.includes('default.jpg');
    
    if (bHasValidProfilePic) {
        // Normalize profile picture URL format
        const strProfilePicUrl = objData.profile_pic.startsWith('/static/') ? 
                                objData.profile_pic : 
                                `/static/profile_pics/${objData.profile_pic}`;
        strAvatarHtml = `<img src="${strProfilePicUrl}" alt="Profile" class="avatar-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="avatar-fallback" style="display: none;">${(objData.display_name || objData.username || '?')[0].toUpperCase()}</div>`;
    } else {
        // Generate initial-based avatar fallback
        const strInitial = (objData.display_name || objData.username || '?')[0].toUpperCase();
        strAvatarHtml = `<div class="avatar-fallback">${strInitial}</div>`;
    }
    
    // Construct private message HTML structure
    elemMessageDiv.innerHTML = `
        <div class="message-avatar">
            ${strAvatarHtml}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${objData.display_name || objData.username}</span>
                <span class="message-time">${new Date(objData.timestamp || Date.now()).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
            <div class="message-text">${processFileMessage(objData.text || objData.message)}</div>
        </div>
    `;
    
    // Append to container and auto-scroll to latest message
    elemMessagesContainer.appendChild(elemMessageDiv);
    elemMessagesContainer.scrollTop = elemMessagesContainer.scrollHeight;
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

/**
 * Show Notification Function
 * Displays browser notifications with fallback to toast notifications
 * @param {Object} objData - Notification data containing title, message, and action URLs
 */
function showNotification(objData) {
    console.log('📢 Showing notification:', objData);
    
    // Attempt browser notification first (requires permission and works without push subscription)
    if ('Notification' in window && Notification.permission === 'granted') {
        try {
            const objNotification = new Notification(objData.title || 'Chattrix', {
                body: objData.message || objData.body || 'New message',
                icon: '/static/profile_pics/default.jpg',
                badge: '/static/profile_pics/default.jpg',
                tag: 'chattrix-notification',
                requireInteraction: false
            });
            
            // Handle notification click event for navigation
            objNotification.onclick = function() {
                window.focus();
                if (objData.chat_url) {
                    window.location.href = objData.chat_url;
                }
                objNotification.close();
            };
            
            // Auto-close notification after 5 seconds to prevent clutter
            setTimeout(() => objNotification.close(), 5000);
            
            console.log('✅ Browser notification shown successfully');
            return;
        } catch (objError) {
            console.error('❌ Browser notification error:', objError);
        }
    }
    
    // Fallback: display toast notification for users without browser notification permission
    showToast(`${objData.title || 'New Message'}: ${objData.message || objData.body}`, 'info');
    
    // Play audio notification for all notification types
    playNotificationSound();
}

/**
 * Pin Message Function
 * Allows admin users to pin important messages
 * @param {number} nMessageId - ID of message to pin
 */
function pinMessage(nMessageId) {
    if (!bIsAdmin) return;
    
    objSocket.emit('pin_message', { message_id: nMessageId });
    console.log('Pinning message:', nMessageId);
}

/**
 * Unpin Message Function  
 * Allows admin users to unpin previously pinned messages
 * @param {number} nMessageId - ID of message to unpin
 */
function unpinMessage(nMessageId) {
    if (!bIsAdmin) return;
    
    objSocket.emit('unpin_message', { message_id: nMessageId });
    console.log('Unpinning message:', nMessageId);
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
/**
 * Send Typing Indicator
 * Notifies other users when current user is typing
 * @param {boolean} bIsTyping - Whether user is currently typing
 * @param {string} strChatType - Type of chat (public/private)
 * @param {number} nRecipientId - Recipient ID for private chats
 */
function sendTypingIndicator(bIsTyping, strChatType, nRecipientId = null) {
    if (strConnectionStatus === 'connected') {
        objSocket.emit('typing', {
            is_typing: bIsTyping,
            chat_type: strChatType,
            recipient_id: nRecipientId
        });
    }
}

/**
 * Handle Typing Indicators
 * Processes incoming typing status from other users
 * @param {Object} objData - Typing indicator data
 */
function handleTypingIndicator(objData) {
    if (objData.user_id === nCurrentUserId) return; // Don't show our own typing
    
    const elemTypingContainer = document.getElementById('typingIndicator');
    if (!elemTypingContainer) return;
    
    const strUserName = objData.display_name || objData.username;
    if (objData.is_typing) {
        setTypingUsers.add(strUserName);
    } else {
        setTypingUsers.delete(strUserName);
    }
    
    updateTypingDisplay();
}

/**
 * Update Typing Display
 * Updates the visual display of users currently typing
 */
function updateTypingDisplay() {
    const elemTypingContainer = document.getElementById('typingIndicator');
    if (!elemTypingContainer) return;
    
    if (setTypingUsers.size === 0) {
        elemTypingContainer.innerHTML = '';
        elemTypingContainer.style.display = 'none';
    } else {
        const arrUserList = Array.from(setTypingUsers);
        let strText = '';
        
        // Format typing indicator text based on number of typing users
        if (arrUserList.length === 1) {
            strText = `${arrUserList[0]} is typing...`;
        } else if (arrUserList.length === 2) {
            strText = `${arrUserList[0]} and ${arrUserList[1]} are typing...`;
        } else {
            strText = `${arrUserList[0]} and ${arrUserList.length - 1} others are typing...`;
        }
        
        elemTypingContainer.innerHTML = `<div class="typing-indicator">${strText}</div>`;
        elemTypingContainer.style.display = 'block';
    }
}

/**
 * Connection Status Management Functions
 * Handles real-time connection status display and user feedback
 */

/**
 * Update Connection Status Display
 * Updates the visual connection status indicator based on current state
 */
function updateConnectionStatus() {
    console.log('🔄 Updating connection status:', strConnectionStatus);
    
    let elemStatusIndicator = document.getElementById('connectionStatus');
    if (!elemStatusIndicator) {
        // Create connection status indicator if it doesn't exist
        const elemIndicator = document.createElement('div');
        elemIndicator.id = 'connectionStatus';
        elemIndicator.className = 'connection-status';
        document.body.appendChild(elemIndicator);
        console.log('✅ Created connection status indicator');
        elemStatusIndicator = elemIndicator;
    }
    
    elemStatusIndicator.className = `connection-status ${strConnectionStatus}`;
    
    // Set status display based on current connection state
    switch (strConnectionStatus) {
        case 'connected':
            elemStatusIndicator.innerHTML = '🟢 Real-time';
            elemStatusIndicator.title = 'Connected - Real-time messaging active';
            break;
        case 'connecting':
            elemStatusIndicator.innerHTML = '🟡 Connecting...';
            elemStatusIndicator.title = 'Connecting to server...';
            break;
        case 'disconnected':
            elemStatusIndicator.innerHTML = '🔴 Offline';
            elemStatusIndicator.title = 'Disconnected - Messages will be sent when reconnected';
            break;
        case 'error':
            elemStatusIndicator.innerHTML = '⚠️ Error';
            elemStatusIndicator.title = 'Connection error - Attempting to reconnect...';
            break;
    }
    
    console.log('📊 Connection status updated to:', elemStatusIndicator.innerHTML);
}

/**
 * Start Heartbeat Monitoring
 * Initiates periodic connection health checks
 */
function startHeartbeat() {
    if (nHeartbeatInterval) clearInterval(nHeartbeatInterval);
    
    nHeartbeatInterval = setInterval(() => {
        if (strConnectionStatus === 'connected') {
            objSocket.emit('heartbeat');
        }
    }, 10000); // Send heartbeat every 10 seconds
}

/**
 * Stop Heartbeat Monitoring
 * Cleans up heartbeat interval when connection is lost
 */
function stopHeartbeat() {
    if (nHeartbeatInterval) {
        clearInterval(nHeartbeatInterval);
        nHeartbeatInterval = null;
    }
}

/**
 * Update Connection Quality Display
 * Shows connection latency-based quality indicator
 */
function updateConnectionQuality() {
    const nLatency = Date.now() - nLastHeartbeat;
    const elemQualityIndicator = document.getElementById('connectionQuality');
    
    if (elemQualityIndicator) {
        // Categorize connection quality based on latency
        if (nLatency < 100) {
            elemQualityIndicator.innerHTML = '🔵 Excellent';
            elemQualityIndicator.className = 'quality excellent';
        } else if (nLatency < 300) {
            elemQualityIndicator.innerHTML = '🟢 Good';
            elemQualityIndicator.className = 'quality good';
        } else if (nLatency < 1000) {
            elemQualityIndicator.innerHTML = '🟡 Fair';
            elemQualityIndicator.className = 'quality fair';
        } else {
            elemQualityIndicator.innerHTML = '🔴 Poor';
            elemQualityIndicator.className = 'quality poor';
        }
    }
}

/**
 * Message Queue Management Functions
 * Handles offline message queuing and processing
 */

/**
 * Add Message to Queue
 * Stores messages when offline for later transmission
 * @param {Object} objMessage - Message object to queue
 */
function addToMessageQueue(objMessage) {
    arrMessageQueue.push(objMessage);
}

/**
 * Remove Message from Queue
 * Removes processed messages and updates UI elements
 * @param {string} strMessageId - ID of message to remove from queue
 */
function removeFromMessageQueue(strMessageId) {
    const elemTempMessage = document.querySelector(`[data-temp-id="${strMessageId}"]`);
    if (elemTempMessage) {
        elemTempMessage.removeAttribute('data-temp-id');
        elemTempMessage.classList.remove('temp-message');
    }
    arrMessageQueue = arrMessageQueue.filter(objMsg => objMsg.id !== strMessageId);
}

/**
 * Process Message Queue
 * Sends all queued messages when connection is restored
 */
function processMessageQueue() {
    // Process any messages that were queued while disconnected
    arrMessageQueue.forEach(objMsg => {
        if (objMsg.temp) {
            // Resend temporary messages based on type
            if (objMsg.is_private) {
                objSocket.emit('send_private_message', {
                    text: objMsg.text,
                    recipient_id: objMsg.recipient_id
                });
            } else {
                objSocket.emit('send_message', {
                    text: msg.text
                });
            }
        }
    });
}

/**
 * Play Notification Sound
 * Generates a subtle audio notification using Web Audio API
 */
function playNotificationSound() {
    // Create a subtle notification sound using Web Audio API
    const objAudioContext = window.AudioContext || window.webkitAudioContext;
    if (objAudioContext) {
        try {
            const objContext = new objAudioContext();
            const objOscillator = objContext.createOscillator();
            const objGainNode = objContext.createGain();
            
            // Connect audio nodes
            objOscillator.connect(objGainNode);
            objGainNode.connect(objContext.destination);
            
            // Configure frequency sweep (high to low pitch)
            objOscillator.frequency.setValueAtTime(800, objContext.currentTime);
            objOscillator.frequency.exponentialRampToValueAtTime(400, objContext.currentTime + 0.1);
            
            // Configure volume envelope (fade out)
            objGainNode.gain.setValueAtTime(0.1, objContext.currentTime);
            objGainNode.gain.exponentialRampToValueAtTime(0.01, objContext.currentTime + 0.1);
            
            // Play the sound for 100ms
            objOscillator.start(objContext.currentTime);
            objOscillator.stop(objContext.currentTime + 0.1);
        } catch (objError) {
            // Fallback: silently fail if audio is not available
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