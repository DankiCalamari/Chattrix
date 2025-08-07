---
layout: default
title: API Reference
---

# 📡 API Reference

Complete API documentation for Chattrix messaging application.

## 🔗 Base URL

```
https://yourdomain.com/api
```

## 🔐 Authentication

Chattrix uses session-based authentication. Users must be logged in to access most API endpoints.

### Authentication Headers

```http
Content-Type: application/json
X-Requested-With: XMLHttpRequest
```

### Session Management

Sessions are managed via secure HTTP cookies:
- `session` - Session identifier
- `remember_token` - Remember me functionality (optional)

## 📋 REST API Endpoints

### Authentication Endpoints

#### POST /register
Register a new user account.

**Request Body:**
```json
{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepassword123",
    "display_name": "John Doe"
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "display_name": "John Doe",
        "profile_pic": "default.jpg",
        "created_at": "2025-08-07T10:00:00Z"
    }
}
```

**Error Response (400 Bad Request):**
```json
{
    "success": false,
    "message": "Username already exists",
    "errors": {
        "username": ["Username 'johndoe' is already taken"]
    }
}
```

#### POST /login
Authenticate user and create session.

**Request Body:**
```json
{
    "username": "johndoe",
    "password": "securepassword123",
    "remember_me": false
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "id": 1,
        "username": "johndoe",
        "display_name": "John Doe",
        "profile_pic": "default.jpg"
    },
    "redirect_url": "/chat"
}
```

#### POST /logout
End user session.

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Logged out successfully"
}
```

### User Management

#### GET /api/user/profile
Get current user's profile information.

**Response (200 OK):**
```json
{
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "profile_pic": "profile_pics/user_1.jpg",
    "bio": "Software developer and chat enthusiast",
    "last_seen": "2025-08-07T14:30:00Z",
    "is_online": true,
    "created_at": "2025-08-07T10:00:00Z",
    "settings": {
        "notifications_enabled": true,
        "sound_enabled": true,
        "theme": "light"
    }
}
```

#### PUT /api/user/profile
Update user profile information.

**Request Body:**
```json
{
    "display_name": "John Smith",
    "bio": "Updated bio text",
    "settings": {
        "notifications_enabled": false,
        "sound_enabled": true,
        "theme": "dark"
    }
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Profile updated successfully",
    "user": {
        "id": 1,
        "username": "johndoe",
        "display_name": "John Smith",
        "bio": "Updated bio text"
    }
}
```

#### POST /api/user/upload-avatar
Upload user profile picture.

**Request (multipart/form-data):**
```
file: [image file]
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Profile picture updated successfully",
    "profile_pic_url": "/static/profile_pics/user_1_20250807.jpg"
}
```

### User Discovery

#### GET /api/users
Get list of all users (for starting conversations).

**Query Parameters:**
- `search` (optional) - Search users by username or display name
- `limit` (optional) - Maximum number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response (200 OK):**
```json
{
    "users": [
        {
            "id": 2,
            "username": "jane_doe",
            "display_name": "Jane Doe",
            "profile_pic": "profile_pics/user_2.jpg",
            "is_online": true,
            "last_seen": "2025-08-07T14:25:00Z"
        },
        {
            "id": 3,
            "username": "bob_smith",
            "display_name": "Bob Smith",
            "profile_pic": "default.jpg",
            "is_online": false,
            "last_seen": "2025-08-07T12:00:00Z"
        }
    ],
    "total": 2,
    "limit": 50,
    "offset": 0
}
```

### Conversations

#### GET /api/conversations
Get user's conversations list.

**Response (200 OK):**
```json
{
    "conversations": [
        {
            "id": 1,
            "type": "private",
            "participants": [
                {
                    "id": 1,
                    "username": "johndoe",
                    "display_name": "John Doe",
                    "profile_pic": "default.jpg"
                },
                {
                    "id": 2,
                    "username": "jane_doe",
                    "display_name": "Jane Doe",
                    "profile_pic": "profile_pics/user_2.jpg"
                }
            ],
            "last_message": {
                "id": 150,
                "content": "Hey, how are you?",
                "sender_id": 2,
                "sender_name": "Jane Doe",
                "timestamp": "2025-08-07T14:30:00Z",
                "type": "text"
            },
            "unread_count": 2,
            "updated_at": "2025-08-07T14:30:00Z"
        }
    ]
}
```

#### POST /api/conversations
Create a new conversation.

**Request Body:**
```json
{
    "type": "private",
    "participant_ids": [2]
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Conversation created successfully",
    "conversation": {
        "id": 5,
        "type": "private",
        "participants": [
            {
                "id": 1,
                "username": "johndoe",
                "display_name": "John Doe"
            },
            {
                "id": 2,
                "username": "jane_doe",
                "display_name": "Jane Doe"
            }
        ],
        "created_at": "2025-08-07T14:35:00Z"
    }
}
```

### Messages

#### GET /api/conversations/{conversation_id}/messages
Get messages from a conversation.

**Query Parameters:**
- `limit` (optional) - Number of messages to return (default: 50, max: 100)
- `before` (optional) - Message ID to load messages before (for pagination)
- `after` (optional) - Message ID to load messages after

**Response (200 OK):**
```json
{
    "messages": [
        {
            "id": 148,
            "conversation_id": 1,
            "sender_id": 1,
            "sender": {
                "id": 1,
                "username": "johndoe",
                "display_name": "John Doe",
                "profile_pic": "default.jpg"
            },
            "content": "Hello there!",
            "type": "text",
            "timestamp": "2025-08-07T14:25:00Z",
            "edited": false,
            "edited_at": null,
            "file_url": null,
            "file_name": null,
            "file_size": null
        },
        {
            "id": 149,
            "conversation_id": 1,
            "sender_id": 2,
            "sender": {
                "id": 2,
                "username": "jane_doe",
                "display_name": "Jane Doe",
                "profile_pic": "profile_pics/user_2.jpg"
            },
            "content": "Hi! Check out this image:",
            "type": "file",
            "timestamp": "2025-08-07T14:28:00Z",
            "edited": false,
            "edited_at": null,
            "file_url": "/static/uploads/2_20250807_142800_sunset.jpg",
            "file_name": "sunset.jpg",
            "file_size": 245760
        }
    ],
    "has_more": false,
    "conversation_id": 1
}
```

#### POST /api/conversations/{conversation_id}/messages
Send a new message to a conversation.

**Request Body (Text Message):**
```json
{
    "content": "Hello everyone!",
    "type": "text"
}
```

**Request Body (File Message - multipart/form-data):**
```
content: "Check out this file:"
type: "file"
file: [uploaded file]
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Message sent successfully",
    "message_data": {
        "id": 151,
        "conversation_id": 1,
        "sender_id": 1,
        "content": "Hello everyone!",
        "type": "text",
        "timestamp": "2025-08-07T14:35:00Z",
        "file_url": null,
        "file_name": null,
        "file_size": null
    }
}
```

#### PUT /api/messages/{message_id}
Edit an existing message (only sender can edit).

**Request Body:**
```json
{
    "content": "Updated message content"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Message updated successfully",
    "message_data": {
        "id": 151,
        "content": "Updated message content",
        "edited": true,
        "edited_at": "2025-08-07T14:40:00Z"
    }
}
```

#### DELETE /api/messages/{message_id}
Delete a message (only sender can delete).

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Message deleted successfully"
}
```

