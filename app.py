"""
Chattrix Real-Time Messaging Application
Main Flask application with Socket.IO support for real-time communication.

Features:
- Real-time messaging with Socket.IO
- User authentication and profile management
- File upload capabilities
- Push notifications with VAPID
- Admin interface with Flask-Admin
- Database management with SQLAlchemy
"""

import eventlet
eventlet.monkey_patch()

# Core Flask imports
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import send, emit, join_room, leave_room, SocketIO
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

# Admin interface imports
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView

# Security and utilities
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_toastr import Toastr
from flask import flash
from sqlalchemy import text
from PIL import Image

# External services and configuration
import os
import json
from pywebpush import webpush, WebPushException
from dotenv import load_dotenv
from config import config

# Load environment variables from .env file
load_dotenv()

# --- Application Factory Pattern ---
def create_app(strConfigName=None):
    """
    Application Factory Pattern for Creating Flask App Instances
    
    Creates and configures a Flask application instance with all necessary
    extensions, database setup, and configuration management.
    
    Args:
        strConfigName (str): Configuration environment identifier
                           ('development', 'production', 'testing')
        
    Returns:
        Flask: Fully configured Flask application instance with:
               - Database integration (SQLAlchemy)
               - Real-time communication (Socket.IO)
               - Authentication system (Flask-Login)
               - Admin interface (Flask-Admin)
               - Push notification support (WebPush)
    """
    objApp = Flask(__name__)
    
    # Determine configuration environment from parameter or environment variable
    if strConfigName is None:
        strConfigName = os.environ.get('FLASK_ENV', 'development')
    
    objApp.config.from_object(config[strConfigName])
    
    # Override database URI for production environment using environment variables
    if strConfigName == 'production':
        from config import get_database_uri
        strDatabaseUri = get_database_uri()
        objApp.config['SQLALCHEMY_DATABASE_URI'] = strDatabaseUri
        
        # Add SSL configuration only for AWS RDS PostgreSQL connections
        if strDatabaseUri and 'postgresql://' in strDatabaseUri and 'amazonaws.com' in strDatabaseUri:
            objApp.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                **objApp.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}),
                'connect_args': {
                    'sslmode': 'require',
                    'connect_timeout': 10
                }
            }
    
    return objApp

# Create application instance using factory pattern
strConfigName = os.environ.get('FLASK_ENV', 'development')
objApp = create_app(strConfigName)

# Extract VAPID configuration values for push notifications
strVapidPrivateKey = objApp.config['VAPID_PRIVATE_KEY']
strVapidPublicKey = objApp.config['VAPID_PUBLIC_KEY']
dictVapidClaims = objApp.config['VAPID_CLAIMS']

# Extract upload folder configuration from application config
strProfilePicsFolder = objApp.config['PROFILE_PICS_FOLDER']
strUploadsFolder = objApp.config['UPLOADS_FOLDER']
setAllowedExtensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx', 'mp4'}

# Create upload directories if they don't exist
os.makedirs(strProfilePicsFolder, exist_ok=True)
os.makedirs(strUploadsFolder, exist_ok=True)

# Initialize database extension
objDb = SQLAlchemy(objApp)

# Configure SocketIO for optimal real-time performance
dictSocketIoKwargs = {
    'manage_session': True,
    'async_mode': 'eventlet',
    'ping_timeout': 10,
    'ping_interval': 5,
    'max_http_buffer_size': 1000000,
    'allow_upgrades': True,
    'transports': ['websocket', 'polling']
}

# Environment-specific SocketIO configuration
if strConfigName == 'production':
    dictSocketIoKwargs.update({
        'logger': True,
        'engineio_logger': True,
        'cors_allowed_origins': "*"  # Configure this properly for your domain
    })
else:
    # Development mode optimizations
    dictSocketIoKwargs.update({
        'logger': False,
        'engineio_logger': False
    })

objSocketIo = SocketIO(objApp, **dictSocketIoKwargs)

# --- Flask-Login Authentication Setup ---
objLoginManager = LoginManager(objApp)
objLoginManager.login_view = 'login'

# --- Global State Management ---
dictUserLocations = {}  # Track which page/chat each user is currently viewing

# --- Database Models with SQLAlchemy ---

class User(objDb.Model, UserMixin):
    """
    User Model for Authentication and Profile Management
    
    Handles user registration, authentication, and profile management.
    Integrates with Flask-Login for session management and supports admin privileges.
    """
    nId = objDb.Column(objDb.Integer, primary_key=True)
    strDisplayName = objDb.Column(objDb.String(50), nullable=False)
    strUsername = objDb.Column(objDb.String(80), unique=True, nullable=False)
    strPasswordHash = objDb.Column(objDb.String(255), nullable=False)  # Increased from 80 to 255 for password hashes
    bIsAdmin = objDb.Column(objDb.Boolean, default=False)
    strProfilePic = objDb.Column(objDb.String(120), default='default.jpg')
    strBio = objDb.Column(objDb.String(300), default='')

    # Flask-Login required properties
    def get_id(self):
        return str(self.nId)

