---
layout: default
title: Configuration Guide
---

# ⚙️ Configuration Guide

Complete guide to configuring Chattrix for different environments and use cases.

## 🔧 Environment Configuration

### Configuration Files

Chattrix uses multiple configuration methods:

1. **Environment Variables** (`.env` file)
2. **Configuration Classes** (`config.py`)
3. **Runtime Settings** (Admin panel)

### Environment Variables (.env)

#### Core Application Settings

```env
# Flask Configuration
FLASK_ENV=development                    # development|production|testing
SECRET_KEY=your-super-secret-key-here   # Minimum 32 characters
DEBUG=False                             # True|False

# Server Configuration  
HOST=127.0.0.1                         # Bind address
PORT=5000                               # Port number
```

#### Database Configuration

```env
# Development (SQLite)
DATABASE_URL=sqlite:///instance/db.sqlite3

# Production (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/chattrix_db

# Alternative formats
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
DATABASE_URL=mysql+pymysql://user:password@host:port/database
```

#### Security Settings

```env
# Session Security
SESSION_COOKIE_SECURE=True              # HTTPS only cookies
SESSION_COOKIE_HTTPONLY=True            # No JavaScript access
SESSION_COOKIE_SAMESITE=Lax             # CSRF protection
PERMANENT_SESSION_LIFETIME=86400        # Session timeout (seconds)

# CSRF Protection
WTF_CSRF_ENABLED=True                   # Enable CSRF protection
WTF_CSRF_TIME_LIMIT=3600                # CSRF token timeout

# Password Security
BCRYPT_LOG_ROUNDS=12                    # Password hash rounds
```

#### Push Notifications (VAPID)

```env
# VAPID Configuration
VAPID_PRIVATE_KEY=your-private-key      # Generate with vapid.py
VAPID_PUBLIC_KEY=your-public-key        # Generate with vapid.py  
VAPID_SUBJECT=mailto:admin@yourdomain.com
```

#### File Upload Settings

```env
# Upload Configuration
MAX_CONTENT_LENGTH=16777216             # 16MB in bytes
UPLOAD_FOLDER=static/uploads            # Upload directory
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,txt,doc,docx,zip

# Profile Pictures
PROFILE_PIC_FOLDER=static/profile_pics
MAX_PROFILE_PIC_SIZE=2097152           # 2MB in bytes
```

#### Email Configuration (Optional)

```env
# SMTP Settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

#### Logging Configuration

```env
# Logging Settings
LOG_LEVEL=INFO                          # DEBUG|INFO|WARNING|ERROR|CRITICAL
LOG_FILE=logs/chattrix.log
LOG_MAX_BYTES=10485760                  # 10MB
LOG_BACKUP_COUNT=5
```

#### Performance Settings

```env
# Database Connection Pool
SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE=10
SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW=20
SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT=30

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0
SESSION_TYPE=redis                      # Use Redis for sessions
```

#### Feature Flags

```env
# Feature Toggles
ENABLE_REGISTRATION=True                # Allow new user registration
ENABLE_FILE_UPLOAD=True                 # Allow file uploads
ENABLE_PUSH_NOTIFICATIONS=True          # Enable push notifications
ENABLE_EMAIL_NOTIFICATIONS=False        # Send email notifications
REQUIRE_EMAIL_VERIFICATION=False        # Require email verification
```

### Configuration Classes (config.py)

#### Development Configuration

```python
class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'db.sqlite3')
    
    # Security (relaxed for development)
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Performance
    SQLALCHEMY_ECHO = True  # Log SQL queries
```

#### Production Configuration

```python
class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Security (strict)
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # HTTPS
    PREFERRED_URL_SCHEME = 'https'
    
    # Logging
    LOG_LEVEL = 'INFO'
    
    # Performance
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

#### Testing Configuration

```python
class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Security
    WTF_CSRF_ENABLED = False
    
    # Disable features for testing
    ENABLE_PUSH_NOTIFICATIONS = False
    ENABLE_EMAIL_NOTIFICATIONS = False
```

## 🔒 Security Configuration

### HTTPS Configuration

#### Nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Application proxy
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Flask HTTPS Configuration

```python
# Force HTTPS in production
if app.config['FLASK_ENV'] == 'production':
    from flask_talisman import Talisman
    
    Talisman(app, 
        force_https=True,
        strict_transport_security=True,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' https://cdn.socket.io",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: https:",
            'connect-src': "'self' wss: https:"
        }
    )
```

### Rate Limiting Configuration

#### Nginx Rate Limiting

```nginx
http {
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=10r/m;
    
    server {
        # Apply rate limits
        location /login {
            limit_req zone=login burst=3 nodelay;
            # ... proxy configuration
        }
        
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            # ... proxy configuration  
        }
        
        location /upload {
            limit_req zone=upload burst=5 nodelay;
            # ... proxy configuration
        }
    }
}
```

#### Application Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to specific routes
@app.route('/api/messages', methods=['POST'])
@limiter.limit("100 per hour")
def send_message():
    # Implementation
    pass

@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    # Implementation
    pass
```

## 🗄️ Database Configuration

### PostgreSQL Configuration

#### Connection Settings

```env
# Basic connection
DATABASE_URL=postgresql://chattrix_user:password@localhost:5432/chattrix_db

# With SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Connection pool settings
SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE=10
SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW=20
SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT=30
SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE=3600
```

#### PostgreSQL Server Configuration

```conf
# /etc/postgresql/13/main/postgresql.conf

# Connection settings
listen_addresses = 'localhost'
port = 5432
max_connections = 100

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Security
ssl = on
password_encryption = scram-sha-256
```

### Database Migrations

```python
# migrations/env.py configuration
from alembic import context
from app import app, db

def run_migrations_online():
    """Run migrations in 'online' mode."""
    with app.app_context():
        connectable = db.engine
        
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=db.metadata,
                compare_type=True,
                compare_server_default=True
            )
            
            with context.begin_transaction():
                context.run_migrations()
```

## 🔔 Push Notifications Configuration

### VAPID Key Generation

```python
# vapid.py - Generate VAPID keys
from py_vapid import Vapid01

vapid = Vapid01()
vapid.generate_keys()

print("VAPID_PRIVATE_KEY=" + vapid.private_key.decode('utf-8'))
print("VAPID_PUBLIC_KEY=" + vapid.public_key.decode('utf-8'))
```

### Service Worker Configuration

```javascript
// static/sw.js
const CACHE_NAME = 'chattrix-v1';
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/script.js',
    '/static/images/icon-192.png'
];

// Install event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(urlsToCache);
            })
    );
});

// Push notification handling
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : 'New message received',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/badge-72.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View message',
                icon: '/static/images/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close notification',
                icon: '/static/images/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Chattrix', options)
    );
});
```

## 📁 File Upload Configuration

### Storage Configuration

```python
# Local file storage
UPLOAD_FOLDER = 'static/uploads'
PROFILE_PIC_FOLDER = 'static/profile_pics'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# File type validation
ALLOWED_EXTENSIONS = {
    'images': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
    'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
    'archives': {'zip', 'rar', '7z'},
    'all': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'zip'}
}

def allowed_file(filename, file_type='all'):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())
```

### Cloud Storage (AWS S3)

```python
# AWS S3 configuration
import boto3
from botocore.client import Config

# S3 settings
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-west-2')

# S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION,
    config=Config(signature_version='s3v4')
)

def upload_to_s3(file, filename):
    """Upload file to S3 bucket."""
    try:
        s3_client.upload_fileobj(
            file,
            AWS_S3_BUCKET,
            filename,
            ExtraArgs={"ACL": "public-read"}
        )
        return f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{filename}"
    except Exception as e:
        print(f"S3 upload error: {e}")
        return None
```

## 📧 Email Configuration

### SMTP Configuration

```python
# Email settings
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

# Email templates
EMAIL_TEMPLATES = {
    'welcome': 'emails/welcome.html',
    'password_reset': 'emails/password_reset.html',
    'verification': 'emails/verification.html'
}
```

### Email Providers

#### Gmail Configuration

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password  # Use app password, not regular password
```

#### SendGrid Configuration

