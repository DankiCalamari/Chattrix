from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import send, emit, join_room, leave_room, SocketIO
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from flask_toastr import Toastr
from flask import flash
from sqlalchemy import text
import json
from pywebpush import webpush, WebPushException
from dotenv import load_dotenv
from config import config

# Load environment variables
load_dotenv()

# --- Flask app setup ---
def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Override database URI for production to use environment variables
    if config_name == 'production':
        from config import get_database_uri
        database_uri = get_database_uri()
        app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
        
        # Add SSL config only for AWS RDS PostgreSQL
        if database_uri and 'postgresql://' in database_uri and 'amazonaws.com' in database_uri:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                **app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}),
                'connect_args': {
                    'sslmode': 'require',
                    'connect_timeout': 10
                }
            }
    
    return app

# Create app instance
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Get configuration values
VAPID_PRIVATE_KEY = app.config['VAPID_PRIVATE_KEY']
VAPID_PUBLIC_KEY = app.config['VAPID_PUBLIC_KEY']
VAPID_CLAIMS = app.config['VAPID_CLAIMS']

# Upload folder configuration from config
PROFILE_PICS_FOLDER = app.config['PROFILE_PICS_FOLDER']
UPLOADS_FOLDER = app.config['UPLOADS_FOLDER']
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx', 'mp4'}

# Create upload directories
# Create upload directories
os.makedirs(PROFILE_PICS_FOLDER, exist_ok=True)
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)

# Configure SocketIO for production
socketio_kwargs = {'manage_session': True}
if config_name == 'production':
    socketio_kwargs.update({
        'logger': True,
        'engineio_logger': True,
        'cors_allowed_origins': "*"  # Configure this properly for your domain
    })

socketio = SocketIO(app, **socketio_kwargs)

# --- Flask-Login setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Global variables for tracking user locations ---
user_locations = {}  # Track which page/chat each user is on

# --- Database Models ---

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Increased from 80 to 255 for password hashes
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(120), default='default.jpg')
    bio = db.Column(db.String(300), default='')

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Message model with private messaging support
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # NULL = public message
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    is_private = db.Column(db.Boolean, default=False)
    pinned = db.Column(db.Boolean, default=False)
    is_file = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    read = db.Column(db.Boolean, default=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

# Conversation model to track private chats
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now)
    
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    last_message = db.relationship('Message', foreign_keys=[last_message_id])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Use db.session.get() instead of User.query.get()

