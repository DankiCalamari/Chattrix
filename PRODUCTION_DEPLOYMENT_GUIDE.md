# 🚀 Chattrix Production Deployment Guide

This comprehensive guide will walk you through deploying Chattrix in a production environment with proper security, scalability, and monitoring.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [SSL Certificate Setup](#ssl-certificate-setup)
4. [Database Configuration](#database-configuration)
5. [Application Deployment](#application-deployment)
6. [Nginx Configuration](#nginx-configuration)
7. [Security Hardening](#security-hardening)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup Strategy](#backup-strategy)
10. [Maintenance](#maintenance)
11. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

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

---

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
git clone https://github.com/YourUsername/Chattrix.git app
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

---

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

---

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

---

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

---

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

    # Admin panel with extra security
    location /admin/ {
        limit_req zone=general burst=5 nodelay;
        
        # Optional: IP whitelist for admin
        # allow 203.0.113.1;  # Your IP
        # deny all;
        
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

    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    location = /404.html {
        internal;
    }
    
    location = /50x.html {
        internal;
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

---

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

### 3. System Updates and Security

```bash
# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure automatic updates
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

### 4. File Permissions

```bash
# Set proper file permissions
sudo chown -R chattrix:chattrix /opt/chattrix/app
sudo chmod -R 755 /opt/chattrix/app
sudo chmod 600 /opt/chattrix/app/.env

# Secure upload directories
sudo chmod 755 /opt/chattrix/app/static/uploads
sudo chmod 755 /opt/chattrix/app/static/profile_pics
```

---

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

### 2. System Monitoring Script

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

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log_message "ERROR: PostgreSQL service is not running"
    systemctl restart postgresql
    log_message "INFO: Attempted to restart PostgreSQL service"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    log_message "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ $MEMORY_USAGE -gt 90 ]; then
    log_message "WARNING: Memory usage is at ${MEMORY_USAGE}%"
fi

log_message "INFO: Health check completed"
```

```bash
# Make script executable
sudo chmod +x /opt/chattrix/monitor.sh

# Add to crontab for regular monitoring
sudo crontab -e
```

Add this line to run every 5 minutes:

```
*/5 * * * * /opt/chattrix/monitor.sh
```

### 3. Application Health Check

```bash
# Create health check endpoint test
sudo nano /opt/chattrix/health_check.sh
```

```bash
#!/bin/bash

HEALTH_URL="https://yourdomain.com/"
EXPECTED_STATUS=200

# Check if application responds
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $HTTP_STATUS -eq $EXPECTED_STATUS ]; then
    echo "$(date): Application is healthy (HTTP $HTTP_STATUS)"
else
    echo "$(date): Application is unhealthy (HTTP $HTTP_STATUS)"
    # Restart application
    sudo systemctl restart chattrix
    echo "$(date): Restarted Chattrix service"
fi
```

---

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
# Make executable and set up daily backup
sudo chmod +x /opt/chattrix/backup.sh
sudo crontab -e
```

Add this line for daily backups at 2 AM:

```
0 2 * * * /opt/chattrix/backup.sh
```

### 2. Remote Backup (Optional)

```bash
# Install and configure rclone for cloud backups
curl https://rclone.org/install.sh | sudo bash

# Configure rclone (follow interactive setup)
rclone config

# Add to backup script for cloud sync
# rclone sync /opt/chattrix/backups remote:chattrix-backups
```

---

## 🔧 Maintenance

### 1. Regular Maintenance Tasks

**Daily:**
- Monitor application logs
- Check system resources
- Verify backups completed

**Weekly:**
- Review security logs
- Update packages
- Check SSL certificate expiry

**Monthly:**
- Full system security audit
- Performance review
- Backup verification

### 2. Update Procedure

```bash
# Create update script
sudo nano /opt/chattrix/update.sh
```

```bash
#!/bin/bash

echo "Starting Chattrix update..."

# Switch to application user
sudo su - chattrix << 'EOF'
cd /opt/chattrix/app

# Create backup before update
./backup.sh

# Pull latest changes
git fetch origin
git pull origin main

# Update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations if any
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database migrations completed')
"
EOF

# Restart services
sudo systemctl restart chattrix
sudo systemctl restart nginx

echo "Update completed successfully"
```

### 3. Performance Tuning

```bash
# PostgreSQL tuning
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

# Connection settings
max_connections = 100
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Application Won't Start

```bash
# Check service status
sudo systemctl status chattrix

# Check logs
sudo journalctl -u chattrix -f

# Check configuration
sudo su - chattrix
cd /opt/chattrix/app
source .venv/bin/activate
python3 -c "from app import app; print('Config loaded successfully')"
```

#### 2. Database Connection Issues

```bash
# Test database connection
sudo su - postgres
psql -d chattrix_db -U chattrix_user

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### 3. Nginx Issues

```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

#### 4. SSL Certificate Issues

```bash
# Test SSL certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test SSL configuration
openssl s_client -connect yourdomain.com:443
```

### Log File Locations

- **Application logs:** `/var/log/chattrix/`
- **Nginx logs:** `/var/log/nginx/`
- **PostgreSQL logs:** `/var/log/postgresql/`
- **System logs:** `/var/log/syslog`
- **Security logs:** `/var/log/auth.log`

### Performance Monitoring Commands

```bash
# Monitor system resources
htop
iotop
nethogs

# Monitor database
sudo su - postgres
psql -d chattrix_db -c "SELECT * FROM pg_stat_activity;"

# Monitor application
sudo systemctl status chattrix
sudo journalctl -u chattrix --since "1 hour ago"
```

---

## ✅ Final Checklist

Before going live, ensure:

- [ ] Domain DNS points to your server
- [ ] SSL certificate is installed and working
- [ ] All services start automatically on boot
- [ ] Firewall is configured and enabled
- [ ] Backup system is working
- [ ] Monitoring is in place
- [ ] Security headers are configured
- [ ] Rate limiting is working
- [ ] File uploads work correctly
- [ ] Push notifications are functional
- [ ] Admin panel is accessible
- [ ] Error pages are customized
- [ ] Log rotation is configured
- [ ] Performance is optimized

**Congratulations!** 🎉 Your Chattrix application is now running in a production environment with enterprise-grade security, monitoring, and reliability.

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Consult the main README.md
4. Open an issue on the project repository

---

*Last updated: August 2025*
