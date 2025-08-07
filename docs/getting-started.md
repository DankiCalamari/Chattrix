---
layout: default
title: Getting Started
---

# 🚀 Getting Started with Chattrix

This guide will help you get Chattrix up and running on your local machine for development and testing purposes.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### Required Software
- **Python 3.8+** - [Download Python](https://python.org/downloads/)
- **Node.js 14+** - [Download Node.js](https://nodejs.org/) (for frontend tools)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **PostgreSQL 12+** - [Download PostgreSQL](https://postgresql.org/download/) (for production) or SQLite (for development)

### System Requirements
- **OS:** Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM:** 2GB minimum, 4GB recommended
- **Storage:** 1GB free space

## 🔧 Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/DankiCalamari/Chattrix.git
cd Chattrix
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit the environment file
nano .env  # or use your preferred editor
```

**Basic `.env` configuration:**
```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-for-development
DEBUG=True

# Database (SQLite for development)
DATABASE_URL=sqlite:///instance/db.sqlite3

# VAPID Keys (generate these - see below)
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_SUBJECT=mailto:your-email@example.com

# Development settings
HOST=127.0.0.1
PORT=5000
```

### 5. Generate VAPID Keys

```bash
python vapid.py
```

Copy the generated keys to your `.env` file.

### 6. Initialize Database

```bash
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully!')
"
```

### 7. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser!

## 🎉 First Steps

### Create Your First Account

1. Navigate to `http://localhost:5000`
2. Click "Register" to create a new account
3. Fill in your details:
   - Username (unique)
   - Email address
   - Password (minimum 8 characters)
   - Display name

### Test Real-time Messaging

1. Open two browser tabs/windows
2. Register two different accounts
3. Start a conversation
4. Watch messages appear in real-time!

### Test Push Notifications

1. Allow notifications when prompted
2. Send yourself a message from another account
3. Minimize the browser window
4. You should receive a desktop notification

## 🛠️ Development Workflow

### File Structure

```
Chattrix/
├── app.py                 # Main application
├── config.py             # Configuration classes
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── vapid.py             # VAPID key generator
├── static/              # Static files
│   ├── script.js        # Frontend JavaScript
│   ├── style.css        # Styles
│   ├── sw.js           # Service Worker
│   └── uploads/        # User uploads
├── templates/           # HTML templates
│   ├── base.html       # Base template
│   ├── chat.html       # Main chat interface
│   └── ...
└── instance/           # Instance-specific files
    └── db.sqlite3      # Development database
```

### Making Changes

1. **Backend Changes:** Edit Python files in the root directory
2. **Frontend Changes:** Edit files in `static/` and `templates/`
3. **Database Changes:** Modify models in `app.py`
4. **Configuration:** Update `config.py` or `.env`

### Testing Your Changes

```bash
# Restart the development server
python app.py

# Check for errors in the console
# Test in browser at http://localhost:5000
```

### Debug Mode

Development mode includes:
- **Auto-reload:** Server restarts on file changes
- **Debug toolbar:** Detailed error information
- **Hot reload:** Frontend changes without restart
- **Verbose logging:** Detailed application logs

## 🔧 Advanced Setup

### Using PostgreSQL for Development

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # macOS with Homebrew
   brew install postgresql
   
   # Windows - Download installer from postgresql.org
   ```

2. **Create database:**
   ```bash
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb chattrix_dev
   ```

3. **Update .env:**
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/chattrix_dev
   ```

### Frontend Development

For advanced frontend development:

```bash
# Install Node.js dependencies (if any)
npm install

# Watch for CSS/JS changes
npm run watch

# Build for production
npm run build
```

### Docker Development

```bash
# Build development container
docker build -t chattrix-dev .

# Run with development settings
docker run -p 5000:5000 --env-file .env chattrix-dev
```

## 🧪 Testing

### Manual Testing Checklist

- [ ] User registration works
- [ ] User login/logout works
- [ ] Real-time messaging functions
- [ ] File upload works
- [ ] Push notifications appear
- [ ] Profile updates save
- [ ] Conversations list loads
- [ ] Private messaging works

### Automated Testing

```bash
# Run test suite (when available)
python -m pytest

# Run with coverage
python -m pytest --cov=app
```

## 🔍 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :5000   # Windows
```

**Database connection error:**
- Check if PostgreSQL is running
- Verify database credentials in `.env`
- Ensure database exists

**VAPID key errors:**
- Run `python vapid.py` to generate new keys
- Copy both private and public keys to `.env`

**Push notifications not working:**
- Ensure you're using HTTPS (required for push notifications)
- Check browser console for errors
- Verify VAPID keys are correctly configured

## 📚 Next Steps

Now that you have Chattrix running locally:

1. **Explore Features:** Try all the messaging features
2. **Customize:** Modify the UI and add your own features
3. **Deploy:** Follow the [Deployment Guide](deployment.md)
4. **Contribute:** Check out the [Contributing Guide](contributing.md)

## 🤝 Getting Help

- **Documentation:** Continue reading these guides
- **Issues:** Check [GitHub Issues](https://github.com/DankiCalamari/Chattrix/issues)
- **Discussions:** Join [GitHub Discussions](https://github.com/DankiCalamari/Chattrix/discussions)
- **Discord:** Join our community server

---

**Ready for production?** Check out the [Production Deployment Guide](deployment.md) next!

---

*Last updated: August 2025*