# --- Database Migration ---
def migrate_database():
    """Add missing columns to existing database"""
    try:
        with app.app_context():
            # Use db.session.execute instead of db.engine.execute
            try:
                db.session.execute(text("SELECT recipient_id FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN recipient_id INTEGER"))
                db.session.commit()
                print("Added recipient_id column")
            
            try:
                db.session.execute(text("SELECT is_private FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN is_private BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("Added is_private column")
            
            try:
                db.session.execute(text("SELECT read FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN read BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("Added read column")
            
            try:
                db.session.execute(text("SELECT is_file FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN is_file BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("Added is_file column")
            
            try:
                db.session.execute(text("SELECT file_path FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN file_path VARCHAR(255)"))
                db.session.commit()
                print("Added file_path column")
            
            try:
                db.session.execute(text("SELECT original_filename FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN original_filename VARCHAR(255)"))
                db.session.commit()
                print("Added original_filename column")
            
            try:
                db.session.execute(text("SELECT pinned FROM message LIMIT 1"))
            except:
                db.session.execute(text("ALTER TABLE message ADD COLUMN pinned BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("Added pinned column")
            
            # Check if push_subscription table exists
            try:
                db.session.execute(text("SELECT 1 FROM push_subscription LIMIT 1"))
                print("PushSubscription table exists")
            except:
                print("Creating PushSubscription table...")
                db.create_all()
                print("PushSubscription table created")
                
    except Exception as e:
        print(f"Migration error: {e}")

# --- Create tables and migrate ---
with app.app_context():
    db.create_all()
    migrate_database()

# --- SocketIO session/user mapping ---
user_sid_map = {}
online_users = {}

# --- Helper Functions ---

@app.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    try:
        subscription_data = request.get_json()
        
        if not subscription_data or 'endpoint' not in subscription_data:
            return jsonify({'success': False, 'error': 'Invalid subscription data'}), 400
        
        # Remove existing subscriptions for this user
        PushSubscription.query.filter_by(user_id=current_user.id).delete()
        
        # Add new subscription
        subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=subscription_data['endpoint'],
            p256dh=subscription_data['keys']['p256dh'],
            auth=subscription_data['keys']['auth']
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        print(f"✅ Push subscription saved for user {current_user.id}")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌ Error saving push subscription: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/vapid-public-key')
def get_vapid_public_key():
    """Return the VAPID public key for frontend use"""
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})

@app.route('/test-push/<int:user_id>')
@login_required
def test_push_notification(user_id):
    """Test endpoint to send a push notification to a specific user"""
    if current_user.is_admin:
        send_web_push(
            user_id,
            "Test Notification",
            "This is a test push notification from Chattrix!",
            "/chat"
        )
        return jsonify({'success': True, 'message': f'Test notification sent to user {user_id}'})
    else:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403


def send_web_push(user_id, title, body, url='/chat'):
    try:
        subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
        
        if not subscriptions:
            print(f"⚠️ No push subscriptions found for user {user_id}")
            return
        
        print(f"📤 Sending push notification to {len(subscriptions)} subscription(s) for user {user_id}")
        
        for subscription in subscriptions:
            try:
                payload = json.dumps({
                    "title": title,
                    "body": body,
                    "url": url,
                    "icon": "/static/profile_pics/default.jpg",
                    "badge": "/static/profile_pics/default.jpg"
                })
                
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh,
                            "auth": subscription.auth
                        }
                    },
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS
                )
                print(f"✅ Push notification sent successfully to user {user_id}")
                
            except WebPushException as e:
                print(f"❌ WebPush error for user {user_id}: {e}")
                if e.response and e.response.status_code == 410:
                    # Subscription expired, remove it
                    print(f"🗑️ Removing expired subscription for user {user_id}")
                    db.session.delete(subscription)
                    db.session.commit()
            except Exception as e:
                print(f"❌ Unexpected error sending push notification: {e}")
                
    except Exception as e:
        print(f"❌ Error in send_web_push function: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_or_create_conversation(user1_id, user2_id):
    """Get existing conversation or create new one"""
    conversation = Conversation.query.filter(
        ((Conversation.user1_id == user1_id) & (Conversation.user2_id == user2_id)) |
        ((Conversation.user1_id == user2_id) & (Conversation.user2_id == user1_id))
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user1_id=min(user1_id, user2_id),
            user2_id=max(user1_id, user2_id),
            updated_at=datetime.now()
        )
        db.session.add(conversation)
        db.session.commit()
    
    return conversation

# --- Routes ---

@app.route('/')
@login_required
def index():
    """Main public chat page."""
    return render_template('chat.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
        else:
            hashedPassword = generate_password_hash(password, method='pbkdf2:sha256')
            user = User(display_name=display_name, username=username, password=hashedPassword)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User does not exist.", "error")
        elif not check_password_hash(user.password, password):
            flash("Incorrect password.", "error")
        else:
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Allow user to update display name, password, and profile picture."""
    if request.method == 'POST':
        bio = request.form.get('bio')
        display_name = request.form.get('display_name')
        password = request.form.get('password')
        
        if display_name:
            current_user.display_name = display_name

        if password:
            current_user.password = generate_password_hash(password, method='pbkdf2:sha256')
        
        if bio is not None:
            current_user.bio = bio
            
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{current_user.id}_{file.filename}")
                filepath = os.path.join(app.config['PROFILE_PICS_FOLDER'], filename)
                file.save(filepath)
                current_user.profile_pic = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

# --- Private Messaging Routes ---

@app.route('/conversations')
@login_required
def conversations():
    """Show all private conversations for current user"""
    conversations = db.session.query(Conversation).filter(
        (Conversation.user1_id == current_user.id) | 
        (Conversation.user2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    return render_template('conversations.html', conversations=conversations)

@app.route('/chat/<int:user_id>')
@login_required 
def private_chat(user_id):
    """Private chat with specific user"""
    other_user = User.query.get_or_404(user_id)
    
    if other_user.id == current_user.id:
        flash("You can't chat with yourself!", "error")
        return redirect(url_for('conversations'))
    
    # Get or create conversation
    conversation = get_or_create_conversation(current_user.id, user_id)
    
    # Get messages for this conversation
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    # Mark messages as read
    Message.query.filter(
        (Message.sender_id == user_id) & 
        (Message.recipient_id == current_user.id) &
        (Message.read == False)
    ).update({'read': True})
    db.session.commit()
    
    return render_template('private_chat.html', other_user=other_user, messages=messages)

@app.route('/users')
@login_required
def user_list():
    """Show all users to start private chats"""
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('user_list.html', users=users)

# --- File Upload Routes ---

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not (file and allowed_file(file.filename)):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        recipient_id = request.form.get('recipient_id')  # For private file sharing
        filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOADS_FOLDER'], filename)
        file.save(filepath)
        
        # Save file message to database
        file_message = Message(
            sender_id=current_user.id,
            recipient_id=int(recipient_id) if recipient_id else None,
            text=f"[FILE:{filename}:{file.filename}]",
            timestamp=datetime.now(),
            is_private=bool(recipient_id),
            is_file=True,
            file_path=filepath,
            original_filename=file.filename
        )
        db.session.add(file_message)
        db.session.commit()
        
        # Update conversation if private file
        if recipient_id:
            conversation = get_or_create_conversation(current_user.id, int(recipient_id))
            conversation.last_message_id = file_message.id
            conversation.updated_at = datetime.now()
            db.session.commit()
            
            # Send to specific users only
            socketio.emit('receive_message', {
                'id': file_message.id,
                'display_name': current_user.display_name,
                'text': file_message.text,
                'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_private': True,
                'sender_id': current_user.id,
                'profile_pic': current_user.profile_pic or 'default.jpg'
            }, room=f"user_{recipient_id}")
            
            socketio.emit('receive_message', {
                'id': file_message.id,
                'display_name': current_user.display_name,
                'text': file_message.text,
                'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_private': True,
                'sender_id': current_user.id,
                'profile_pic': current_user.profile_pic or 'default.jpg'
            }, room=f"user_{current_user.id}")
        else:
            # Public file - broadcast to all
            socketio.emit('receive_message', {
                'id': file_message.id,
                'display_name': current_user.display_name,
                'text': file_message.text,
                'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_private': False,
                'sender_id': current_user.id,
                'profile_pic': current_user.profile_pic or 'default.jpg'
            }, broadcast=True)
        
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# --- Message API Routes ---

@app.route('/messages')
@login_required
def get_messages():
    """Return all public messages with profile pictures."""
    messages = Message.query.filter_by(is_private=False).order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'display_name': msg.sender.display_name if msg.sender else 'System',
            'username': msg.sender.username if msg.sender else 'system',
            'text': msg.text,
            'message': msg.text,  # For compatibility
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_private': False,
            'sender_id': msg.sender_id,
            'profile_pic': url_for('static', filename=f'profile_pics/{msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else "default.jpg"}'),
            'avatar': url_for('static', filename=f'profile_pics/{msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else "default.jpg"}')
        })
    return jsonify(result)

@app.route('/pinned_messages')
@login_required
def get_pinned_messages():
    """Return all pinned messages with profile pictures."""
    pinned = Message.query.filter_by(pinned=True, is_private=False).order_by(Message.timestamp.desc()).all()
    result = []
    for msg in pinned:
        result.append({
            'id': msg.id,
            'display_name': msg.sender.display_name if msg.sender else 'System',
            'username': msg.sender.username if msg.sender else 'system',
            'text': msg.text,
            'message': msg.text,  # For compatibility
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'pinned': True,
            'profile_pic': url_for('static', filename=f'profile_pics/{msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else "default.jpg"}'),
            'avatar': url_for('static', filename=f'profile_pics/{msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else "default.jpg"}')
        })
    return jsonify(result)

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handle user connection and broadcast online users."""
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")
        user_sid_map[current_user.id] = request.sid
        online_users[current_user.id] = {
            'id': current_user.id,
            'username': current_user.username,
            'display_name': current_user.display_name,
            'profile_pic': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}')
        }
        # Initialize user location
        user_locations[current_user.id] = 'unknown'
        emit('online_users', list(online_users.values()), broadcast=True)
        print(f'✅ User {current_user.id} ({current_user.username}) connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection and broadcast online users."""
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        user_sid_map.pop(current_user.id, None)
        online_users.pop(current_user.id, None)
        # Remove user from location tracking
        user_locations.pop(current_user.id, None)
        emit('online_users', list(online_users.values()), broadcast=True)
        print(f'❌ User {current_user.id} ({current_user.username}) disconnected')

@socketio.on('user_location')
def handle_user_location(data):
    """Track which page/chat the user is currently on"""
    if not current_user.is_authenticated:
        return
        
    location = data.get('location')
    user_locations[current_user.id] = location
    print(f"📍 User {current_user.id} ({current_user.username}) is now on: {location}")

@socketio.on('join_user_room')
def handle_join_user_room():
    """Join user to their personal notification room"""
    if not current_user.is_authenticated:
        return
        
    room = f'user_{current_user.id}'
    join_room(room)
    print(f"🏠 User {current_user.id} ({current_user.username}) joined notification room: {room}")

@socketio.on('join_private_room')
def handle_join_private_room(data):
    """Join private chat room between two users"""
    if not current_user.is_authenticated:
        return
        
    user1_id = data['user1_id']
    user2_id = data['user2_id']
    room = f"private_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
    join_room(room)
    print(f"💬 User {current_user.id} ({current_user.username}) joined private room: {room}")

# Update your handle_private_message function in app.py
@socketio.on('private_message')
def handle_private_message(data):
    """Handle private messages (alternative handler)"""
    if not current_user.is_authenticated:
        return
        
    recipient_id = data['recipient_id']
    message_text = data['message']
    
    recipient = User.query.get(recipient_id)
    if not recipient:
        return
    
    # Create private message using existing Message model
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,  # Set recipient for private message
        text=message_text,
        is_private=True
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Update conversation
    conversation = get_or_create_conversation(current_user.id, recipient_id)
    conversation.last_message_id = message.id
    conversation.updated_at = datetime.now()
    db.session.commit()
    
    # Prepare message data with profile picture
    message_data = {
        'id': message.id,
        'sender_id': current_user.id,
        'username': current_user.username,
        'display_name': current_user.display_name,
        'text': message_text,
        'message': message_text,  # Add both for compatibility
        'timestamp': message.timestamp.isoformat(),
        'recipient_id': recipient_id,
        'profile_pic': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}'),
        'avatar': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}')
    }
    
    # Send to both sender and recipient
    emit('receive_private_message', message_data, room=f"user_{current_user.id}")
    emit('receive_private_message', message_data, room=f"user_{recipient_id}")
    
    # Send web push notification to recipient
    send_web_push(
        recipient_id,
        f"Message from {current_user.display_name or current_user.username}",
        message_text[:100] + ("..." if len(message_text) > 100 else ""),
        f"/chat/{current_user.id}"
    )
    
    print(f"💬 Private message sent from {current_user.username} to {recipient.username}")

# Replace your existing send_message handler with this one:
@socketio.on('send_message')
def handle_send_message(data):
    """Handle public messages - this is the main handler for public chat"""
    if not current_user.is_authenticated:
        return
    
    text = data.get('text', '').strip()
    
    if not text:
        return
    
    # Create public message (no recipient_id = public)
    message = Message(
        sender_id=current_user.id,
        recipient_id=None,  # NULL = public message
        text=text,
        timestamp=datetime.now(),
        is_private=False
    )
    db.session.add(message)
    db.session.commit()
    
    # Prepare message data with profile picture URL
    message_data = {
        'id': message.id,
        'display_name': current_user.display_name,
        'username': current_user.username,
        'text': message.text,
        'message': message.text,  # For compatibility
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_private': False,
        'sender_id': current_user.id,
        'profile_pic': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}'),
        'avatar': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}')  # Alternative field name
    }
    
    # Send to all users in public chat
    emit('receive_message', message_data, broadcast=True)
    
    # Send notifications to users not in public chat
    for user_id, location in user_locations.items():
        if user_id != current_user.id and location != 'public_chat':
            emit('notification', {
                'type': 'public_message',
                'title': 'New message in Public Chat',
                'message': f'{current_user.display_name or current_user.username}: {text[:50]}...',
                'sender': current_user.display_name or current_user.username,
                'chat_url': url_for('index')
            }, room=f'user_{user_id}')
    
    print(f"📤 Public message sent by {current_user.id}: {text}")

# Add send_private_message handler after the other message handlers
@socketio.on('send_private_message')
def handle_send_private_message(data):
    """Handle private messages"""
    if not current_user.is_authenticated:
        return
    
    recipient_id = data.get('recipient_id')
    message_text = data.get('text') or data.get('message', '')
    
    if not recipient_id or not message_text:
        emit('error', {'message': 'Missing recipient or message'})
        return
    
    # Create private message
    private_message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        text=message_text,
        timestamp=datetime.now(),
        is_private=True
    )
    
    db.session.add(private_message)
    db.session.commit()
    
    # Update conversation
    conversation = get_or_create_conversation(current_user.id, recipient_id)
    conversation.last_message_id = private_message.id
    conversation.updated_at = datetime.now()
    db.session.commit()
    
    # Prepare message data with profile picture
    message_data = {
        'id': private_message.id,
        'text': message_text,
        'message': message_text,
        'sender_id': current_user.id,
        'recipient_id': recipient_id,
        'username': current_user.username,
        'display_name': current_user.display_name,
        'timestamp': private_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'profile_pic': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}'),
        'avatar': url_for('static', filename=f'profile_pics/{current_user.profile_pic or "default.jpg"}')
    }
    
    print(f"📤 Sending private message with profile pic: {message_data['profile_pic']}")
    
    # Send to both sender and recipient
    emit('receive_private_message', message_data, room=f'user_{current_user.id}')
    emit('receive_private_message', message_data, room=f'user_{recipient_id}')
    
    # Send push notification to recipient
    send_web_push(recipient_id, f"Private message from {current_user.username}", message_text)
    
    print(f"📤 Private message sent from {current_user.id} to {recipient_id}")

