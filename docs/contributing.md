---
layout: default
title: Contributing Guide
---

# 🤝 Contributing to Chattrix

Thank you for your interest in contributing to Chattrix! This guide will help you get started with contributing to the project.

## 🎯 How to Contribute

### Ways to Contribute

- **🐛 Bug Reports:** Report issues you encounter
- **✨ Feature Requests:** Suggest new features
- **📝 Documentation:** Improve or add documentation
- **💻 Code Contributions:** Submit code improvements
- **🧪 Testing:** Help test new features and releases
- **🌍 Translations:** Help translate the interface
- **🎨 Design:** Contribute UI/UX improvements

## 🚀 Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YourUsername/Chattrix.git
cd Chattrix

# Add upstream remote
git remote add upstream https://github.com/DankiCalamari/Chattrix.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run application
python app.py
```

### 3. Create a Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

## 🐛 Bug Reports

### Before Submitting

1. **Search existing issues** to avoid duplicates
2. **Test on latest version** to ensure bug still exists
3. **Gather information** about your environment

### Bug Report Template

```markdown
**Bug Description**
A clear description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Screenshots**
If applicable, add screenshots to help explain the problem.

**Environment**
- OS: [e.g., Ubuntu 20.04]
- Browser: [e.g., Chrome 91.0]
- Chattrix Version: [e.g., 1.0.0]
- Python Version: [e.g., 3.9.5]

**Additional Context**
Any other context about the problem.

**Error Logs**
```
Paste relevant error logs here
```
```

## ✨ Feature Requests

### Feature Request Template

```markdown
**Feature Description**
A clear description of the feature you'd like to see.

**Problem/Use Case**
What problem does this feature solve? What's the use case?

**Proposed Solution**
Describe how you'd like this feature to work.

**Alternative Solutions**
Any alternative solutions you've considered.

**Additional Context**
Screenshots, mockups, or other context that helps explain the feature.

**Implementation Notes**
If you have ideas about how this could be implemented.
```

## 💻 Code Contributions

### Coding Standards

#### Python Code Style
```python
# Use PEP 8 style guide
# Maximum line length: 88 characters (Black formatter)
# Use type hints where appropriate

def send_message(user_id: int, content: str) -> bool:
    """Send a message to a user.
    
    Args:
        user_id: The ID of the recipient user
        content: The message content
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    # Implementation here
    pass

# Use descriptive variable names
user_message_count = get_user_message_count(user.id)
is_message_valid = validate_message_content(content)
```

#### Frontend Code Style
```javascript
// Use modern JavaScript (ES6+)
// Use camelCase for variables and functions
// Use PascalCase for classes

const messageInput = document.getElementById('messageInput');
const socketConnection = io();

// Use arrow functions for short functions
const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
};

// Use async/await for promises
async function sendMessage(content) {
    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        return await response.json();
    } catch (error) {
        console.error('Failed to send message:', error);
        throw error;
    }
}
```

### Development Guidelines

#### Backend Development

**1. Database Changes**
```python
# Always use migrations for database changes
# Create migration scripts in migrations/ folder

# Example migration
"""Add message reactions table

