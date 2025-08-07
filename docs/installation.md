---
layout: default
title: Installation Guide
---

# 📦 Installation Guide

This comprehensive guide covers installing Chattrix in different environments and configurations.

## 🖥️ Local Development Installation

### Windows Installation

**Prerequisites:**
```powershell
# Install Python 3.8+ from python.org
# Install Git from git-scm.com
# Install PostgreSQL (optional, for production-like development)
```

**Setup Steps:**
```powershell
# Clone repository
git clone https://github.com/DankiCalamari/Chattrix.git
cd Chattrix

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# Generate VAPID keys
python vapid.py

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run application
python app.py
```

### macOS Installation

**Prerequisites:**
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required software
brew install python3 git postgresql
```

**Setup Steps:**
```bash
# Clone repository
git clone https://github.com/DankiCalamari/Chattrix.git
cd Chattrix

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Generate VAPID keys
python vapid.py

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run application
python app.py
```

### Linux (Ubuntu/Debian) Installation

**Prerequisites:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib
```

**Setup Steps:**
```bash
# Clone repository
git clone https://github.com/DankiCalamari/Chattrix.git
cd Chattrix

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Generate VAPID keys
python vapid.py

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run application
python app.py
```

## 🐳 Docker Installation

### Quick Start with Docker

```bash
# Clone repository
git clone https://github.com/DankiCalamari/Chattrix.git
cd Chattrix

# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env

# Build and run with Docker Compose
docker-compose up --build
```

### Manual Docker Build

```bash
# Build image
docker build -t chattrix:latest .

# Run container
docker run -d \
  --name chattrix \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/static/uploads:/app/static/uploads \
  chattrix:latest
```

### Docker Environment Configuration

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://chattrix:password@db:5432/chattrix
    depends_on:
      - db
    volumes:
      - ./static/uploads:/app/static/uploads

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=chattrix
      - POSTGRES_USER=chattrix
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## ☁️ Cloud Platform Installation

### Heroku Deployment

**Prerequisites:**
- Heroku account
- Heroku CLI installed

**Steps:**
```bash
# Install Heroku CLI
# Windows: Download from heroku.com
# macOS: brew install heroku/brew/heroku
# Linux: snap install heroku --classic

# Login to Heroku
heroku login

# Create application
heroku create your-chattrix-app

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set VAPID_PRIVATE_KEY=your-vapid-private-key
heroku config:set VAPID_PUBLIC_KEY=your-vapid-public-key
heroku config:set VAPID_SUBJECT=mailto:your-email@example.com

# Deploy
git push heroku main

# Initialize database
heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### DigitalOcean Droplet

**Create Droplet:**
1. Ubuntu 20.04 LTS
2. 2GB RAM minimum
3. Add SSH key

**Installation:**
```bash
# Connect to droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# Create application user
adduser --system --group --shell /bin/bash --home /opt/chattrix chattrix

# Switch to application user
su - chattrix

# Clone and setup application
git clone https://github.com/DankiCalamari/Chattrix.git app
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production settings

# Setup database
su - postgres
createuser --interactive chattrix
createdb chattrix_db --owner=chattrix
exit

# Initialize application database
su - chattrix
cd app
source .venv/bin/activate
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Setup systemd service (as root)
# See deployment guide for full systemd configuration
```

### AWS EC2 Deployment

**Launch EC2 Instance:**
1. Ubuntu Server 20.04 LTS
2. t3.micro or larger
3. Configure security groups (HTTP, HTTPS, SSH)

**Installation:**
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib nginx awscli

# Follow same steps as DigitalOcean for application setup
```

## 🔧 Advanced Installation Options

### Production with Systemd

**Create systemd service:**
```bash
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
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable chattrix
sudo systemctl start chattrix
```

### SSL Certificate Installation

**Let's Encrypt (Free):**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Setup auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

**Custom SSL Certificate:**
```bash
# Copy certificates
sudo mkdir -p /etc/ssl/chattrix
sudo cp your-cert.pem /etc/ssl/chattrix/
sudo cp your-key.pem /etc/ssl/chattrix/
sudo chmod 600 /etc/ssl/chattrix/your-key.pem
```

### Database Setup Variations

**PostgreSQL (Production):**
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE chattrix_db;
CREATE USER chattrix_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE chattrix_db TO chattrix_user;
\q

# Update .env
DATABASE_URL=postgresql://chattrix_user:secure_password@localhost:5432/chattrix_db
```

**SQLite (Development):**
```bash
# No installation needed - included with Python
# Update .env
DATABASE_URL=sqlite:///instance/db.sqlite3
```

**MySQL (Alternative):**
```bash
# Install MySQL
sudo apt install mysql-server

# Create database
sudo mysql
CREATE DATABASE chattrix_db;
CREATE USER 'chattrix_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON chattrix_db.* TO 'chattrix_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Install Python MySQL driver
pip install PyMySQL

# Update .env
DATABASE_URL=mysql+pymysql://chattrix_user:secure_password@localhost:3306/chattrix_db
```

## 🔒 Security Hardening During Installation

### Firewall Configuration

```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Fail2Ban Setup

```bash
# Install Fail2Ban
sudo apt install fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# Enable for SSH and Nginx
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### User Security

```bash
# Create dedicated user with limited privileges
sudo adduser --system --group --shell /bin/bash --home /opt/chattrix chattrix

# Restrict file permissions
sudo chown -R chattrix:chattrix /opt/chattrix
sudo chmod -R 755 /opt/chattrix
sudo chmod 600 /opt/chattrix/app/.env
```

## ✅ Installation Verification

### Health Check Commands

```bash
# Check application status
curl -I http://localhost:5000

# Check database connection
sudo -u chattrix psql -d chattrix_db -c "SELECT version();"

# Check logs
sudo journalctl -u chattrix -f

# Check nginx status
sudo nginx -t
sudo systemctl status nginx
```

### Test Functionality

1. **Web Interface:** Visit your domain/IP
2. **Registration:** Create a test account
3. **Messaging:** Send test messages
4. **File Upload:** Upload a test file
5. **Push Notifications:** Test desktop notifications

## 🚨 Troubleshooting Installation

### Common Issues

**Permission denied errors:**
```bash
# Fix ownership
sudo chown -R chattrix:chattrix /opt/chattrix
sudo chmod +x /opt/chattrix/app/.venv/bin/gunicorn
```

**Database connection refused:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l
```

**Port already in use:**
```bash
# Find process using port
sudo lsof -i :5000
sudo kill -9 <PID>
```

**SSL certificate errors:**
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/chattrix/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect yourdomain.com:443
```

### Log Locations

- **Application logs:** `/var/log/chattrix/`
- **Nginx logs:** `/var/log/nginx/`
- **PostgreSQL logs:** `/var/log/postgresql/`
- **System logs:** `/var/log/syslog`

## 📋 Post-Installation Checklist

- [ ] Application starts without errors
- [ ] Database connection works
- [ ] Web interface loads
- [ ] User registration functions
- [ ] Real-time messaging works
- [ ] File uploads work
- [ ] Push notifications function
- [ ] SSL certificate valid
- [ ] Firewall configured
- [ ] Backup system in place
- [ ] Monitoring configured

---

**Next Step:** Configure your installation with the [Configuration Guide](configuration.md) or deploy to production with the [Deployment Guide](deployment.md).

---

*Last updated: August 2025*