### File Upload

#### POST /api/upload
Upload a file for sharing in messages.

**Request (multipart/form-data):**
```
file: [file to upload]
conversation_id: 1
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "File uploaded successfully",
    "file": {
        "url": "/static/uploads/1_20250807_143500_document.pdf",
        "name": "document.pdf",
        "size": 1024000,
        "type": "application/pdf"
    }
}
```

**Error Response (413 Payload Too Large):**
```json
{
    "success": false,
    "message": "File too large. Maximum size is 16MB."
}
```

### Push Notifications

#### GET /api/vapid-public-key
Get VAPID public key for push notification subscription.

**Response (200 OK):**
```json
{
    "public_key": "BL7ELnvwqOX8oKXYOSV6..."
}
```

#### POST /api/subscribe
Subscribe to push notifications.

**Request Body:**
```json
{
    "subscription": {
        "endpoint": "https://fcm.googleapis.com/fcm/send/...",
        "keys": {
            "p256dh": "BGyyVt9FFV...",
            "auth": "R9sidzkcdf..."
        }
    }
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Subscription saved successfully"
}
```

#### DELETE /api/subscribe
Unsubscribe from push notifications.

**Request Body:**
```json
{
    "endpoint": "https://fcm.googleapis.com/fcm/send/..."
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Unsubscribed successfully"
}
```

## 🔌 WebSocket Events

Chattrix uses Socket.IO for real-time communication.

### Connection

```javascript
const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});
```

### Client Events (Emitted by Client)

#### join_conversation
Join a conversation room for real-time updates.