# Also add these alternative handlers in case your frontend uses different event names:
@socketio.on('message')
def handle_message(data):
    """Alternative handler for public messages"""
    return handle_send_message(data)

@socketio.on('new_message')  
def handle_new_message(data):
    """Another alternative handler for public messages"""
    if isinstance(data, str):
        # If data is just a string, convert to dict
        data = {'text': data}
    return handle_send_message(data)

@socketio.on('send_public_message')
def handle_send_public_message(data):
    """Explicit public message handler"""
    return handle_send_message(data)

# --- Pin/unpin message events ---
@socketio.on('pin_message')
def handle_pin_message(data):
    """Allow admin to pin a message."""
    if not (current_user.is_authenticated and current_user.is_admin):
        emit('error', {'message': 'Admin access required'})
        return
    
    message_id = data.get('message_id')
    if not message_id:
        emit('error', {'message': 'Message ID required'})
        return
        
    msg = db.session.get(Message, message_id)
    if msg and not msg.is_private:  # Only pin public messages
        msg.pinned = True
        db.session.commit()
        emit('update_pinned', {'message_id': message_id}, broadcast=True)
        print(f"📌 Admin {current_user.id} pinned message {message_id}")
        emit('success', {'message': 'Message pinned successfully'})
    else:
        emit('error', {'message': 'Message not found or is private'})