class PushSubscription(objDb.Model):
    """
    Push Notification Subscription Model
    
    Stores browser push notification subscription data for WebPush delivery.
    Each user can have multiple subscriptions across different devices/browsers.
    """
    nId = objDb.Column(objDb.Integer, primary_key=True)
    nUserId = objDb.Column(objDb.Integer, objDb.ForeignKey('user.nId'), nullable=False)
    strEndpoint = objDb.Column(objDb.Text, nullable=False)
    strP256dhKey = objDb.Column(objDb.Text, nullable=False)
    strAuthKey = objDb.Column(objDb.Text, nullable=False)
    dtCreatedAt = objDb.Column(objDb.DateTime, default=datetime.utcnow)


class Message(objDb.Model):
    """
    Message Model for Public and Private Communications
    
    Handles both public chat messages and private direct messages.
    Supports file attachments, message pinning, and read status tracking.
    """
    nId = objDb.Column(objDb.Integer, primary_key=True)
    nSenderId = objDb.Column(objDb.Integer, objDb.ForeignKey('user.nId'), nullable=False)
    nRecipientId = objDb.Column(objDb.Integer, objDb.ForeignKey('user.nId'), nullable=True)  # NULL = public message
    strText = objDb.Column(objDb.Text, nullable=False)
    dtTimestamp = objDb.Column(objDb.DateTime, default=datetime.now)
    bIsPrivate = objDb.Column(objDb.Boolean, default=False)
    bPinned = objDb.Column(objDb.Boolean, default=False)
    bIsFile = objDb.Column(objDb.Boolean, default=False)
    strFilePath = objDb.Column(objDb.String(255), nullable=True)
    strOriginalFilename = objDb.Column(objDb.String(255), nullable=True)
    bRead = objDb.Column(objDb.Boolean, default=False)
    
    # Database relationships for message participants
    objSender = objDb.relationship('User', foreign_keys=[nSenderId], backref='sent_messages')
    objRecipient = objDb.relationship('User', foreign_keys=[nRecipientId], backref='received_messages')

class Conversation(objDb.Model):
    """
    Conversation Model for Private Chat Management
    
    Tracks private conversations between users, maintaining last message
    and timestamp information for conversation ordering and management.
    """
    nId = objDb.Column(objDb.Integer, primary_key=True)
    nUser1Id = objDb.Column(objDb.Integer, objDb.ForeignKey('user.nId'), nullable=False)
    nUser2Id = objDb.Column(objDb.Integer, objDb.ForeignKey('user.nId'), nullable=False)
    nLastMessageId = objDb.Column(objDb.Integer, objDb.ForeignKey('message.nId'), nullable=True)
    dtUpdatedAt = objDb.Column(objDb.DateTime, default=datetime.now)
    
    # Database relationships for conversation participants
    objUser1 = objDb.relationship('User', foreign_keys=[nUser1Id])
    objUser2 = objDb.relationship('User', foreign_keys=[nUser2Id])
    objLastMessage = objDb.relationship('Message', foreign_keys=[nLastMessageId])

@objLoginManager.user_loader
def load_user(strUserId):
    """
    User loader callback for Flask-Login.
    
    Args:
        strUserId (str): User ID from session
        
    Returns:
        User: User object if found, None otherwise
    """
    return objDb.session.get(User, int(strUserId))  # Use objDb.session.get() instead of User.query.get()