```javascript
socket.emit('join_conversation', {
    conversation_id: 1
});
```

#### leave_conversation
Leave a conversation room.

```javascript
socket.emit('leave_conversation', {
    conversation_id: 1
});
```

#### send_message
Send a real-time message.

```javascript
socket.emit('send_message', {
    conversation_id: 1,
    content: "Hello world!",
    type: "text"
});
```

#### typing_start
Indicate user started typing.

```javascript
socket.emit('typing_start', {
    conversation_id: 1
});
```

#### typing_stop
Indicate user stopped typing.

```javascript
socket.emit('typing_stop', {
    conversation_id: 1
});
```

#### mark_as_read
Mark messages as read.

```javascript
socket.emit('mark_as_read', {
    conversation_id: 1,
    message_id: 150
});
```

### Server Events (Received by Client)

#### new_message
Receive a new message in real-time.

```javascript
socket.on('new_message', (data) => {
    console.log('New message:', data);
    // data contains message object
});
```

#### message_edited
Receive notification of edited message.

```javascript
socket.on('message_edited', (data) => {
    console.log('Message edited:', data);
    // data contains updated message object
});
```

#### message_deleted
Receive notification of deleted message.

```javascript
socket.on('message_deleted', (data) => {
    console.log('Message deleted:', data.message_id);
});
```

#### user_typing
Receive typing indicator.

```javascript
socket.on('user_typing', (data) => {
    console.log(`${data.user.display_name} is typing...`);
    // data contains user info and conversation_id
});
```

#### user_stopped_typing
Receive stopped typing indicator.

```javascript
socket.on('user_stopped_typing', (data) => {
    console.log(`${data.user.display_name} stopped typing`);
});
```

#### user_online
User came online.

```javascript
socket.on('user_online', (data) => {
    console.log(`${data.user.display_name} is now online`);
});
```

#### user_offline
User went offline.

```javascript
socket.on('user_offline', (data) => {
    console.log(`${data.user.display_name} is now offline`);
});
```

#### conversation_updated
Conversation information updated.

```javascript
socket.on('conversation_updated', (data) => {
    console.log('Conversation updated:', data);
});
```

## 🚫 Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `413 Payload Too Large` - File too large
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
    "success": false,
    "message": "Error description",
    "errors": {
        "field_name": ["Specific error message"]
    },
    "code": "ERROR_CODE"
}
```

### Rate Limiting

API endpoints are rate limited:

- **General endpoints:** 60 requests per minute
- **Authentication:** 10 requests per minute
- **File uploads:** 20 requests per minute
- **Messages:** 100 requests per minute

Rate limit headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1628345678
```

## 📝 Examples

### Complete Chat Implementation

```javascript
// Initialize Socket.IO connection
const socket = io();

// Join conversation
socket.emit('join_conversation', { conversation_id: 1 });

// Send message
function sendMessage(content) {
    fetch('/api/conversations/1/messages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            content: content,
            type: 'text'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Message sent via API');
        }
    });
}

// Listen for new messages
socket.on('new_message', (message) => {
    displayMessage(message);
});

// Handle typing indicators
let typingTimer;
document.getElementById('messageInput').addEventListener('input', () => {
    socket.emit('typing_start', { conversation_id: 1 });
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
        socket.emit('typing_stop', { conversation_id: 1 });
    }, 1000);
});

// Listen for typing indicators
socket.on('user_typing', (data) => {
    showTypingIndicator(data.user);
});

socket.on('user_stopped_typing', (data) => {
    hideTypingIndicator(data.user);
});
```

### File Upload with Progress

```javascript
function uploadFile(file, conversationId) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);

    return fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Send file message
            return fetch(`/api/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: `Shared a file: ${data.file.name}`,
                    type: 'file',
                    file_url: data.file.url,
                    file_name: data.file.name,
                    file_size: data.file.size
                })
            });
        }
    });
}
```

## 🔒 Security Considerations

### Authentication
- Always include session cookies in requests
- Check authentication status before API calls
- Handle 401 responses by redirecting to login

### Input Validation
- Sanitize all user inputs
- Validate file types and sizes
- Check conversation permissions

### Rate Limiting
- Implement client-side rate limiting
- Handle 429 responses gracefully
- Use exponential backoff for retries

---

**🔗 Related Documentation:**
- [WebSocket Events Guide](websocket-events.md)
- [Security Best Practices](security.md)
- [Error Handling Guide](troubleshooting.md)

---

*Last updated: August 2025*
