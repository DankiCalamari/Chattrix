---
layout: default
title: Production Deployment
---

# 🚀 Production Deployment Guide

This comprehensive guide covers deploying Chattrix in a production environment with enterprise-grade security, scalability, and reliability.

## 📋 Prerequisites

### Server Requirements

**Minimum Specifications:**
- **CPU:** 2 vCPUs
- **RAM:** 2GB
- **Storage:** 20GB SSD
- **OS:** Ubuntu 20.04 LTS or newer
- **Network:** Public IP address
- **Domain:** Registered domain name

**Recommended Specifications:**
- **CPU:** 4 vCPUs
- **RAM:** 4GB
- **Storage:** 50GB SSD
- **Backup:** Regular automated backups

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    ufw \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    htop \
    fail2ban \
    logrotate
```

## 🖥️ Server Setup

### 1. Create Application User

```bash
# Create dedicated user for the application
sudo adduser --system --group --shell /bin/bash --home /opt/chattrix chattrix

# Switch to application user
sudo su - chattrix
```

### 2. Clone and Setup Application

```bash
# Clone the repository
cd /opt/chattrix
git clone https://github.com/DankiCalamari/Chattrix.git app
cd app

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Production .env Configuration:**

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secure-random-secret-key-min-32-chars
DEBUG=False

# Database Configuration
DATABASE_URL=postgresql://chattrix_user:secure_password@localhost:5432/chattrix_db

# VAPID Keys for Push Notifications
VAPID_PRIVATE_KEY=your-generated-vapid-private-key
VAPID_PUBLIC_KEY=your-generated-vapid-public-key
VAPID_SUBJECT=mailto:admin@yourdomain.com

# Admin Configuration
ADMIN_USERNAME=admin
ADMIN_PASSWORD=very-secure-admin-password
ADMIN_EMAIL=admin@yourdomain.com

# Server Configuration
HOST=127.0.0.1
PORT=5000

# Security
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
```

## 🔒 SSL Certificate Setup

### Option 1: Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### Option 2: Custom SSL Certificate

```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/chattrix

# Copy your certificates
sudo cp your-cert.pem /etc/ssl/chattrix/cert.pem
sudo cp your-private-key.pem /etc/ssl/chattrix/key.pem

# Set proper permissions
sudo chmod 600 /etc/ssl/chattrix/key.pem
sudo chmod 644 /etc/ssl/chattrix/cert.pem
```

## 🗄️ Database Configuration

### 1. PostgreSQL Setup

```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
psql
```

```sql
-- Create user and database
CREATE USER chattrix_user WITH PASSWORD 'secure_password';
CREATE DATABASE chattrix_db OWNER chattrix_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE chattrix_db TO chattrix_user;
ALTER USER chattrix_user CREATEDB;

-- Exit psql
\q
```

```bash
# Exit postgres user
exit
```

### 2. Database Security

```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Add/modify these settings:

```conf
# Connection settings
listen_addresses = 'localhost'
max_connections = 100

# Security settings
ssl = on
password_encryption = scram-sha-256

# Performance settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

```bash
# Edit pg_hba.conf for authentication
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Ensure these lines exist:

```conf
# Local connections
local   all             postgres                                peer
local   all             all                                     md5

# IPv4 local connections
host    all             all             127.0.0.1/32            md5
```

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### 3. Initialize Database

```bash
# Switch to application user
sudo su - chattrix
cd /opt/chattrix/app
source .venv/bin/activate

# Initialize database
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
```

## 🚀 Application Deployment

### 1. Systemd Service Configuration

```bash
# Create systemd service file
sudo nano /etc/systemd/system/chattrix.service
```

```ini
[Unit]
Description=Chattrix Messaging Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=chattrix
Group=chattrix
WorkingDirectory=/opt/chattrix/app
Environment=PATH=/opt/chattrix/app/.venv/bin
EnvironmentFile=/opt/chattrix/app/.env
ExecStart=/opt/chattrix/app/.venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/chattrix/app/static/uploads /opt/chattrix/app/static/profile_pics

[Install]
WantedBy=multi-user.target
```

### 2. Gunicorn Configuration

```bash
# Create/edit gunicorn configuration
nano /opt/chattrix/app/gunicorn.conf.py
```

```python
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
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "chattrix"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
```

### 3. Create Log Directory

```bash
# Create log directory
sudo mkdir -p /var/log/chattrix
sudo chown chattrix:chattrix /var/log/chattrix
sudo chmod 755 /var/log/chattrix
```

### 4. Start Application Service

```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable chattrix
sudo systemctl start chattrix

# Check status
sudo systemctl status chattrix
```

## 🌐 Nginx Configuration

### 1. Create Nginx Configuration

```bash
# Create Nginx site configuration
sudo nano /etc/nginx/sites-available/chattrix
```

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general:10m rate=5r/s;