# --- Database Migration ---
def migrateDatabaseSchema():
    """
    Database Schema Migration Function
    
    Safely add missing columns to existing database tables for backward compatibility.
    
    This function checks for the existence of each column before attempting to add it,
    preventing errors when running on existing databases that may be missing newer columns.
    Handles: recipient_id, is_private, read, is_file, file_path, original_filename, pinned columns
    """
    try:
        with objApp.app_context():
            # Use objDb.session.execute instead of objDb.engine.execute
            try:
                objDb.session.execute(text("SELECT recipient_id FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN recipient_id INTEGER"))
                objDb.session.commit()
                print("Added recipient_id column")
            
            try:
                objDb.session.execute(text("SELECT is_private FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN is_private BOOLEAN DEFAULT 0"))
                objDb.session.commit()
                print("Added is_private column")
            
            try:
                objDb.session.execute(text("SELECT read FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN read BOOLEAN DEFAULT 0"))
                objDb.session.commit()
                print("Added read column")
            
            try:
                objDb.session.execute(text("SELECT is_file FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN is_file BOOLEAN DEFAULT 0"))
                objDb.session.commit()
                print("Added is_file column")
            
            try:
                objDb.session.execute(text("SELECT file_path FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN file_path VARCHAR(255)"))
                objDb.session.commit()
                print("Added file_path column")
            
            try:
                objDb.session.execute(text("SELECT original_filename FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN original_filename VARCHAR(255)"))
                objDb.session.commit()
                print("Added original_filename column")
            
            try:
                objDb.session.execute(text("SELECT pinned FROM message LIMIT 1"))
            except:
                objDb.session.execute(text("ALTER TABLE message ADD COLUMN pinned BOOLEAN DEFAULT 0"))
                objDb.session.commit()
                print("Added pinned column")
            
            # Check if push_subscription table exists
            try:
                objDb.session.execute(text("SELECT 1 FROM push_subscription LIMIT 1"))
                print("PushSubscription table exists")
            except:
                print("Creating PushSubscription table...")
                objDb.create_all()
                print("PushSubscription table created")
                
    except Exception as objError:
        print(f"Migration error: {objError}")

# --- Create tables and migrate ---
with objApp.app_context():
    objDb.create_all()
    migrateDatabaseSchema()

# --- SocketIO session/user mapping ---
dictUserSidMap = {}
dictOnlineUsers = {}

# --- Helper Functions ---

@objApp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    """
    Push Notification Subscription Handler
    
    Handles push notification subscription requests from authenticated users.
    Removes existing subscriptions and creates new ones to prevent duplicates.
    
    Returns:
        JSON: Success/error response with subscription status
    """
    try:
        objSubscriptionData = request.get_json()
        
        if not objSubscriptionData or 'endpoint' not in objSubscriptionData:
            return jsonify({'success': False, 'error': 'Invalid subscription data'}), 400
        
        # Remove existing subscriptions for this user
        PushSubscription.query.filter_by(nUserId=current_user.nId).delete()
        
        # Add new subscription
        objSubscription = PushSubscription(
            nUserId=current_user.nId,
            strEndpoint=objSubscriptionData['endpoint'],
            strP256dhKey=objSubscriptionData['keys']['p256dh'],
            strAuthKey=objSubscriptionData['keys']['auth']
        )
        
        objDb.session.add(objSubscription)
        objDb.session.commit()
        
        print(f"✅ Push subscription saved for user {current_user.nId}")
        return jsonify({'success': True})
        
    except Exception as objError:
        print(f"❌ Error saving push subscription: {objError}")
        objDb.session.rollback()
        return jsonify({'success': False, 'error': str(objError)}), 500

@objApp.route('/vapid-public-key')
def getVapidPublicKey():
    """
    VAPID Public Key API Endpoint
    
    API endpoint to provide VAPID public key for push notification setup.
    
    Returns:
        JSON: Contains the VAPID public key needed by frontend for push subscriptions
    """
    return jsonify({'publicKey': strVapidPublicKey})

@objApp.route('/subscribe-push', methods=['POST'])
@login_required
def subscribePush():
    """
    Push Notification Subscription Handler
    
    Subscribe a user to push notifications.
    Expects JSON with 'subscription' containing push subscription data.
    
    Returns:
        JSON: Success/error response with subscription details
    """
    try:
        objData = request.get_json()
        objSubscriptionData = objData.get('subscription')
        
        if not objSubscriptionData:
            return jsonify({'error': 'No subscription data provided'}), 400
        
        # Remove any existing subscription for this user
        PushSubscription.query.filter_by(nUserId=current_user.nId).delete()
        
        # Create new subscription
        objSubscription = PushSubscription(
            nUserId=current_user.nId,
            strEndpoint=objSubscriptionData['endpoint'],
            strP256dhKey=objSubscriptionData['keys']['p256dh'],
            strAuthKey=objSubscriptionData['keys']['auth']
        )
        
        objDb.session.add(objSubscription)
        objDb.session.commit()
        
        print(f"✅ Push subscription saved for user {current_user.nId}")
        print(f"📤 Endpoint: {objSubscriptionData['endpoint'][:100]}...")
        
        return jsonify({'success': True, 'message': 'Push subscription saved'})
        
    except Exception as objError:
        print(f"❌ Error saving push subscription: {objError}")
        return jsonify({'error': str(objError)}), 500

@objApp.route('/test-push/<int:nUserId>')
@login_required
def testPushNotification(nUserId):
    """
    Push Notification Test Endpoint (Admin Only)
    
    Admin-only endpoint for testing push notifications to a specific user.
    
    Args:
        nUserId (int): Target user ID for the test notification
        
    Returns:
        JSON: Success/failure status of the test notification
    """
    if current_user.bIsAdmin:
        send_web_push(
            nUserId,
            "Test Notification",
            "This is a test push notification from Chattrix!",
            "/chat"
        )
        return jsonify({'success': True, 'message': f'Test notification sent to user {nUserId}'})
    else:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