Revision ID: abc123
Revises: def456
Create Date: 2025-08-07 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('message_reactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('emoji', sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('message_reactions')
```

**2. API Endpoints**
```python
@app.route('/api/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def add_reaction(message_id):
    """Add a reaction to a message."""
    try:
        data = request.get_json()
        
        # Validate input
        emoji = data.get('emoji')
        if not emoji or len(emoji) > 50:
            return jsonify({'error': 'Invalid emoji'}), 400
            
        # Check if message exists and user has access
        message = Message.query.get_or_404(message_id)
        if not user_can_access_message(current_user.id, message):
            return jsonify({'error': 'Access denied'}), 403
            
        # Add reaction
        reaction = MessageReaction(
            message_id=message_id,
            user_id=current_user.id,
            emoji=emoji
        )
        db.session.add(reaction)
        db.session.commit()
        
        # Emit real-time update
        socketio.emit('reaction_added', {
            'message_id': message_id,
            'user_id': current_user.id,
            'emoji': emoji
        }, room=f'conversation_{message.conversation_id}')
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error adding reaction: {e}')
        return jsonify({'error': 'Internal server error'}), 500
```

**3. Error Handling**
```python
# Always include proper error handling
# Log errors with appropriate level
# Return user-friendly error messages

import logging

logger = logging.getLogger(__name__)

def upload_file(file):
    """Upload a file with comprehensive error handling."""
    try:
        # Validate file
        if not file or not file.filename:
            raise ValueError("No file provided")
            
        if not allowed_file(file.filename):
            raise ValueError("File type not allowed")
            
        if file.content_length > MAX_FILE_SIZE:
            raise ValueError("File too large")
            
        # Process upload
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        logger.info(f"File uploaded successfully: {filename}")
        return file_path
        
    except ValueError as e:
        logger.warning(f"File upload validation error: {e}")
        raise
    except IOError as e:
        logger.error(f"File upload IO error: {e}")
        raise RuntimeError("Failed to save file")
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise RuntimeError("Upload failed")
```

#### Frontend Development

**1. Real-time Updates**
```javascript
// Handle WebSocket events properly
socket.on('new_message', (data) => {
    // Validate data
    if (!data || !data.message) {
        console.error('Invalid message data received');
        return;
    }
    
    // Update UI
    const messageElement = createMessageElement(data.message);
    messagesContainer.appendChild(messageElement);
    
    // Scroll to bottom if user is at bottom
    if (isUserAtBottom()) {
        scrollToBottom();
    }
    
    // Show notification if window not focused
    if (document.hidden && data.message.sender_id !== currentUserId) {
        showNotification(data.message);
    }
    
    // Update conversation list
    updateConversationsList(data.conversation_id, data.message);
});

// Handle connection errors
socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error);
    showConnectionError();
});

socket.on('disconnect', (reason) => {
    console.warn('Socket disconnected:', reason);
    showConnectionStatus('disconnected');
});
```

**2. User Interface**
```javascript
// Create reusable UI components
class MessageComponent {
    constructor(messageData) {
        this.message = messageData;
        this.element = null;
    }
    
    render() {
        this.element = document.createElement('div');
        this.element.className = 'message';
        this.element.dataset.messageId = this.message.id;
        
        // Add message content
        this.element.innerHTML = `
            <div class="message-header">
                <img src="${this.message.sender.profile_pic}" alt="Profile" class="profile-pic">
                <span class="sender-name">${this.message.sender.display_name}</span>
                <span class="timestamp">${formatTimestamp(this.message.timestamp)}</span>
            </div>
            <div class="message-content">${this.sanitizeContent(this.message.content)}</div>
            ${this.renderActions()}
        `;
        
        // Add event listeners
        this.attachEventListeners();
        
        return this.element;
    }
    
    sanitizeContent(content) {
        // Sanitize HTML content to prevent XSS
        const div = document.createElement('div');
        div.textContent = content;
        return div.innerHTML;
    }
    
    renderActions() {
        if (this.message.sender_id === currentUserId) {
            return `
                <div class="message-actions">
                    <button class="edit-btn" title="Edit">✏️</button>
                    <button class="delete-btn" title="Delete">🗑️</button>
                </div>
            `;
        }
        return '';
    }
    
    attachEventListeners() {
        const editBtn = this.element.querySelector('.edit-btn');
        const deleteBtn = this.element.querySelector('.delete-btn');
        
        if (editBtn) {
            editBtn.addEventListener('click', () => this.editMessage());
        }
        
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteMessage());
        }
    }
    
    async editMessage() {
        // Implementation for editing messages
    }
    
    async deleteMessage() {
        // Implementation for deleting messages
    }
}
```

### Testing

#### Backend Tests
```python
# Use pytest for testing
# Write tests for all new features

import pytest
from app import app, db
from models import User, Message

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def authenticated_user(client):
    # Create and authenticate a test user
    user = User(username='testuser', email='test@example.com')
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()
    
    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    return user