# Upstream backend
upstream chattrix_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss: https:; font-src 'self';" always;

    # File upload size
    client_max_body_size 16M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static files with caching
    location /static/ {
        alias /opt/chattrix/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        
        # Security for uploaded files
        location ~* \.(php|jsp|pl|py|asp|sh|cgi)$ {
            deny all;
        }
    }

    # Socket.IO with proper WebSocket support
    location /socket.io/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://chattrix_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Login rate limiting
    location ~ ^/(login|register)$ {
        limit_req zone=login burst=3 nodelay;
        
        proxy_pass http://chattrix_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # API endpoints
    location ~ ^/(api|subscribe|vapid-public-key|upload|messages)/ {
        limit_req zone=api burst=15 nodelay;
        
        proxy_pass http://chattrix_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main application
    location / {
        limit_req zone=general burst=10 nodelay;
        
        proxy_pass http://chattrix_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

### 2. Enable Site and Test Configuration

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/chattrix /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🛡️ Security Hardening

### 1. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change 22 to your custom SSH port if modified)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 2. Fail2Ban Configuration

```bash
# Create Fail2Ban jail for Nginx
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
```

```bash
# Restart Fail2Ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

## 📊 Monitoring & Logging

### 1. Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/chattrix
```

```
/var/log/chattrix/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0644 chattrix chattrix
    postrotate
        /bin/systemctl reload chattrix
    endscript
}
```

### 2. Health Monitoring

```bash
# Create monitoring script
sudo nano /opt/chattrix/monitor.sh
```

```bash
#!/bin/bash

# Chattrix Monitoring Script
LOG_FILE="/var/log/chattrix/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log_message() {
    echo "[$DATE] $1" >> $LOG_FILE
}

# Check if application is running
if ! systemctl is-active --quiet chattrix; then
    log_message "ERROR: Chattrix service is not running"
    systemctl restart chattrix
    log_message "INFO: Attempted to restart Chattrix service"
fi

# Check if Nginx is running
if ! systemctl is-active --quiet nginx; then
    log_message "ERROR: Nginx service is not running"
    systemctl restart nginx
    log_message "INFO: Attempted to restart Nginx service"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    log_message "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

log_message "INFO: Health check completed"
```

```bash
# Make script executable and schedule
sudo chmod +x /opt/chattrix/monitor.sh
sudo crontab -e
```

Add this line to run every 5 minutes:
```
*/5 * * * * /opt/chattrix/monitor.sh
```

## 💾 Backup Strategy

### 1. Database Backup Script

```bash
# Create backup script
sudo nano /opt/chattrix/backup.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/opt/chattrix/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="chattrix_db"
DB_USER="chattrix_user"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
export PGPASSWORD="secure_password"
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz \
    /opt/chattrix/app/static/uploads \
    /opt/chattrix/app/static/profile_pics \
    /opt/chattrix/app/.env

# Remove backups older than 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "$(date): Backup completed - $DATE"
```

```bash
# Make executable and schedule daily backup
sudo chmod +x /opt/chattrix/backup.sh
sudo crontab -e
```

Add for daily backups at 2 AM:
```
0 2 * * * /opt/chattrix/backup.sh
```

## 🔧 Performance Optimization

### 1. PostgreSQL Tuning

```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/*/main/postgresql.conf
```

```conf
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 2. System Optimizations

```bash
# Increase file descriptor limits
sudo nano /etc/security/limits.conf
```

Add:
```
chattrix soft nofile 65536
chattrix hard nofile 65536
```

## 🚨 Troubleshooting

### Service Status Checks

```bash
# Check all services
sudo systemctl status chattrix nginx postgresql

# Check logs
sudo journalctl -u chattrix -f
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/chattrix/error.log
```

### Common Issues

**Application won't start:**
```bash
sudo systemctl status chattrix
sudo journalctl -u chattrix --no-pager
```

**Database connection issues:**
```bash
sudo -u postgres psql -d chattrix_db -c "SELECT version();"
```

**SSL certificate problems:**
```bash
sudo certbot certificates
openssl s_client -connect yourdomain.com:443
```

## ✅ Production Checklist

Before going live:

- [ ] Domain DNS points to your server
- [ ] SSL certificate installed and auto-renewing
- [ ] All services start on boot
- [ ] Firewall configured and active
- [ ] Backup system operational
- [ ] Monitoring scripts running
- [ ] Log rotation configured
- [ ] Security headers enabled
- [ ] Rate limiting functional
- [ ] Database optimized
- [ ] Error pages customized
- [ ] Performance tested

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Daily:**
- Monitor logs for errors
- Check backup completion
- Review security alerts

**Weekly:**
- Update system packages
- Review performance metrics
- Check SSL certificate expiry

**Monthly:**
- Security audit
- Performance review
- Backup restoration test

### Getting Help

- **Documentation:** Check troubleshooting guides
- **Logs:** Review application and system logs
- **Community:** GitHub Issues and Discussions
- **Professional Support:** Available for enterprise deployments

---

**🎉 Congratulations!** Your Chattrix application is now running in a secure, scalable production environment.

---

*Last updated: August 2025*