@objApp.route('/register-fallback-notifications', methods=['POST'])
@login_required
def registerFallbackNotifications():
    """
    Fallback Browser Notification Registration
    
    Register user for fallback browser notifications (for localhost testing).
    Used when service workers are not available or supported.
    
    Returns:
        JSON: Registration status and user configuration
    """
    try:
        objData = request.get_json()
        nUserId = current_user.nId
        
        # For now, just log that the user wants notifications
        # In a real app, you'd store this preference in the database
        print(f"✅ User {nUserId} registered for fallback notifications")
        
        return jsonify({'success': True, 'message': 'Registered for notifications'})
        
    except Exception as objError:
        print(f"❌ Error registering fallback notifications: {objError}")
        return jsonify({'error': str(objError)}), 500

@objApp.route('/test-browser-notification/<int:nUserId>')
@login_required
def testBrowserNotification(nUserId):
    """
    Browser Notification Test Endpoint
    
    Test browser notification endpoint (doesn't require push subscription).
    Sends Socket.IO events to trigger browser notifications for testing.
    
    Args:
        nUserId (int): Target user ID for the test notification
        
    Returns:
        JSON: Test notification success/failure status
    """
    if current_user.bIsAdmin or current_user.nId == nUserId:
        # Send a socket event that will trigger browser notification
        objSocketIo.emit('browser_notification', {
            'title': 'Test Browser Notification',
            'message': 'This is a test browser notification from Chattrix!',
            'type': 'test'
        }, room=f'user_{nUserId}')
        
        print(f"📤 Browser notification test sent to user {nUserId}")
        return jsonify({'success': True, 'message': f'Test browser notification sent to user {nUserId}'})
    else:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

@objApp.route('/push-test')
def pushTestPage():
    """
    Debug page for testing push notifications
    """
    return render_template('push_test.html')


def send_web_push(nUserId, strTitle, strBody, strUrl='/chat'):
    """
    Web Push Notification Sender Function
    
    Send web push notifications to all subscribed devices for a specific user.
    
    Args:
        nUserId (int): Target user ID for the notification
        strTitle (str): Notification title text
        strBody (str): Notification body/message text
        strUrl (str): URL to navigate to when notification is clicked (default: '/chat')
        
    Note:
        - Automatically removes expired subscriptions (410 responses)
        - Handles WebPush exceptions gracefully
        - Logs success/failure for debugging
    """
    try:
        arrSubscriptions = PushSubscription.query.filter_by(nUserId=nUserId).all()
        
        if not arrSubscriptions:
            print(f"⚠️ No push subscriptions found for user {nUserId}")
            return
        
        print(f"📤 Sending push notification to {len(arrSubscriptions)} subscription(s) for user {nUserId}")
        
        for objSubscription in arrSubscriptions:
            try:
                dictPayload = json.dumps({
                    "title": strTitle,
                    "body": strBody,
                    "url": strUrl,
                    "icon": "/static/profile_pics/default.jpg",
                    "badge": "/static/profile_pics/default.jpg"
                })
                
                webpush(
                    subscription_info={
                        "endpoint": objSubscription.strEndpoint,
                        "keys": {
                            "p256dh": objSubscription.strP256dhKey,
                            "auth": objSubscription.strAuthKey
                        }
                    },
                    data=dictPayload,
                    vapid_private_key=strVapidPrivateKey,
                    vapid_claims=dictVapidClaims
                )
                print(f"✅ Push notification sent successfully to user {nUserId}")
                
            except WebPushException as objWebPushError:
                print(f"❌ WebPush error for user {nUserId}: {objWebPushError}")
                if objWebPushError.response and objWebPushError.response.status_code == 410:
                    # Subscription expired, remove it
                    print(f"🗑️ Removing expired subscription for user {nUserId}")
                    objDb.session.delete(objSubscription)
                    objDb.session.commit()
            except Exception as objError:
                print(f"❌ Unexpected error sending push notification: {objError}")
                
    except Exception as objError:
        print(f"❌ Error in send_web_push function: {objError}")

def isAllowedFile(strFilename):
    """
    File Extension Validation Function
    
    Check if uploaded file has an allowed extension for security.
    
    Args:
        strFilename (str): Name of the uploaded file
        
    Returns:
        bool: True if file extension is in setAllowedExtensions, False otherwise
    """
    return '.' in strFilename and strFilename.rsplit('.', 1)[1].lower() in setAllowedExtensions