def test_send_message(client, authenticated_user):
    """Test sending a message."""
    response = client.post('/api/messages', json={
        'conversation_id': 1,
        'content': 'Test message',
        'type': 'text'
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert 'message_data' in data

def test_send_empty_message(client, authenticated_user):
    """Test that empty messages are rejected."""
    response = client.post('/api/messages', json={
        'conversation_id': 1,
        'content': '',
        'type': 'text'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
```

#### Frontend Tests
```javascript
// Use Jest for frontend testing

describe('MessageComponent', () => {
    let messageData;
    
    beforeEach(() => {
        messageData = {
            id: 1,
            content: 'Test message',
            sender: {
                id: 1,
                display_name: 'Test User',
                profile_pic: 'default.jpg'
            },
            timestamp: '2025-08-07T14:30:00Z'
        };
    });
    
    test('renders message correctly', () => {
        const component = new MessageComponent(messageData);
        const element = component.render();
        
        expect(element.classList.contains('message')).toBe(true);
        expect(element.querySelector('.sender-name').textContent).toBe('Test User');
        expect(element.querySelector('.message-content').textContent).toBe('Test message');
    });
    
    test('sanitizes HTML content', () => {
        messageData.content = '<script>alert("xss")</script>Hello';
        const component = new MessageComponent(messageData);
        const element = component.render();
        
        const content = element.querySelector('.message-content').innerHTML;
        expect(content).not.toContain('<script>');
        expect(content).toContain('Hello');
    });
});
```

### Documentation

#### Code Documentation
```python
# Use docstrings for all functions and classes

def calculate_message_score(message: Message, user: User) -> float:
    """Calculate relevance score for a message.
    
    The score is calculated based on various factors including:
    - Message recency
    - User interaction history
    - Message content relevance
    
    Args:
        message: The message to score
        user: The user for whom to calculate the score
        
    Returns:
        A float score between 0.0 and 1.0, where 1.0 is most relevant
        
    Raises:
        ValueError: If message or user is None
        
    Example:
        >>> message = Message.query.get(1)
        >>> user = User.query.get(1)
        >>> score = calculate_message_score(message, user)
        >>> print(f"Relevance score: {score:.2f}")
        Relevance score: 0.85
    """
    if not message or not user:
        raise ValueError("Message and user must not be None")
        
    # Implementation here
    pass
```

### Pull Request Process

#### 1. Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Changes are tested locally
- [ ] Commit messages are clear

#### 2. Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally
```

#### 3. Review Process

1. **Automated Checks:** CI/CD pipeline runs tests
2. **Code Review:** Maintainers review the code
3. **Testing:** Changes are tested in staging environment
4. **Approval:** At least one maintainer approves
5. **Merge:** Changes are merged to main branch

### Release Process

#### Version Numbering
We follow [Semantic Versioning (SemVer)](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

#### Release Checklist
- [ ] Update version number
- [ ] Update CHANGELOG.md
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git
- [ ] Deploy to staging for testing
- [ ] Deploy to production

## 🏆 Recognition

### Contributors

All contributors are recognized in:
- README.md contributors section
- CONTRIBUTORS.md file
- Release notes
- Annual contributor appreciation

### Types of Recognition

- **🌟 Featured Contributor:** Monthly highlight
- **🎯 Bug Hunter:** Most bugs reported/fixed
- **📚 Documentation Champion:** Best documentation contributions
- **🚀 Feature Master:** Most features implemented
- **🤝 Community Helper:** Most helpful in discussions

## 📞 Getting Help

### Development Help

**Stuck on something?**
- Check existing [GitHub Issues](https://github.com/DankiCalamari/Chattrix/issues)
- Start a [Discussion](https://github.com/DankiCalamari/Chattrix/discussions)
- Join our [Discord community](https://discord.gg/chattrix)

**Need mentoring?**
- Tag `@maintainers` in your issue
- Attend office hours (schedule TBD)
- Pair programming sessions available

### Communication Channels

- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** General questions and ideas
- **Discord:** Real-time chat and help
- **Email:** security@chattrix.com (security issues only)

## 🎉 Thank You!

Every contribution, no matter how small, helps make Chattrix better for everyone. Thank you for taking the time to contribute!

---

**Ready to contribute?** Start by checking out our [good first issues](https://github.com/DankiCalamari/Chattrix/labels/good%20first%20issue) or join the discussion in our [community channels](https://discord.gg/chattrix).

---

*Last updated: August 2025*
