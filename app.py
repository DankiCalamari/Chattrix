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


# --- Flask app setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

# Fix upload folder configuration
PROFILE_PICS_FOLDER = os.path.join('static', 'profile_pics')
UPLOADS_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx', 'mp4'}

app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER
app.config['UPLOADS_FOLDER'] = UPLOADS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directories
os.makedirs(PROFILE_PICS_FOLDER, exist_ok=True)
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
socketio = SocketIO(app, manage_session=True)

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
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(120), default='default.jpg')
    bio = db.Column(db.String(300), default='')

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
    """Return all public messages."""
    messages = Message.query.filter_by(is_private=False).order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        pic = msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else 'default.jpg'
        result.append({
            'id': msg.id,
            'display_name': msg.sender.display_name if msg.sender else 'System',
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_private': False,
            'sender_id': msg.sender_id,
            'profile_pic': pic
        })
    return jsonify(result)

@app.route('/pinned_messages')
@login_required
def get_pinned_messages():
    """Return all pinned messages."""
    pinned = Message.query.filter_by(pinned=True, is_private=False).order_by(Message.timestamp.desc()).all()
    result = []
    for msg in pinned:
        pic = msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else 'default.jpg'
        result.append({
            'id': msg.id,
            'display_name': msg.sender.display_name if msg.sender else 'System',
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'pinned': True,
            'profile_pic': pic
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
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic or 'default.jpg'
        }
        # Initialize user location
        user_locations[current_user.id] = 'unknown'
        emit('online_users', list(online_users.values()), broadcast=True)
        print(f'User {current_user.id} connected')

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
        print(f'User {current_user.id} disconnected')

@socketio.on('user_location')
def handle_user_location(data):
    """Track which page/chat the user is currently on"""
    location = data.get('location')
    user_locations[current_user.id] = location
    print(f"User {current_user.id} is now on: {location}")

@socketio.on('join_user_room')
def handle_join_user_room():
    """Join user to their personal notification room"""
    room = f'user_{current_user.id}'
    join_room(room)
    print(f"User {current_user.id} joined notification room: {room}")

@socketio.on('join_private_room')
def handle_join_private_room(data):
    user1_id = data['user1_id']
    user2_id = data['user2_id']
    room = f"private_{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
    join_room(room)
    print(f"User {current_user.id} joined private room: {room}")

@socketio.on('private_message')
def handle_private_message(data):
    recipient_id = data['recipient_id']
    message_content = data['message']
    
    # Save message to database using the Message model (not PrivateMessage)
    private_message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        text=message_content,  # Use 'text' field, not 'content'
        timestamp=datetime.now(),  # Use datetime.now(), not datetime.utcnow()
        is_private=True
    )
    db.session.add(private_message)
    db.session.commit()
    
    # Update conversation
    conversation = get_or_create_conversation(current_user.id, recipient_id)
    conversation.last_message_id = private_message.id
    conversation.updated_at = datetime.now()
    db.session.commit()
    
    # Create room name (consistent ordering)
    room = f"private_{min(current_user.id, recipient_id)}_{max(current_user.id, recipient_id)}"
    
    # Emit to the private room
    emit('private_message', {
        'message': message_content,
        'sender_id': current_user.id,
        'recipient_id': recipient_id,
        'timestamp': private_message.timestamp.isoformat(),
        'sender_name': current_user.display_name or current_user.username
    }, room=room)
    
    # Check if recipient is in this private chat
    recipient_location = user_locations.get(recipient_id, 'unknown')
    private_chat_location = f"private_chat_{current_user.id}"
    
    # Send notification if recipient is not in this private chat
    if recipient_location != private_chat_location:
        emit('notification', {
            'type': 'private_message',
            'title': 'New private message',
            'message': f'{current_user.display_name or current_user.username}: {message_content[:50]}...',
            'sender': current_user.display_name or current_user.username,
            'sender_id': current_user.id,
            'chat_url': url_for('private_chat', user_id=current_user.id)
        }, room=f'user_{recipient_id}')
    
    print(f"Private message sent from {current_user.id} to {recipient_id} in room {room}")

# Replace your existing send_message handler with this one:
@socketio.on('send_message')
def handle_send_message(data):
    """Handle public messages - this is the main handler for public chat"""
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
    
    # Prepare message data
    message_data = {
        'id': message.id,
        'display_name': current_user.display_name,
        'username': current_user.username,
        'text': message.text,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_private': False,
        'sender_id': current_user.id,
        'profile_pic': current_user.profile_pic or 'default.jpg'
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
    
    print(f"Public message sent by {current_user.id}: {text}")

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
    if current_user.is_authenticated and current_user.is_admin:
        # FIX: Use db.session.get() instead of Message.query.get()
        msg = db.session.get(Message, data['message_id'])
        if msg and not msg.is_private:  # Only pin public messages
            msg.pinned = True
            db.session.commit()
            # FIX: Use emit() without socketio prefix
            emit('update_pinned', broadcast=True)

@socketio.on('unpin_message')
def handle_unpin_message(data):
    """Handle unpinning a message"""
    if not current_user.is_admin:
        return {'success': False, 'message': 'Admin access required'}
    
    message_id = data.get('message_id')
    if not message_id:
        return {'success': False, 'message': 'Message ID required'}
    
    # Find and unpin the message - FIX: Use db.session.get() instead of Message.query.get()
    message = db.session.get(Message, message_id)
    if message:
        message.pinned = False  # FIX: Use 'pinned' not 'is_pinned'
        db.session.commit()
        
        # FIX: Use emit() without socketio prefix and without broadcast parameter
        emit('update_unpinned', broadcast=True)
        
        print(f"Admin {current_user.id} unpinned message {message_id}")
        return {'success': True}
    else:
        return {'success': False, 'message': 'Message not found'}

@socketio.on('user_joined')
def handle_user_joined():
    """Broadcast a system message when a user joins."""
    if current_user.is_authenticated:
        emit('new_message', {
            'system': True,
            'text': f"{current_user.display_name} has joined the chat.",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

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
with app.app_context():
    admin_username = "admin"
    admin_password = "admin123"
    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(
            display_name="Administrator",
            username=admin_username,
            password=generate_password_hash(admin_password, method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username='admin', password='admin123'")

# --- Run the app ---
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)