def resizeProfilePicture(strFilepath, tplMaxSize=(200, 200)):
    """
    Profile Picture Resize and Optimization Function
    
    Resize and optimize profile picture for consistent display and performance.
    
    Args:
        strFilepath (str): Path to the uploaded image file
        tplMaxSize (tuple): Maximum dimensions (width, height)
        
    Note:
        - Maintains aspect ratio during resize
        - Optimizes file size for web performance
        - Handles various image formats
    """
    try:
        with Image.open(strFilepath) as objImg:
            # Convert to RGB if necessary (handles RGBA, P mode images)
            if objImg.mode in ('RGBA', 'P'):
                objRgbImg = Image.new('RGB', objImg.size, (255, 255, 255))
                objRgbImg.paste(objImg, mask=objImg.split()[-1] if objImg.mode == 'RGBA' else None)
                objImg = objRgbImg
            
            # Resize maintaining aspect ratio
            objImg.thumbnail(tplMaxSize, Image.Resampling.LANCZOS)
            
            # Save optimized image
            objImg.save(strFilepath, 'JPEG', quality=85, optimize=True)
    except Exception as objError:
        print(f"Error resizing profile picture: {objError}")
        # If resize fails, keep original file

def getOrCreateConversation(nUser1Id, nUser2Id):
    """
    Private Conversation Management Function
    
    Find existing private conversation between two users or create a new one.
    
    Args:
        nUser1Id (int): First user's ID
        nUser2Id (int): Second user's ID
        
    Returns:
        Conversation: Existing or newly created conversation object
        
    Note:
        - Automatically orders user IDs (lower ID as user1, higher as user2)
        - Creates conversation in database if it doesn't exist
        - Updates timestamp when conversation is accessed
    """
    objConversation = Conversation.query.filter(
        ((Conversation.nUser1Id == nUser1Id) & (Conversation.nUser2Id == nUser2Id)) |
        ((Conversation.nUser1Id == nUser2Id) & (Conversation.nUser2Id == nUser1Id))
    ).first()
    
    if not objConversation:
        objConversation = Conversation(
            nUser1Id=min(nUser1Id, nUser2Id),
            nUser2Id=max(nUser1Id, nUser2Id),
            dtUpdatedAt=datetime.now()
        )
        objDb.session.add(objConversation)
        objDb.session.commit()
    
    return objConversation

# --- Routes ---

@objApp.route('/')
@login_required
def indexPage():
    """
    Application Home Page Route
    
    Main public chat page route serving as the primary interface.
    
    Returns:
        Template: Renders the main chat interface (chat.html)
        
    Note:
        - Requires user authentication
        - Serves as the primary chat room for all users
    """
    return render_template('chat.html')

@objApp.route('/register', methods=['GET', 'POST'])
def registerPage():
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
        strDisplayName = request.form['display_name']
        strUsername = request.form['username']
        strPassword = request.form['password']
        if User.query.filter_by(strUsername=strUsername).first():
            flash("Username already taken.", "error")
        else:
            strHashedPassword = generate_password_hash(strPassword, method='pbkdf2:sha256')
            objUser = User(strDisplayName=strDisplayName, strUsername=strUsername, strPasswordHash=strHashedPassword)
            objDb.session.add(objUser)
            objDb.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('loginPage'))
    return render_template('register.html')

@objApp.route('/login', methods=['GET', 'POST'])
def loginPage():
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
            return redirect(url_for('indexPage'))
    return render_template('login.html')

@objApp.route('/logout')
@login_required
def logoutPage():
    """
    User Logout Route Handler
    
    User logout route that ends the current session.
    
    Returns:
        Redirect: Redirects to login page after logout
        
    Note:
        - Requires user to be logged in
        - Clears user session using Flask-Login
    """
    logout_user()
    return redirect(url_for('loginPage'))

@objApp.route('/profile', methods=['GET', 'POST'])
@login_required
def profilePage():
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
            objFile = request.files['profile_pic']
            if objFile and objFile.filename and isAllowedFile(objFile.filename):
                # Generate secure filename with user ID
                strFileExt = objFile.filename.rsplit('.', 1)[1].lower()
                strFilename = secure_filename(f"{current_user.nId}_profile.jpg")  # Always save as jpg after processing
                strFilepath = os.path.join(objApp.config['PROFILE_PICS_FOLDER'], strFilename)
                
                # Save original file temporarily
                strTempPath = strFilepath + '.temp'
                objFile.save(strTempPath)
                
                # Resize and optimize the image
                resizeProfilePicture(strTempPath, tplMaxSize=(200, 200))
                
                # Move processed file to final location
                os.rename(strTempPath, strFilepath)
                
                current_user.strProfilePic = strFilename

        objDb.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profilePage'))

    return render_template('profile.html', objUser=current_user)

