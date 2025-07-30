# Chattrix Messaging App

A real-time messaging app built with Flask, Flask-SocketIO, Flask-Login, Flask-Admin, and SQLAlchemy.  
Features include public chat, private whispers, online user tracking, password encryption, admin panel, and dark mode.

---

## Features

- **User Registration & Login** (with password hashing)
- **Real-time Chat** (Socket.IO)
- **Private Messages (Whispers)**
- **Online Users List**
- **Admin Panel** (`/admin`) for managing users and messages
- **Dark Mode** (toggle only, not persistent)
- **Responsive Sidebar Layout**

---

## Getting Started

### 1. Install Dependencies

```sh
pip install flask flask-socketio flask-login flask-admin flask_sqlalchemy werkzeug requests
```

### 2. Run the App

```sh
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) in your browser.

---

## Configuration

- **Database:** SQLite (`db.sqlite3` by default)
- **Admin Panel:** Visit `/admin` (requires `is_admin` property on User model)
- **Password Hashing:** Uses `pbkdf2:sha256` via Werkzeug

---

## Folder Structure

```
messaging_app_socketio/
├── app.py
├── templates/
│   ├── base.html
│   ├── chat.html
│   ├── login.html
│   ├── register.html
│   └── ... (other templates)
├── static/
│   └── style.css
└── db.sqlite3
```

---

## Customization

- **Dark Mode:** Toggle with the button in the sidebar.
- **Admin Access:** Restrict admin panel by customizing `AdminModelView.is_accessible()`.

---

## Security Notes

- Passwords are **hashed** before storage.
- Always use HTTPS and environment variables for secrets in production.

---

## License

MIT

---

## Credits

Built with [Flask](https://flask.palletsprojects.com/), [Flask-SocketIO](https://flask-socketio.readthedocs.io/), [Flask-Admin](https://flask-admin.readthedocs.io/), and [Flask-Login](https://flask-login.readthedocs.io/).