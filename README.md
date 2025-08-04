# Chattrix Messaging App

A real-time messaging app built with Flask, Flask-SocketIO, Flask-Login, Flask-Admin, and SQLAlchemy.  
Current features include public chat, private whispers, online user tracking, password encryption, admin panel, and dark mode.

---

## Features

- **User Registration & Login** (secure password hashing)
- **Real-time Chat** (Socket.IO)
- **Private Messages (Whispers)**
- **Online Users List**
- **Pinned Messages**
- **Admin Panel** (`/admin`) for managing users and messages
- **Dark Mode** (persistent across sessions)
- **Responsive Sidebar Layout**
- **User profile pages (avatar, bio)**

---

## To Do

- [x] Pinned Messages
- [x] User profile pages (avatar, bio)
- [ ] Message search/filter
- [x] File/image sharing
- [ ] Emoji/sticker support
- [ ] Message editing/deletion
- [ ] Typing indicators
- [ ] Read receipts
- [ ] Group chat rooms/channels
- [ ] Push notifications
- [ ] Rate limiting/spam protection
- [ ] User blocking/muting
- [ ] Admin/moderator controls (ban/kick)
- [ ] Chat history export
- [ ] Two-factor/Social Login
- [ ] Customizable themes
- [ ] Mobile-friendly design
- [ ] Invite links for private rooms
- [ ] Activity logs for admin
- [ ] Accessibility improvements

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

- **Dark Mode:** Toggle with the sidebar button.
- **Admin Access:** Restrict admin panel by customizing `AdminModelView.is_accessible()`.

---

## Security Notes

- Passwords are **hashed** before storage.
- Use HTTPS and environment variables for secrets in production.

---

## License

MIT

---

## Credits

Built with [Flask](https://flask.palletsprojects.com/), [Flask-SocketIO](https://flask-socketio.readthedocs.io/), [Flask-Admin](https://flask-admin.readthedocs.io/), and [Flask-Login](https://flask-login.readthedocs.io/).