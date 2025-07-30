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
- **Dark Mode** (Persistent)
- **Responsive Sidebar Layout**

---
##To Do

-[] User profile pages (with avatar and bio)
-[] Message search/filter functionality
-[] File/image sharing in chat
-[] Emoji/sticker support
-[] Message editing and deletion
-[] Typing indicators ("user is typing...")
-[] Read receipts for messages
-[] Group chat rooms/channels
-[] Push notifications (browser or email)
-[] Rate limiting or spam protection
-[] User blocking/muting
-[] Admin/moderator controls (ban/kick users)
-[] Chat message history export (download as text)
-[] Two-factor/Social Login authentication for login
-[] Customizable themes (user-selectable color schemes)
-[] Mobile-friendly responsive design
-[] Invite links for private rooms
-[] Activity logs for admin review
-[] Accessibility improvements (screen reader support, contrast options)

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