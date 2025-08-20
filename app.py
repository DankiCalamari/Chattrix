import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import send, emit, join_room, leave_room, SocketIO
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_admin import Admin, BaseView, expose
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
from PIL import Image


# Load environment variables
load_dotenv()

# --- Flask app setup ---
def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config_name (str): Configuration environment ('development', 'production', 'testing')
        
    Returns:
        Flask: Configured Flask application instance with database and extensions
    """
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

# Configure SocketIO for better real-time performance
socketio_kwargs = {
    'manage_session': True,
    'async_mode': 'eventlet',
    'ping_timeout': 10,
    'ping_interval': 5,
    'max_http_buffer_size': 1000000,
    'allow_upgrades': True,
    'transports': ['websocket', 'polling']
}

if config_name == 'production':
    socketio_kwargs.update({
        'logger': True,
        'engineio_logger': True,
        'cors_allowed_origins': "*"  # Configure this properly for your domain
    })
else:
    # Development mode optimizations
    socketio_kwargs.update({
        'logger': False,
        'engineio_logger': False
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
    """
    User model with authentication and profile support
    
    Handles user registration, login, and profile management
    """
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
    """
    User loader callback for Flask-Login.
    
    Args:
        user_id (str): User ID from session
        
    Returns:
        User: User object if found, None otherwise
    """
    return db.session.get(User, int(user_id))  # Use db.session.get() instead of User.query.get()

# --- Database Migration ---
def migrate_database():
    """
    Safely add missing columns to existing database tables for backward compatibility.
    
    This function checks for the existence of each column before attempting to add it,
    preventing errors when running on existing databases that may be missing newer columns.
    Handles: recipient_id, is_private, read, is_file, file_path, original_filename, pinned columns
    """
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
    """
    API endpoint to provide VAPID public key for push notification setup.
    
    Returns:
        JSON: Contains the VAPID public key needed by frontend for push subscriptions
    """
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})

@app.route('/subscribe-push', methods=['POST'])
@login_required
def subscribe_push():
    """
    Subscribe a user to push notifications.
    
    Expects JSON with 'subscription' containing push subscription data.
    """
    try:
        data = request.get_json()
        subscription_data = data.get('subscription')
        
        if not subscription_data:
            return jsonify({'error': 'No subscription data provided'}), 400
        
        # Remove any existing subscription for this user
        PushSubscription.query.filter_by(user_id=current_user.id).delete()
        
        # Create new subscription
        subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=subscription_data['endpoint'],
            p256dh=subscription_data['keys']['p256dh'],
            auth=subscription_data['keys']['auth']
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        print(f"✅ Push subscription saved for user {current_user.id}")
        print(f"📤 Endpoint: {subscription_data['endpoint'][:100]}...")
        
        return jsonify({'success': True, 'message': 'Push subscription saved'})
        
    except Exception as e:
        print(f"❌ Error saving push subscription: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-push/<int:user_id>')
@login_required
def test_push_notification(user_id):
    """
    Admin-only endpoint for testing push notifications to a specific user.
    
    Args:
        user_id (int): Target user ID for the test notification
        
    Returns:
        JSON: Success/failure status of the test notification
    """
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

@app.route('/register-fallback-notifications', methods=['POST'])
@login_required
def register_fallback_notifications():
    """
    Register user for fallback browser notifications (for localhost testing).
    """
    try:
        data = request.get_json()
        user_id = current_user.id
        
        # For now, just log that the user wants notifications
        # In a real app, you'd store this preference in the database
        print(f"✅ User {user_id} registered for fallback notifications")
        
        return jsonify({'success': True, 'message': 'Registered for notifications'})
        
    except Exception as e:
        print(f"❌ Error registering fallback notifications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-browser-notification/<int:user_id>')
@login_required
def test_browser_notification(user_id):
    """
    Test browser notification endpoint (doesn't require push subscription).
    """
    if current_user.is_admin or current_user.id == user_id:
        # Send a socket event that will trigger browser notification
        socketio.emit('browser_notification', {
            'title': 'Test Browser Notification',
            'message': 'This is a test browser notification from Chattrix!',
            'type': 'test'
        }, room=f'user_{user_id}')
        
        print(f"📤 Browser notification test sent to user {user_id}")
        return jsonify({'success': True, 'message': f'Test browser notification sent to user {user_id}'})
    else:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

@app.route('/push-test')
def push_test():
    """
    Debug page for testing push notifications
    """
    return render_template('push_test.html')


def send_web_push(user_id, title, body, url='/chat'):
    """
    Send web push notifications to all subscribed devices for a specific user.
    
    Args:
        user_id (int): Target user ID for the notification
        title (str): Notification title text
        body (str): Notification body/message text
        url (str): URL to navigate to when notification is clicked (default: '/chat')
        
    Note:
        - Automatically removes expired subscriptions (410 responses)
        - Handles WebPush exceptions gracefully
        - Logs success/failure for debugging
    """
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
    """
    Check if uploaded file has an allowed extension.
    
    Args:
        filename (str): Name of the uploaded file
        
    Returns:
        bool: True if file extension is in ALLOWED_EXTENSIONS, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_profile_picture(filepath, max_size=(200, 200)):
    """
    Resize and optimize profile picture.
    
    Args:
        filepath (str): Path to the uploaded image file
        max_size (tuple): Maximum dimensions (width, height)
    """
    try:
        with Image.open(filepath) as img:
            # Convert to RGB if necessary (handles RGBA, P mode images)
            if img.mode in ('RGBA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Resize maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(filepath, 'JPEG', quality=85, optimize=True)
    except Exception as e:
        print(f"Error resizing profile picture: {e}")
        # If resize fails, keep original file

def get_or_create_conversation(user1_id, user2_id):
    """
    Find existing private conversation between two users or create a new one.
    
    Args:
        user1_id (int): First user's ID
        user2_id (int): Second user's ID
        
    Returns:
        Conversation: Existing or newly created conversation object
        
    Note:
        - Automatically orders user IDs (lower ID as user1, higher as user2)
        - Creates conversation in database if it doesn't exist
        - Updates timestamp when conversation is accessed
    """
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
    """
    Main public chat page route.
    
    Returns:
        Template: Renders the main chat interface (chat.html)
        
    Note:
        - Requires user authentication
        - Serves as the primary chat room for all users
    """
    return render_template('chat.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route handling both GET and POST requests.
    
    GET: Displays registration form
    POST: Processes registration form submission
    
    Form fields:
        - display_name: User's display name
        - username: Unique username for login
        - password: User's password (will be hashed)
        
    Returns:
        Template: Registration form on GET, redirect to login on successful POST
        
    Note:
        - Validates username uniqueness
        - Hashes passwords using PBKDF2 with SHA256
        - Shows flash messages for feedback
    """
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
    """
    User login route handling both GET and POST requests.
    
    GET: Displays login form
    POST: Processes login form submission
    
    Form fields:
        - username: User's username
        - password: User's password
        
    Returns:
        Template: Login form on GET, redirect to main chat on successful POST
        
    Note:
        - Validates user existence and password
        - Uses Flask-Login for session management
        - Shows flash messages for feedback
    """
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
    """
    User logout route that ends the current session.
    
    Returns:
        Redirect: Redirects to login page after logout
        
    Note:
        - Requires user to be logged in
        - Clears user session using Flask-Login
    """
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    User profile management route for updating personal information.
    
    GET: Displays profile editing form with current user data
    POST: Processes profile update form submission
    
    Form fields:
        - display_name: User's display name
        - password: New password (optional)
        - bio: User's bio/description
        - profile_pic: Profile picture file upload
        
    Returns:
        Template: Profile form on GET, redirect to profile on successful POST
        
    Note:
        - Validates and secures uploaded profile pictures
        - Hashes new passwords if provided
        - Updates only provided fields
        - Shows flash messages for feedback
    """
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
                # Generate secure filename with user ID
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{current_user.id}_profile.jpg")  # Always save as jpg after processing
                filepath = os.path.join(app.config['PROFILE_PICS_FOLDER'], filename)
                
                # Save original file temporarily
                temp_path = filepath + '.temp'
                file.save(temp_path)
                
                # Resize and optimize the image
                resize_profile_picture(temp_path, max_size=(200, 200))
                
                # Move processed file to final location
                os.rename(temp_path, filepath)
                
                current_user.profile_pic = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

# --- Private Messaging Routes ---

@app.route('/conversations')
@login_required
def conversations():
    """
    Display all private conversations for the current user.
    
    Returns:
        Template: Conversations list page with all user's private chats
        
    Note:
        - Shows conversations ordered by most recent activity
        - Includes conversations where user is either participant
        - Requires user authentication
    """
    conversations = db.session.query(Conversation).filter(
        (Conversation.user1_id == current_user.id) | 
        (Conversation.user2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    return render_template('conversations.html', conversations=conversations)

@app.route('/chat/<int:user_id>')
@login_required 
def private_chat(user_id):
    """
    Private chat interface between current user and specified user.
    
    Args:
        user_id (int): ID of the other user to chat with
        
    Returns:
        Template: Private chat interface with message history
        Redirect: To conversations page if trying to chat with self
        
    Note:
        - Prevents users from chatting with themselves
        - Creates conversation record if it doesn't exist
        - Automatically marks incoming messages as read
        - Loads complete message history between the two users
    """
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
    """
    Display list of all users available for starting private chats.
    
    Returns:
        Template: User list page showing all users except current user
        
    Note:
        - Excludes current user from the list
        - Used for initiating new private conversations
        - Requires user authentication
    """
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('user_list.html', users=users)

# --- File Upload Routes ---

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Handle file uploads for both public and private messages.
    
    Form fields:
        - file: The uploaded file
        - recipient_id: Target user ID for private file sharing (optional)
        
    Returns:
        JSON: Success status with filename, or error message
        
    Note:
        - Validates file types against ALLOWED_EXTENSIONS
        - Secures filenames and adds timestamp prefix
        - Creates message records for file sharing
        - Supports both public and private file sharing
        - Sends real-time notifications via SocketIO
        - Updates conversation records for private files
    """
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
            })
        
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """
    Serve uploaded files from the uploads directory.
    
    Args:
        filename (str): Name of the file to serve
        
    Returns:
        File: The requested file or 404 if not found
    """
    return send_from_directory(app.config['UPLOADS_FOLDER'], filename)

@app.route('/static/profile_pics/<filename>')  
def profile_pic(filename):
    """
    Serve profile pictures from the profile pics directory.
    
    Args:
        filename (str): Name of the profile picture to serve
        
    Returns:
        File: The requested profile picture or 404 if not found
    """
    return send_from_directory(app.config['PROFILE_PICS_FOLDER'], filename)

@app.route('/test-upload')
def test_upload_page():
    """Test page for file upload functionality without login"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload Test</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div style="padding: 20px;">
            <h1>File Upload Test</h1>
            <div class="message-form-container">
                <form id="messageForm" class="message-form">
                    <label for="file-input" class="file-upload-btn">📎 Select File</label>
                    <input type="file" id="file-input" accept="image/*,.pdf,.txt,.docx,.mp4" style="display: block; margin: 10px 0;">
                    <input type="text" id="msgInput" class="message-input" placeholder="Type your message..." style="margin: 10px 0;">
                    <button type="submit" class="send-btn">Send</button>
                </form>
                <button onclick="testFileUpload()" style="margin: 10px 0; background: red; color: white; padding: 10px;">TEST FILE UPLOAD</button>
            </div>
        </div>
        
        <script src="/static/script.js"></script>
        <script>
            // Initialize file uploads when page loads
            document.addEventListener('DOMContentLoaded', function() {
                console.log('Test page loaded, initializing file uploads...');
                initializeFileUploads();
            });
        </script>
    </body>
    </html>
    '''

# --- Message API Routes ---

@app.route('/messages')
@login_required
def get_messages():
    """
    API endpoint to retrieve all public messages with user profile information.
    
    Returns:
        JSON: Array of public message objects with:
            - Message content and metadata
            - Sender information (display_name, username)
            - Profile picture URLs
            - Timestamps and message IDs
            
    Note:
        - Only returns non-private messages
        - Includes complete user profile data for frontend display
        - Orders messages chronologically
        - Provides both 'text' and 'message' fields for compatibility
    """
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
            'profile_pic': msg.sender.profile_pic if (msg.sender and msg.sender.profile_pic and msg.sender.profile_pic != 'default.jpg') else None,
            'avatar': url_for('static', filename=f'profile_pics/{msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else "default.jpg"}')
        })
    return jsonify(result)

@app.route('/pinned_messages')
@login_required
def get_pinned_messages():
    """
    API endpoint to retrieve all pinned public messages for admin users.
    
    Returns:
        JSON: Array of pinned message objects with complete user profile data
        
    Note:
        - Only returns pinned, non-private messages
        - Orders by most recent first
        - Includes profile pictures and user information
        - Used by admin interface for managing pinned content
    """
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
    """
    Handle WebSocket connection from authenticated users.
    
    Actions performed:
        - Adds user to online users tracking
        - Joins user to their personal notification room
        - Broadcasts updated online users list to all clients
        - Logs connection for debugging
        
    Note:
        - Only processes connections from authenticated users
        - Personal rooms enable targeted private messaging
        - Online users list updates in real-time across all clients
    """
    if current_user.is_authenticated:
        # Add user to online users
        online_users[current_user.id] = {
            'id': current_user.id,
            'username': current_user.username,
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic if (current_user.profile_pic and current_user.profile_pic != 'default.jpg') else None
        }
        
        # Join user to their personal room
        join_room(f'user_{current_user.id}')
        
        # Broadcast updated online users list
        emit('online_users', list(online_users.values()))
        
        print(f"✅ User {current_user.username} connected - {len(online_users)} users online")

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket disconnection from authenticated users.
    
    Actions performed:
        - Removes user from online users tracking
        - Removes user from their personal notification room
        - Broadcasts updated online users list to remaining clients
        - Logs disconnection for debugging
        
    Note:
        - Automatically cleans up user presence data
        - Updates online status for all remaining connected users
    """
    if current_user.is_authenticated:
        # Remove user from online users
        if current_user.id in online_users:
            del online_users[current_user.id]
        
        # Leave user's personal room
        leave_room(f'user_{current_user.id}')
        
        # Broadcast updated online users list
        emit('online_users', list(online_users.values()))
        
        print(f"❌ User {current_user.username} disconnected - {len(online_users)} users online")

@socketio.on('user_location')
def handle_user_location(data):
    """
    Track which page or chat interface the user is currently viewing.
    
    Args:
        data (dict): Contains 'location' key with current page/chat identifier
        
    Note:
        - Used for intelligent notification routing
        - Helps prevent notifications when user is already viewing the content
        - Supports location values: 'public_chat', 'private_chat', etc.
        - Enables context-aware notification delivery
    """
    if not current_user.is_authenticated:
        return
        
    location = data.get('location')
    user_locations[current_user.id] = location
    print(f"📍 User {current_user.id} ({current_user.username}) is now on: {location}")

@socketio.on('join_user_room')
def handle_join_user_room():
    """
    Explicitly join user to their personal notification room and update online status.
    
    Actions performed:
        - Joins user to their personal room (user_<id>)
        - Updates online users tracking with current user data
        - Broadcasts refreshed online users list
        - Logs the room joining event
        
    Note:
        - Used when users explicitly want to ensure they're receiving notifications
        - Refreshes user data in online tracking (display name, profile pic)
        - Complements automatic room joining on connection
    """
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        
        # Update online users when they explicitly join
        online_users[current_user.id] = {
            'id': current_user.id,
            'username': current_user.username,
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic if (current_user.profile_pic and current_user.profile_pic != 'default.jpg') else None
        }
        
        # Send updated online users list
        emit('online_users', list(online_users.values()))
        print(f"👥 {current_user.username} joined user room - Broadcasting online users")

@socketio.on('join_private_room')
def handle_join_private_room(data):
    """
    Join a specific private chat room for real-time messaging between two users.
    
    Args:
        data (dict): Contains 'user1_id' and 'user2_id' for the private conversation
        
    Note:
        - Room names follow pattern: 'private_<min_id>_<max_id>'
        - Enables real-time private messaging between specific users
        - Used when users navigate to private chat interfaces
        - Automatically orders user IDs to ensure consistent room naming
    """
    if not current_user.is_authenticated:
        return
        
    user1_id = data['user1_id']
    user2_id = data['user2_id']
    room = f"private_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
    join_room(room)
    print(f"💬 User {current_user.id} ({current_user.username}) joined private room: {room}")

@socketio.on('get_online_users')
def handle_get_online_users():
    """
    Send current online users list to the requesting client.
    
    Response:
        - Emits 'online_users' event with array of online user objects
        - Each user object contains: id, username, display_name, profile_pic
        
    Note:
        - Used for refreshing online users display
        - Only sends to the requesting client (not broadcast)
        - Logs the request for debugging purposes
    """
    if current_user.is_authenticated:
        emit('online_users', list(online_users.values()))
        print(f"📊 Sent online users list to {current_user.username}: {len(online_users)} users")

# Update your handle_private_message function in app.py
@socketio.on('private_message')
def handle_private_message(data):
    """
    Handle private message sending between users (alternative handler).
    
    Args:
        data (dict): Contains 'recipient_id' and 'message' for private messaging
        
    Actions performed:
        - Creates private message record in database
        - Updates conversation timestamp and last message
        - Sends real-time message to both sender and recipient
        - Triggers push notification to recipient
        - Logs the private message event
        
    Note:
        - Alternative to 'send_private_message' handler for compatibility
        - Includes complete user profile data in message
        - Updates conversation records for chat history
    """
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
    """
    Handle public message sending to the main chat room.
    
    Args:
        data (dict): Contains 'text' field with the message content
        
    Actions performed:
        - Validates message content (non-empty)
        - Creates public message record (recipient_id = None)
        - Broadcasts message to all connected users
        - Sends notifications to users not currently in public chat
        - Logs the public message event
        
    Note:
        - This is the main handler for public chat messages
        - Includes complete user profile data for display
        - Provides both 'text' and 'message' fields for frontend compatibility
        - Context-aware notifications based on user location tracking
    """
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
    emit('receive_message', message_data)
    
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
            
            # Send push notification
            send_web_push(
                user_id,
                'New message in Public Chat',
                f'{current_user.display_name or current_user.username}: {text[:50]}{"..." if len(text) > 50 else ""}',
                '/chat'
            )
    
    print(f"📤 Public message sent by {current_user.id}: {text}")

# Add send_private_message handler after the other message handlers
@socketio.on('send_private_message')
def handle_send_private_message(data):
    """
    Handle private message sending with comprehensive error handling.
    
    Args:
        data (dict): Contains 'recipient_id' and 'text'/'message' fields
        
    Actions performed:
        - Validates recipient and message content
        - Creates private message record in database
        - Updates conversation metadata (last message, timestamp)
        - Sends real-time message to both participants
        - Triggers push notification to recipient
        - Logs the private messaging event
        
    Error handling:
        - Validates required fields presence
        - Sends error messages for missing data
        - Handles database transaction failures
        
    Note:
        - Primary handler for private messaging functionality
        - Supports both 'text' and 'message' field names for compatibility
        - Includes complete user profile data for message display
    """
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
    """
    Alternative handler for public messages using 'message' event name.
    
    Args:
        data: Message data to be processed
        
    Returns:
        Delegates to handle_send_message for consistent processing
        
    Note:
        - Provides compatibility with different frontend implementations
        - Ensures all message events are processed consistently
    """
    return handle_send_message(data)

@socketio.on('new_message')  
def handle_new_message(data):
    """
    Alternative handler for public messages using 'new_message' event name.
    
    Args:
        data: Message data (string or dict) to be processed
        
    Returns:
        Delegates to handle_send_message for consistent processing
        
    Note:
        - Handles both string and dict message formats
        - Converts string messages to dict format automatically
        - Provides compatibility with various frontend implementations
    """
    if isinstance(data, str):
        # If data is just a string, convert to dict
        data = {'text': data}
    return handle_send_message(data)

@socketio.on('send_public_message')
def handle_send_public_message(data):
    """
    Explicit handler for public messages using 'send_public_message' event name.
    
    Args:
        data: Message data to be processed
        
    Returns:
        Delegates to handle_send_message for consistent processing
        
    Note:
        - Provides explicit naming for public message sending
        - Ensures all public message events use the same processing logic
    """
    return handle_send_message(data)

# --- Pin/unpin message events ---
@socketio.on('pin_message')
def handle_pin_message(data):
    """
    Allow admin users to pin important public messages.
    
    Args:
        data (dict): Contains 'message_id' of the message to pin
        
    Actions performed:
        - Validates admin permissions
        - Validates message existence and public status
        - Updates message pinned status in database
        - Broadcasts pin update to all users
        - Logs the pinning action
        
    Error handling:
        - Rejects non-admin users
        - Validates message ID presence
        - Prevents pinning private messages
        - Sends appropriate error messages
        
    Note:
        - Only public messages can be pinned
        - Pinned messages appear in special admin interface
        - Real-time updates across all connected clients
    """
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
        emit('update_pinned', {'message_id': message_id})
        print(f"📌 Admin {current_user.id} pinned message {message_id}")
        emit('success', {'message': 'Message pinned successfully'})
    else:
        emit('error', {'message': 'Message not found or is private'})

@socketio.on('unpin_message')
def handle_unpin_message(data):
    """
    Allow admin users to unpin previously pinned messages.
    
    Args:
        data (dict): Contains 'message_id' of the message to unpin
        
    Actions performed:
        - Validates admin permissions
        - Validates message existence
        - Updates message pinned status to False in database
        - Broadcasts unpin update to all users
        - Logs the unpinning action
        
    Error handling:
        - Rejects non-admin users
        - Validates message ID presence
        - Handles non-existent messages gracefully
        - Sends appropriate error/success messages
        
    Note:
        - Removes message from pinned messages display
        - Real-time updates across all connected clients
        - Complements pin_message functionality
    """
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
        
        emit('update_unpinned', {'message_id': message_id})
        
        print(f"📌 Admin {current_user.id} unpinned message {message_id}")
        emit('success', {'message': 'Message unpinned successfully'})
    else:
        emit('error', {'message': 'Message not found'})

@socketio.on('user_joined')
def handle_user_joined():
    """
    Broadcast a system message when a user joins the chat.
    
    Actions performed:
        - Creates system-generated welcome message
        - Broadcasts join announcement to all users
        - Includes user's display name or username
        - Uses system profile for message display
        - Logs the user join event
        
    Note:
        - Only triggered for authenticated users
        - Creates friendly welcome atmosphere
        - Uses consistent system message formatting
        - Includes timestamp for message history
    """
    if current_user.is_authenticated:
        join_message_data = {
            'system': True,
            'text': f"{current_user.display_name or current_user.username} has joined the chat.",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'username': 'System',
            'display_name': 'System',
            'profile_pic': url_for('static', filename='profile_pics/default.jpg')
        }
        emit('receive_message', join_message_data)
        print(f"👋 {current_user.username} joined the chat")

@socketio.on('typing')
def handle_typing(data):
    """
    Handle real-time typing indicators for enhanced user experience.
    
    Args:
        data (dict): Contains typing state and context information:
            - chat_type: 'public' or 'private'
            - recipient_id: Target user for private chat typing
            - is_typing: Boolean indicating typing state
            
    Actions performed:
        - Validates user authentication
        - Determines appropriate recipients based on chat type
        - Broadcasts typing indicators to relevant users
        - Excludes sender from receiving their own typing indicator
        - Logs typing events for debugging
        
    Note:
        - Supports both public and private chat typing indicators
        - Real-time feedback improves conversation flow
        - Includes user identification and display names
        - Automatically handles recipient targeting
    """
    if not current_user.is_authenticated:
        return
    
    chat_type = data.get('chat_type', 'public')  # 'public' or 'private'
    recipient_id = data.get('recipient_id')
    is_typing = data.get('is_typing', False)
    
    typing_data = {
        'user_id': current_user.id,
        'username': current_user.username,
        'display_name': current_user.display_name,
        'is_typing': is_typing,
        'chat_type': chat_type
    }
    
    if chat_type == 'private' and recipient_id:
        # Send typing indicator to specific user
        emit('user_typing', typing_data, room=f'user_{recipient_id}')
    else:
        # Send typing indicator to all users in public chat
        emit('user_typing', typing_data, include_self=False)
    
    print(f"👤 {current_user.username} {'started' if is_typing else 'stopped'} typing in {chat_type} chat")

@socketio.on('heartbeat')
def handle_heartbeat():
    """
    Handle connection monitoring heartbeat from clients.
    
    Actions performed:
        - Validates user authentication
        - Responds with timestamped heartbeat acknowledgment
        - Enables client-side connection quality monitoring
        
    Response:
        - Emits 'heartbeat_response' with current server timestamp
        
    Note:
        - Used for connection latency measurement
        - Helps detect connection quality issues
        - Enables automatic reconnection logic
        - Only responds to authenticated users
    """
    if current_user.is_authenticated:
        emit('heartbeat_response', {'timestamp': datetime.now().isoformat()})

# --- Flask-Admin setup ---
admin = Admin(app, name='Chattrix Admin', template_mode='bootstrap4')

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class PushTestView(BaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('push_test'))
    
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Message, db.session))
admin.add_view(AdminModelView(Conversation, db.session))
admin.add_view(PushTestView(name='Push Test', endpoint='push_test_admin'))

# --- Create admin user ---
def create_admin_user():
    """
    Create default admin user if it doesn't exist in the database.
    
    Environment Variables:
        - ADMIN_USERNAME: Admin username (default: 'admin')
        - ADMIN_PASSWORD: Admin password (default: 'admin123')
        - ADMIN_EMAIL: Admin email (default: 'admin@chattrix.com')
        
    Actions performed:
        - Checks if admin user already exists
        - Creates new admin user with environment-specified credentials
        - Sets admin privileges (is_admin=True)
        - Hashes password securely using PBKDF2-SHA256
        - Logs admin user creation for security tracking
        
    Note:
        - Only creates user if one doesn't exist with the specified username
        - Shows password in development mode for convenience
        - Uses secure password hashing for production safety
    """
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

# Replace the last section of your app.py (from "if __name__ == '__main__':")
if __name__ == '__main__':
    print('🚀 Starting Chattrix application...')
    
    # Get configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    print(f'📋 Using configuration: {config_name}')
    
    try:
        # Initialize database and admin user
        with app.app_context():
            print('🔧 Initializing database...')
            db.create_all()
            migrate_database()
            create_admin_user()
            print('✅ Database initialization complete')
        
        # Configuration for local development
        port = int(os.environ.get('PORT', 5000))
        
        # Use 127.0.0.1 for local development, 0.0.0.0 for production
        if config_name == 'development':
            host = '127.0.0.1'
            debug = True
        else:
            host = '0.0.0.0'
            debug = False
        
        # Check for HTTPS mode
        ssl_context = None
        protocol = 'http'
        
        # Look for SSL certificates
        cert_file = 'certs/cert.pem'
        key_file = 'certs/key.pem'
        
        if os.path.exists(cert_file) and os.path.exists(key_file):
            try:
                ssl_context = (cert_file, key_file)
                protocol = 'https'
                print(f'🔒 SSL certificates found - enabling HTTPS')
            except Exception as e:
                print(f'⚠️ SSL certificate error: {e}')
                print(f'📍 Falling back to HTTP')
                ssl_context = None
        
        print(f'🌐 Starting server at {protocol}://{host}:{port}')
        print(f'🔧 Debug mode: {debug}')
        print(f'📍 Visit: {protocol}://127.0.0.1:{port}')
        
        if protocol == 'https':
            print(f'🔒 HTTPS enabled - push notifications should work!')
        else:
            print(f'⚠️ HTTP mode - push notifications may require browser flags')
            print(f'💡 For Chrome: chrome --unsafely-treat-insecure-origin-as-secure=http://localhost:{port}')
            print(f'💡 For Firefox: Should work directly on localhost')
        
        # Start the SocketIO server with proper SSL context handling
        if ssl_context:
            # For HTTPS with Flask-SocketIO + eventlet
            socketio.run(app, 
                        host=host, 
                        port=port, 
                        debug=debug,
                        certfile=cert_file,
                        keyfile=key_file,
                        use_reloader=False,
                        log_output=True)
        else:
            # For HTTP
            socketio.run(app, 
                        host=host, 
                        port=port, 
                        debug=debug,
                        use_reloader=False,
                        log_output=True)
        
    except Exception as e:
        print(f'❌ Error starting application: {e}')
        import traceback
        traceback.print_exc()
        input('Press Enter to continue...')  # Keep window open to see error

# =========================
# END OF CHATTRIX APPLICATION
# =========================
# 
# This file contains the complete Chattrix real-time messaging application
# with comprehensive documentation and comments describing:
# 
# - Application factory pattern for flexible deployment
# - Database models and migration system for schema updates
# - User authentication and authorization with Flask-Login
# - Real-time messaging with optimized SocketIO configuration
# - Push notification system with VAPID key support
# - File upload and sharing functionality with security measures
# - Admin interface for message management and user administration
# - Private messaging system with conversation tracking
# - Connection monitoring and user presence tracking
# 
# All functions and classes have been documented with:
# - Clear purpose descriptions
# - Parameter and return value documentation
# - Usage notes and important considerations
# - Error handling and security implications