# --- Private Messaging Routes ---

@objApp.route('/conversations')
@login_required
def conversationsPage():
    """
    Display all private conversations for the current user.
    
    Returns:
        Template: Conversations list page with all user's private chats
        
    Note:
        - Shows conversations ordered by most recent activity
        - Includes conversations where user is either participant
        - Requires user authentication
    """
    arrConversations = objDb.session.query(Conversation).filter(
        (Conversation.nUser1Id == current_user.nId) | 
        (Conversation.nUser2Id == current_user.nId)
    ).order_by(Conversation.dtUpdatedAt.desc()).all()
    
    return render_template('conversations.html', arrConversations=arrConversations)

@objApp.route('/chat/<int:nUserId>')
@login_required 
def privateChatPage(nUserId):
    """
    Private Chat Interface Route
    
    Private chat interface between current user and specified user.
    
    Args:
        nUserId (int): ID of the other user to chat with
        
    Returns:
        Template: Private chat page with conversation history
        Template: Private chat interface with message history
        Redirect: To conversations page if trying to chat with self
        
    Note:
        - Prevents users from chatting with themselves
        - Creates conversation record if it doesn't exist
        - Automatically marks incoming messages as read
        - Loads complete message history between the two users
    """
    objOtherUser = User.query.get_or_404(nUserId)
    
    if objOtherUser.nId == current_user.nId:
        flash("You can't chat with yourself!", "error")
        return redirect(url_for('conversationsPage'))
    
    # Get or create conversation
    objConversation = getOrCreateConversation(current_user.nId, nUserId)
    
    # Get messages for this conversation
    arrMessages = Message.query.filter(
        ((Message.nSenderId == current_user.nId) & (Message.nRecipientId == nUserId)) |
        ((Message.nSenderId == nUserId) & (Message.nRecipientId == current_user.nId))
    ).order_by(Message.dtTimestamp.asc()).all()
    
    # Mark messages as read
    Message.query.filter(
        (Message.nSenderId == nUserId) & 
        (Message.nRecipientId == current_user.nId) &
        (Message.bRead == False)
    ).update({'bRead': True})
    objDb.session.commit()
    
    return render_template('private_chat.html', objOtherUser=objOtherUser, arrMessages=arrMessages)

@objApp.route('/users')
@login_required
def userListPage():
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

