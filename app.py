from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import send, emit, join_room, leave_room, SocketIO
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash   # For password hashing
# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
socketio = SocketIO(app, manage_session=True)



# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# SocketIO session/user mapping
user_sid_map = {}      # Maps user id to SocketIO session id
online_users = {}      # Maps user id to display_name

# Handle user connection
@socketio.on('connect')
def handle_connect(auth=None):
    if current_user.is_authenticated:
        user_sid_map[current_user.id] = request.sid
        online_users[current_user.id] = current_user.display_name
        emit('online_users', list(online_users.values()), broadcast=True)

# Handle user disconnection
@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        user_sid_map.pop(current_user.id, None)
        online_users.pop(current_user.id, None)
        emit('online_users', list(online_users.values()), broadcast=True)

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    whisper = db.Column(db.Boolean, default=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_whispers')

# Create tables
with app.app_context():
    db.create_all()


#Flask-Admin setup
admin = Admin(app, name='Chattrix Admin', template_mode='bootstrap4')
class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Message, db.session))



# Handle whisper (private message)
@socketio.on('whisper')
def handle_whisper(data):
    if current_user.is_authenticated:
        to_user = User.query.filter_by(username=data['to']).first()
        if to_user and to_user.id in user_sid_map:
            # Save whisper to DB
            msg = Message(
                text=data['text'],
                sender=current_user,
                whisper=True,
                to_user=to_user
            )
            db.session.add(msg)
            db.session.commit()
            # Send whisper to recipient
            emit('whisper', {
                'display_name': current_user.display_name,
                'text': data['text'],
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'to': to_user.display_name
            }, room=user_sid_map[to_user.id])
            # Send confirmation to sender
            emit('whisper', {
                'display_name': f"You (to {to_user.display_name})",
                'text': data['text'],
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'to': to_user.display_name
            }, room=request.sid)

# Chat page (requires login)
@app.route('/')
@login_required
def index():
    return render_template('chat.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        password = request.form['password']
        hashedPassword = generate_password_hash(password, method='pbkdf2:sha256')
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return "Username already exists", 400
        # Create new user
        user = User(display_name=display_name, username=username, password=hashedPassword)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

# User logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Handle sending a public message
@socketio.on('send_message')
def handle_send_message(data):
    if current_user.is_authenticated:
        msg = Message(text=data['text'], sender=current_user)
        db.session.add(msg)
        db.session.commit()
        emit('new_message', {
            'display_name': current_user.display_name,
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

# Get all messages (public and whispers relevant to user)
@app.route('/messages')
@login_required
def get_messages():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    result = []
    for msg in messages:
        # Show whispers only to sender or recipient
        if msg.whisper:
            if msg.sender_id == current_user.id or msg.to_user_id == current_user.id:
                result.append({
                    'display_name': msg.sender.display_name if msg.sender else 'System',
                    'text': msg.text,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'whisper': True,
                    'to': msg.to_user.display_name if msg.to_user else ''
                })
        else:
            result.append({
                'display_name': msg.sender.display_name if msg.sender else 'System',
                'text': msg.text,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
    return jsonify(result)

# Notify when a user joins
@socketio.on('user_joined')
def handle_user_joined():
    if current_user.is_authenticated:
        emit('new_message', {
            'system': True,
            'text': f"{current_user.display_name} has joined the chat.",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

# Run the app
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
