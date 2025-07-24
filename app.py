from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender = db.relationship('User', backref='messages')

# ✅ Create tables explicitly inside the app context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chat.html')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        password = request.form['password']
        user = User(display_name=display_name, username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@socketio.on('send_message')
def handle_send_message(data):
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        msg = Message(text=data['text'], sender=user)
        db.session.add(msg)
        db.session.commit()
        emit('new_message', {
            'display_name': user.display_name,
            'text': msg.text,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