@objApp.route('/upload', methods=['POST'])
@login_required
def uploadFilePage():
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
    
    if not (file and isAllowedFile(file.filename)):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        recipient_id = request.form.get('recipient_id')  # For private file sharing
        filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(objApp.config['UPLOADS_FOLDER'], filename)
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
        objDb.session.add(file_message)
        objDb.session.commit()
        
        # Update conversation if private file
        if recipient_id:
            conversation = getOrCreateConversation(current_user.id, int(recipient_id))
            conversation.last_message_id = file_message.id
            conversation.updated_at = datetime.now()
            objDb.session.commit()
            
            # Send to specific users only
            objSocketIo.emit('receive_message', {
                'id': file_message.id,
                'display_name': current_user.display_name,
                'text': file_message.text,
                'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_private': True,
                'sender_id': current_user.id,
                'profile_pic': current_user.profile_pic or 'default.jpg'
            }, room=f"user_{recipient_id}")
            
            objSocketIo.emit('receive_message', {
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
            objSocketIo.emit('receive_message', {
                'id': file_message.id,
                'display_name': current_user.display_name,
                'text': file_message.text,
                'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_private': False,
                'sender_id': current_user.id,
                'profile_pic': current_user.profile_pic or 'default.jpg'
            })
        
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as objError:
        return jsonify({'error': f'Upload failed: {str(objError)}'}), 500

@objApp.route('/static/uploads/<strFilename>')
def uploadedFilePage(strFilename):
    """
    File Serving Route for Uploads
    
    Serve uploaded files from the uploads directory.
    
    Args:
        strFilename (str): Name of the file to serve
        
    Returns:
        File: The requested file or 404 if not found
    """
    return send_from_directory(objApp.config['UPLOADS_FOLDER'], strFilename)

@objApp.route('/static/profile_pics/<strFilename>')  
def profilePicturePage(strFilename):
    """
    Profile Picture Serving Route
    
    Serve profile pictures from the profile pics directory.
    
    Args:
        strFilename (str): Name of the profile picture to serve
        
    Returns:
        File: The requested profile picture or 404 if not found
    """
    return send_from_directory(objApp.config['PROFILE_PICS_FOLDER'], strFilename)

@objApp.route('/test-upload')
def testUploadPage():
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

@objApp.route('/messages')
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

@objApp.route('/pinned_messages')
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

@objSocketIo.on('connect')
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
        dictOnlineUsers[current_user.id] = {
            'id': current_user.id,
            'username': current_user.username,
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic if (current_user.profile_pic and current_user.profile_pic != 'default.jpg') else None
        }
        
        # Join user to their personal room
        join_room(f'user_{current_user.id}')
        
        # Broadcast updated online users list
        emit('online_users', list(dictOnlineUsers.values()))
        
        print(f"✅ User {current_user.username} connected - {len(dictOnlineUsers)} users online")

@objSocketIo.on('disconnect')
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
        if current_user.id in dictOnlineUsers:
            del dictOnlineUsers[current_user.id]
        
        # Leave user's personal room
        leave_room(f'user_{current_user.id}')
        
        # Broadcast updated online users list
        emit('online_users', list(dictOnlineUsers.values()))
        
        print(f"❌ User {current_user.username} disconnected - {len(dictOnlineUsers)} users online")

@objSocketIo.on('user_location')
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
    dictUserLocations[current_user.id] = location
    print(f"📍 User {current_user.id} ({current_user.username}) is now on: {location}")

@objSocketIo.on('join_user_room')
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
        dictOnlineUsers[current_user.id] = {
            'id': current_user.id,
            'username': current_user.username,
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic if (current_user.profile_pic and current_user.profile_pic != 'default.jpg') else None
        }
        
        # Send updated online users list
        emit('online_users', list(dictOnlineUsers.values()))
        print(f"👥 {current_user.username} joined user room - Broadcasting online users")

@objSocketIo.on('join_private_room')
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

@objSocketIo.on('get_online_users')
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
        emit('online_users', list(dictOnlineUsers.values()))
        print(f"📊 Sent online users list to {current_user.username}: {len(dictOnlineUsers)} users")

# Update your handle_private_message function in app.py
@objSocketIo.on('private_message')
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
    
    objDb.session.add(message)
    objDb.session.commit()
    
    # Update conversation
    conversation = getOrCreateConversation(current_user.id, recipient_id)
    conversation.last_message_id = message.id
    conversation.updated_at = datetime.now()
    objDb.session.commit()
    
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
    
    # Send browser notification to recipient
    emit('notification', {
        'type': 'private_message',
        'title': f'Message from {current_user.display_name or current_user.username}',
        'message': message_text[:100] + ("..." if len(message_text) > 100 else ""),
        'sender': current_user.display_name or current_user.username,
        'chat_url': f'/chat/{current_user.id}',
        'sender_id': current_user.id
    }, room=f'user_{recipient_id}')
    
    # Send web push notification to recipient
    send_web_push(
        recipient_id,
        f"Message from {current_user.display_name or current_user.username}",
        message_text[:100] + ("..." if len(message_text) > 100 else ""),
        f"/chat/{current_user.id}"
    )
    
    print(f"💬 Private message sent from {current_user.username} to {recipient.username}")

# Replace your existing send_message handler with this one:
@objSocketIo.on('send_message')
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
    objDb.session.add(message)
    objDb.session.commit()
    
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
    for user_id, location in dictUserLocations.items():
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
@objSocketIo.on('send_private_message')
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
    
    objDb.session.add(private_message)
    objDb.session.commit()
    
    # Update conversation
    conversation = getOrCreateConversation(current_user.id, recipient_id)
    conversation.last_message_id = private_message.id
    conversation.updated_at = datetime.now()
    objDb.session.commit()
    
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
    
    # Send browser notification to recipient
    emit('notification', {
        'type': 'private_message',
        'title': f'Message from {current_user.display_name or current_user.username}',
        'message': message_text[:100] + ("..." if len(message_text) > 100 else ""),
        'sender': current_user.display_name or current_user.username,
        'chat_url': f'/chat/{current_user.id}',
        'sender_id': current_user.id
    }, room=f'user_{recipient_id}')
    
    # Send push notification to recipient
    send_web_push(
        recipient_id, 
        f"Message from {current_user.display_name or current_user.username}", 
        message_text[:100] + ("..." if len(message_text) > 100 else ""),
        f"/chat/{current_user.id}"
    )
    
    print(f"📤 Private message sent from {current_user.id} to {recipient_id}")

# Also add these alternative handlers in case your frontend uses different event names:
@objSocketIo.on('message')
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

@objSocketIo.on('new_message')  
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

@objSocketIo.on('send_public_message')
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
@objSocketIo.on('pin_message')
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
        
    objMsg = objDb.session.get(Message, message_id)
    if objMsg and not objMsg.is_private:  # Only pin public messages
        objMsg.pinned = True
        objDb.session.commit()
        emit('update_pinned', {'message_id': message_id})
        print(f"📌 Admin {current_user.id} pinned message {message_id}")
        emit('success', {'message': 'Message pinned successfully'})
    else:
        emit('error', {'message': 'Message not found or is private'})

@objSocketIo.on('unpin_message')
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
    objMessage = objDb.session.get(Message, message_id)
    if objMessage:
        objMessage.pinned = False
        objDb.session.commit()
        
        emit('update_unpinned', {'message_id': message_id})
        
        print(f"📌 Admin {current_user.id} unpinned message {message_id}")
        emit('success', {'message': 'Message unpinned successfully'})
    else:
        emit('error', {'message': 'Message not found'})

@objSocketIo.on('user_joined')
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

@objSocketIo.on('typing')
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

@objSocketIo.on('heartbeat')
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
objAdmin = Admin(objApp, name='Chattrix Admin', template_mode='bootstrap4')

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

objAdmin.add_view(AdminModelView(User, objDb.session))
objAdmin.add_view(AdminModelView(Message, objDb.session))
objAdmin.add_view(AdminModelView(Conversation, objDb.session))
objAdmin.add_view(PushTestView(name='Push Test', endpoint='push_test_admin'))

# --- Create admin user ---
def createAdminUser():
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
    strAdminUsername = os.environ.get('ADMIN_USERNAME', 'admin')
    strAdminPassword = os.environ.get('ADMIN_PASSWORD', 'admin123')
    strAdminEmail = os.environ.get('ADMIN_EMAIL', 'admin@chattrix.com')
    
    if not User.query.filter_by(strUsername=strAdminUsername).first():
        objAdminUser = User(
            strDisplayName="Administrator",
            strUsername=strAdminUsername,
            strPasswordHash=generate_password_hash(strAdminPassword, method='pbkdf2:sha256'),
            bIsAdmin=True
        )
        objDb.session.add(objAdminUser)
        objDb.session.commit()
        print(f"Admin user created: username='{strAdminUsername}'")
        if strConfigName == 'development':
            print(f"Password: '{strAdminPassword}'")

# Initialize database and admin user
with objApp.app_context():
    objDb.create_all()
    migrateDatabaseSchema()
    createAdminUser()

# Replace the last section of your app.py (from "if __name__ == '__main__':")
if __name__ == '__main__':
    print('🚀 Starting Chattrix application...')
    
    # Get configuration
    strConfigName = os.environ.get('FLASK_ENV', 'development')
    print(f'📋 Using configuration: {strConfigName}')
    
    try:
        # Initialize database and admin user
        with objApp.app_context():
            print('🔧 Initializing database...')
            objDb.create_all()
            migrateDatabaseSchema()
            createAdminUser()
            print('✅ Database initialization complete')
        
        # Configuration for local development
        nPort = int(os.environ.get('PORT', 5000))
        
        # Use 127.0.0.1 for local development, 0.0.0.0 for production
        if strConfigName == 'development':
            strHost = '127.0.0.1'
            bDebug = True
        else:
            strHost = '0.0.0.0'
            bDebug = False
        
        # Check for HTTPS mode
        objSslContext = None
        strProtocol = 'http'
        
        # Look for SSL certificates
        strCertFile = 'certs/cert.pem'
        strKeyFile = 'certs/key.pem'
        
        if os.path.exists(strCertFile) and os.path.exists(strKeyFile):
            try:
                objSslContext = (strCertFile, strKeyFile)
                strProtocol = 'https'
                print(f'🔒 SSL certificates found - enabling HTTPS')
            except Exception as e:
                print(f'⚠️ SSL certificate error: {e}')
                print(f'📍 Falling back to HTTP')
                objSslContext = None
        
        print(f'🌐 Starting server at {strProtocol}://{strHost}:{nPort}')
        print(f'🔧 Debug mode: {bDebug}')
        print(f'📍 Visit: {strProtocol}://127.0.0.1:{nPort}')
        
        if strProtocol == 'https':
            print(f'🔒 HTTPS enabled - push notifications should work!')
        else:
            print(f'⚠️ HTTP mode - push notifications may require browser flags')
            print(f'💡 For Chrome: chrome --unsafely-treat-insecure-origin-as-secure=http://localhost:{nPort}')
            print(f'💡 For Firefox: Should work directly on localhost')
        
        # Start the SocketIO server with proper SSL context handling
        if objSslContext:
            # For HTTPS with Flask-SocketIO + eventlet
            objSocketIo.run(objApp, 
                        host=strHost, 
                        port=nPort, 
                        debug=bDebug,
                        certfile=strCertFile,
                        keyfile=strKeyFile,
                        use_reloader=False,
                        log_output=True)
        else:
            # For HTTP
            objSocketIo.run(objApp, 
                        host=strHost, 
                        port=nPort, 
                        debug=bDebug,
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