```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
```

## 🚀 Performance Configuration

### Gunicorn Configuration

```python
# gunicorn.conf.py
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "/var/log/chattrix/access.log"
errorlog = "/var/log/chattrix/error.log"
loglevel = "info"

# Performance
worker_tmp_dir = "/dev/shm"  # Use RAM for temporary files
```

### Redis Configuration (Session Storage)

```python
# Redis session configuration
import redis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url(REDIS_URL)
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True
SESSION_KEY_PREFIX = 'chattrix:'
```

### Caching Configuration

```python
# Flask-Caching configuration
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
CACHE_DEFAULT_TIMEOUT = 300

# Cache specific settings
CACHE_KEY_PREFIX = 'chattrix_cache:'
CACHE_OPTIONS = {
    'connection_pool_kwargs': {
        'max_connections': 20,
        'retry_on_timeout': True
    }
}
```

## 📊 Monitoring Configuration

### Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler

def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # File handler
        file_handler = RotatingFileHandler(
            'logs/chattrix.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Chattrix startup')
```

### Health Check Configuration

```python
@app.route('/health')
def health_check():
    """Application health check endpoint."""
    checks = {
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'disk_space': check_disk_space(),
        'memory': check_memory_usage()
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    })
```

## 🔧 Environment-Specific Configurations

### Development Environment

```env
# Development .env
FLASK_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///instance/dev.db
WTF_CSRF_ENABLED=False
SESSION_COOKIE_SECURE=False
ENABLE_EMAIL_NOTIFICATIONS=False
LOG_LEVEL=DEBUG
```

### Staging Environment

```env
# Staging .env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=staging-secret-key
DATABASE_URL=postgresql://user:pass@staging-db:5432/chattrix_staging
WTF_CSRF_ENABLED=True
SESSION_COOKIE_SECURE=True
ENABLE_EMAIL_NOTIFICATIONS=True
LOG_LEVEL=INFO
```

### Production Environment

```env
# Production .env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=super-secure-production-key
DATABASE_URL=postgresql://user:pass@prod-db:5432/chattrix_prod
WTF_CSRF_ENABLED=True
SESSION_COOKIE_SECURE=True
PREFERRED_URL_SCHEME=https
ENABLE_EMAIL_NOTIFICATIONS=True
LOG_LEVEL=WARNING
```

## ✅ Configuration Validation

### Environment Validation Script

```python
# validate_config.py
import os
import sys
from urllib.parse import urlparse

def validate_database_url():
    """Validate database URL format."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return False, "DATABASE_URL not set"
    
    try:
        parsed = urlparse(db_url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid DATABASE_URL format"
        return True, "Valid"
    except Exception as e:
        return False, f"Error parsing DATABASE_URL: {e}"

def validate_secret_key():
    """Validate secret key strength."""
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        return False, "SECRET_KEY not set"
    
    if len(secret_key) < 32:
        return False, "SECRET_KEY too short (minimum 32 characters)"
    
    return True, "Valid"

def validate_vapid_keys():
    """Validate VAPID keys are present."""
    private_key = os.environ.get('VAPID_PRIVATE_KEY')
    public_key = os.environ.get('VAPID_PUBLIC_KEY')
    
    if not private_key or not public_key:
        return False, "VAPID keys not set"
    
    return True, "Valid"

def main():
    """Run all configuration validations."""
    validations = [
        ("Database URL", validate_database_url),
        ("Secret Key", validate_secret_key),
        ("VAPID Keys", validate_vapid_keys)
    ]
    
    all_valid = True
    for name, validator in validations:
        valid, message = validator()
        status = "✓" if valid else "✗"
        print(f"{status} {name}: {message}")
        if not valid:
            all_valid = False
    
    if not all_valid:
        sys.exit(1)
    
    print("\n✓ All configurations valid!")

if __name__ == "__main__":
    main()
```

Run validation:
```bash
python validate_config.py
```

---

**🔗 Related Documentation:**
- [Installation Guide](installation.md)
- [Deployment Guide](deployment.md)
- [Security Guide](security.md)

---

*Last updated: August 2025*