@socketio.on('unpin_message')
def handle_unpin_message(data):
    """Handle unpinning a message"""
    if not (current_user.is_authenticated and current_user.is_admin):
        emit('error', {'message': 'Admin access required'})
        return
    
    message_id = data.get('message_id')
    if not message_id:
        emit('error', {'message': 'Message ID required'})
        return
    
    # Find and unpin the message
    message = db.session.get(Message, message_id)
    if message:
        message.pinned = False
        db.session.commit()
        
        emit('update_unpinned', {'message_id': message_id}, broadcast=True)
        
        print(f"📌 Admin {current_user.id} unpinned message {message_id}")
        emit('success', {'message': 'Message unpinned successfully'})
    else:
        emit('error', {'message': 'Message not found'})

@socketio.on('user_joined')
def handle_user_joined():
    """Broadcast a system message when a user joins."""
    if current_user.is_authenticated:
        join_message_data = {
            'system': True,
            'text': f"{current_user.display_name or current_user.username} has joined the chat.",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'username': 'System',
            'display_name': 'System',
            'profile_pic': url_for('static', filename='profile_pics/default.jpg')
        }
        emit('receive_message', join_message_data, broadcast=True)
        print(f"👋 {current_user.username} joined the chat")

# --- Flask-Admin setup ---
admin = Admin(app, name='Chattrix Admin', template_mode='bootstrap4')

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Message, db.session))
admin.add_view(AdminModelView(Conversation, db.session))

# --- Create admin user ---
def create_admin_user():
    """Create admin user if it doesn't exist"""
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@chattrix.com')
    
    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(
            display_name="Administrator",
            username=admin_username,
            password=generate_password_hash(admin_password, method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user created: username='{admin_username}'")
        if config_name == 'development':
            print(f"Password: '{admin_password}'")

# Initialize database and admin user
with app.app_context():
    db.create_all()
    migrate_database()
    create_admin_user()

# --- Application entry point ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = config_name == 'development'
    
    print(f"Starting Chattrix in {config_name} mode...")
    print(f"Server: http://{host}:{port}")
    
    socketio.run(app, 
                host=host, 
                port=port, 
                debug=debug,
                use_reloader=debug)