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
from werkzeug.utils import secure_filename

# --- Flask app setup ---
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

# --- User model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(120), default='default.jpg')
    bio = db.Column(db.String(300), default='')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- SocketIO session/user mapping ---
user_sid_map = {}      # Maps user id to SocketIO session id
online_users = {}      # Maps user id to user details

# --- SocketIO event handlers ---

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle user connection and broadcast online users."""
    if current_user.is_authenticated:
        user_sid_map[current_user.id] = request.sid
        online_users[current_user.id] = {
            'display_name': current_user.display_name,
            'profile_pic': current_user.profile_pic or 'default.png'
        }
        emit('online_users', list(online_users.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection and broadcast online users."""
    if current_user.is_authenticated:
        user_sid_map.pop(current_user.id, None)
        online_users.pop(current_user.id, None)
        emit('online_users', list(online_users.values()), broadcast=True)

# --- Message model ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    whisper = db.Column(db.Boolean, default=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    pinned = db.Column(db.Boolean, default=False)  # Add this line
    is_file = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_whispers')



# --- Create tables ---
with app.app_context():
    db.create_all()

# --- Profile page ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Allow user to update display name, password, and profile picture."""
    if request.method == 'POST':
        bio = request.form.get('bio')
        display_name = request.form.get('display_name')
        password = request.form.get('password')
        
        # Change display name
        if display_name:
            current_user.display_name = display_name

        # Change password
        if password:
            current_user.password = generate_password_hash(password, method='pbkdf2:sha256')
        
        if bio is not None:
            current_user.bio = bio
            
        # Change profile picture
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOADS_FOLDER'], filename)
        file.save(filepath)
        
        # Save file message to database
        file_message = Message(
            sender_id=current_user.id,
            text=f"[FILE:{filename}:{file.filename}]",
            timestamp=datetime.now(),
            whisper=False,
            is_file=True,
            file_path=filepath,
            original_filename=file.filename
        )
        db.session.add(file_message)
        db.session.commit()
        
        # Emit to all users
        socketio.emit('receive_message', {
            'id': file_message.id,
            'display_name': current_user.display_name,
            'text': file_message.text,
            'timestamp': file_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'whisper': False,
            'profile_pic': current_user.profile_pic or 'default.png'
        })
        
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# --- Flask-Admin setup ---
admin = Admin(app, name='Chattrix Admin', template_mode='bootstrap4')

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Message, db.session))

# --- Pin/unpin message events ---
@socketio.on('pin_message')
def handle_pin_message(data):
    """Allow admin to pin a message."""
    if current_user.is_authenticated and current_user.is_admin:
        msg = Message.query.get(data['message_id'])
        if msg:
            msg.pinned = True
            db.session.commit()
            socketio.emit('update_pinned')

@socketio.on('unpin_message')
def handle_unpin_message(data):
    """Allow admin to unpin a message."""
    if current_user.is_authenticated and current_user.is_admin:
        msg = Message.query.get(data['message_id'])
        if msg:
            msg.pinned = False
            db.session.commit()
            socketio.emit('update_pinned')

# --- Whisper (private message) event ---
@socketio.on('whisper')
def handle_whisper(data):
    """Handle sending a private message (whisper) to another user."""
    if current_user.is_authenticated:
        to_user = User.query.filter_by(username=data['to']).first()
        if to_user and to_user.id in user_sid_map:
            msg = Message(
                text=data['text'],
                sender=current_user,
                whisper=True,
                to_user=to_user
            )
            db.session.add(msg)
            db.session.commit()
            # Send to recipient
            emit('whisper', {
                'display_name': current_user.display_name,
                'text': data['text'],
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'to': to_user.display_name,
                'profile_pic': current_user.profile_pic or 'default.png'
            }, room=user_sid_map[to_user.id])
            # Send to sender
            emit('whisper', {
                'display_name': f"You (to {to_user.display_name})",
                'text': data['text'],
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'to': to_user.display_name,
                'profile_pic': current_user.profile_pic or 'default.png'
            }, room=request.sid)

# --- Chat page ---
@app.route('/')
@login_required
def index():
    """Main chat page."""
    return render_template('chat.html')

# --- User registration ---
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

# --- User login ---
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
# --- User logout ---
@app.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for('login'))

# --- Handle sending a public message ---
@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a public message."""
    if current_user.is_authenticated:
        msg = Message(text=data['text'], sender=current_user)
        db.session.add(msg)
        db.session.commit()
        emit('new_message', {
            'display_name': current_user.display_name,
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'profile_pic': current_user.profile_pic or 'default.png'
        }, broadcast=True)

# --- Get all messages (public and whispers relevant to user) ---
@app.route('/messages')
@login_required
def get_messages():
    """Return all messages (public and whispers relevant to user)."""
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        pic = msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else 'default.png'
        if msg.whisper:
            if msg.sender_id == current_user.id or msg.to_user_id == current_user.id:
                result.append({
                    'id': msg.id,
                    'display_name': msg.sender.display_name if msg.sender else 'System',
                    'text': msg.text,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'whisper': True,
                    'to': msg.to_user.display_name if msg.to_user else '',
                    'profile_pic': pic
                })
        else:
            result.append({
                'id': msg.id,
                'display_name': msg.sender.display_name if msg.sender else 'System',
                'text': msg.text,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'profile_pic': pic
            })
    return jsonify(result)

# --- Get pinned messages ---
@app.route('/pinned_messages')
@login_required
def get_pinned_messages():
    """Return all pinned messages."""
    pinned = Message.query.filter_by(pinned=True).order_by(Message.timestamp.desc()).all()
    result = []
    for msg in pinned:
        pic = msg.sender.profile_pic if msg.sender and msg.sender.profile_pic else 'default.png'
        result.append({
            'id': msg.id,
            'display_name': msg.sender.display_name if msg.sender else 'System',
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'pinned': True,
            'profile_pic': pic
        })
    return jsonify(result)

# --- Notify when a user joins ---
@socketio.on('user_joined')
def handle_user_joined():
    """Broadcast a system message when a user joins."""
    if current_user.is_authenticated:
        emit('new_message', {
            'system': True,
            'text': f"{current_user.display_name} has joined the chat.",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

# --- Automatically create an admin user if not exists ---
with app.app_context():
    admin_username = "admin"
    admin_password = "admin123"  # Change this to a secure password!
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
