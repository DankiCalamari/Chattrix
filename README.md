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
- [x] File/image sharing
- [x] private messaging
- [x] Push notifications
- [ ] Admin/moderator controls (ban/kick)
- [ ] Chat history export
- [ ] Two-factor/Social Login
- [x] Customizable themes (darkmode/lightmode)
- [x] Mobile-friendly design
- [ ] Invite links for private rooms

---

## Getting Started

### Development Setup

#### 1. Install Dependencies

```sh
pip install -r requirements.txt
```

#### 2. Environment Configuration

Copy the example environment file and configure it:
```sh
cp .env.example .env
# Edit .env with your configuration
```

#### 3. Run the App

```sh
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) in your browser.

---

## Production Deployment

### Option 1: Linux Server with systemd

1. **Clone and setup:**
```sh
git clone <your-repo>
cd messaging_app_socketio
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```sh
cp .env.example .env
# Edit .env with production values
nano .env
```

3. **Deploy:**
```sh
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Docker

1. **Build and run:**
```sh
docker-compose up -d
```

2. **With custom domain (edit docker-compose.yml first):**
```sh
# Edit nginx.conf with your domain
docker-compose up -d
```

### Option 3: Heroku

1. **Install Heroku CLI and login:**
```sh
heroku login
```

2. **Create app:**
```sh
heroku create your-app-name
```

3. **Set environment variables:**
```sh
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
heroku config:set VAPID_PRIVATE_KEY=your-vapid-private-key
heroku config:set VAPID_PUBLIC_KEY=your-vapid-public-key
```

4. **Add PostgreSQL:**
```sh
heroku addons:create heroku-postgresql:hobby-dev
```

5. **Deploy:**
```sh
git push heroku main
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_ENV` | Environment (development/production) | ✅ |
| `SECRET_KEY` | Flask secret key | ✅ |
| `DATABASE_URL` | Database connection string | ✅ |
| `VAPID_PRIVATE_KEY` | Push notification private key | ✅ |
| `VAPID_PUBLIC_KEY` | Push notification public key | ✅ |
| `ADMIN_USERNAME` | Default admin username | ❌ |
| `ADMIN_PASSWORD` | Default admin password | ❌ |

---

## Configuration

- **Database:** 
  - Development: SQLite (`dev_chattrix.db`)
  - Production: PostgreSQL (recommended) or SQLite
- **Admin Panel:** Visit `/admin` (requires `is_admin` property on User model)
- **Password Hashing:** Uses `pbkdf2:sha256` via Werkzeug
- **Environment:** Configured via `.env` file or environment variables

---

## Production Features

- **Environment-based configuration** (development/production/testing)
- **PostgreSQL support** for scalable production deployment
- **Docker containerization** with multi-service setup
- **Nginx reverse proxy** with SSL and rate limiting
- **Gunicorn WSGI server** with eventlet workers for WebSocket support
- **Systemd service** for Linux server deployment
- **Heroku-ready** configuration
- **Security headers** and HTTPS enforcement
- **File upload handling** with configurable storage
- **Environment variable management** with .env support

---

## Security Considerations

### Production Checklist

- [ ] Change default SECRET_KEY
- [ ] Use strong admin credentials
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up proper database backups
- [ ] Configure rate limiting
- [ ] Review CORS settings
- [ ] Set up monitoring and logging
- [ ] Configure firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable database connection pooling
- [ ] Set up automated security updates

---

## Folder Structure

```
messaging_app_socketio/
├── app.py                 # Main application file
├── config.py             # Configuration classes
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── gunicorn.conf.py     # Gunicorn configuration
├── deploy.sh            # Linux deployment script
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Multi-service Docker setup
├── nginx.conf           # Nginx reverse proxy config
├── templates/           # Jinja2 templates
│   ├── base.html
│   ├── chat.html
│   ├── login.html
│   └── ...
├── static/              # Static assets
│   ├── style.css
│   ├── script.js
│   ├── sw.js           # Service worker for push notifications
│   ├── profile_pics/   # User profile pictures
│   └── uploads/        # File uploads
└── instance/           # Instance-specific files
    └── *.db           # SQLite databases
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