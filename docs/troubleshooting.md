---
layout: default
title: Troubleshooting
---

# 🚨 Troubleshooting Guide

Common issues and solutions for Chattrix messaging application.

## 🔍 Quick Diagnostics

### System Health Check

Run these commands to check your system status:

```bash
# Check if Chattrix service is running
sudo systemctl status chattrix

# Check Nginx status
sudo systemctl status nginx

# Check PostgreSQL status
sudo systemctl status postgresql

# Check available disk space
df -h

# Check memory usage
free -h

# Check recent logs
sudo journalctl -u chattrix --since "1 hour ago"
```

### Application Health Check

```bash
# Test HTTP response
curl -I http://localhost:5000

# Test HTTPS (if configured)
curl -I https://yourdomain.com

# Check database connection
sudo -u chattrix psql -d chattrix_db -c "SELECT version();"

# Test WebSocket connection
curl -H "Upgrade: websocket" -H "Connection: Upgrade" http://localhost:5000/socket.io/
```

## 🚫 Common Issues

### Application Won't Start

#### Symptoms
- Service fails to start
- Error 502 Bad Gateway
- Connection refused errors

#### Diagnostic Steps
```bash
# Check service status
sudo systemctl status chattrix

# View detailed logs
sudo journalctl -u chattrix -f

# Check if port is available
sudo lsof -i :5000

# Verify configuration
sudo -u chattrix bash -c "cd /opt/chattrix/app && source .venv/bin/activate && python -c 'from app import app; print(\"Config OK\")'"
```

#### Common Solutions

**1. Port Already in Use**
```bash
# Find process using port 5000
sudo lsof -ti:5000

# Kill the process (replace PID)
sudo kill -9 PID

# Restart Chattrix
sudo systemctl restart chattrix
```

**2. Database Connection Error**
```bash
# Check PostgreSQL is running
sudo systemctl start postgresql

# Test database connection
sudo -u postgres psql -d chattrix_db -c "SELECT 1;"

# Check environment variables
sudo -u chattrix cat /opt/chattrix/app/.env | grep DATABASE_URL
```

**3. Permission Issues**
```bash
# Fix file permissions
sudo chown -R chattrix:chattrix /opt/chattrix
sudo chmod 644 /opt/chattrix/app/.env
sudo chmod +x /opt/chattrix/app/.venv/bin/gunicorn
```

**4. Missing Dependencies**
```bash
# Reinstall dependencies
sudo -u chattrix bash -c "cd /opt/chattrix/app && source .venv/bin/activate && pip install -r requirements.txt"
```

### Database Issues

#### Symptoms
- "Database connection refused"
- "Role does not exist"
- "Database does not exist"

#### Solutions

**1. PostgreSQL Not Running**
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

**2. Database/User Missing**
```bash
# Connect as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE chattrix_db;
CREATE USER chattrix_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE chattrix_db TO chattrix_user;
\q
```

**3. Connection String Issues**
```bash
# Check .env file
sudo -u chattrix nano /opt/chattrix/app/.env

# Verify DATABASE_URL format:
# postgresql://username:password@host:port/database
```

**4. Initialize Database Tables**
```bash
sudo -u chattrix bash -c "
cd /opt/chattrix/app
source .venv/bin/activate
python -c 'from app import app, db; app.app_context().push(); db.create_all()'
"
```

### SSL/TLS Certificate Issues

#### Symptoms
- "Your connection is not private"
- SSL certificate errors
- Mixed content warnings

#### Solutions

**1. Let's Encrypt Certificate Issues**
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run

# If renewal fails, try force renewal
sudo certbot renew --force-renewal
```

**2. Certificate File Permissions**
```bash
# Fix Let's Encrypt permissions
sudo chmod 644 /etc/letsencrypt/live/yourdomain.com/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/yourdomain.com/privkey.pem

# For custom certificates
sudo chmod 644 /etc/ssl/chattrix/cert.pem
sudo chmod 600 /etc/ssl/chattrix/key.pem
```

**3. Nginx SSL Configuration**
```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check SSL configuration
openssl s_client -connect yourdomain.com:443
```

### WebSocket Connection Issues

#### Symptoms
- Messages not appearing in real-time
- "Connection failed" errors
- Fallback to polling only

#### Solutions

**1. Nginx WebSocket Configuration**
```bash
# Verify Nginx configuration includes WebSocket support
sudo nano /etc/nginx/sites-available/chattrix
```

Ensure this section exists:
```nginx
location /socket.io/ {
    proxy_pass http://chattrix_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # ... other headers
}
```

**2. Firewall Issues**
```bash
# Check UFW status
sudo ufw status

# Ensure WebSocket traffic is allowed
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

**3. Browser Issues**
- Clear browser cache and cookies
- Try incognito/private mode
- Test in different browser
- Check browser console for errors

### Push Notification Issues

#### Symptoms
- Notifications not appearing
- "Permission denied" errors
- VAPID key errors

#### Solutions

**1. Browser Permissions**
1. Check browser notification permissions
2. Allow notifications for your domain
3. Test with a simple notification

**2. VAPID Key Issues**
```bash
# Generate new VAPID keys
cd /opt/chattrix/app
python vapid.py

# Update .env file with new keys
sudo -u chattrix nano .env

# Restart application
sudo systemctl restart chattrix
```

**3. Service Worker Issues**
1. Open browser developer tools
2. Go to Application → Service Workers
3. Unregister existing service worker
4. Refresh page to reinstall

### File Upload Issues

#### Symptoms
- "File too large" errors
- Upload progress stalls
- File corruption

#### Solutions

**1. File Size Limits**
```bash
# Check Nginx configuration
sudo nano /etc/nginx/sites-available/chattrix
```

Verify:
```nginx
client_max_body_size 16M;
```

**2. Directory Permissions**
```bash
# Fix upload directory permissions
sudo chown -R chattrix:chattrix /opt/chattrix/app/static/uploads
sudo chmod 755 /opt/chattrix/app/static/uploads
```

**3. Disk Space Issues**
```bash
# Check available disk space
df -h

# Clean up old files if needed
find /opt/chattrix/app/static/uploads -type f -mtime +30 -delete
```

### Performance Issues

#### Symptoms
- Slow page loading
- High memory/CPU usage
- Timeout errors

#### Solutions

**1. Database Performance**
```bash
# Analyze database performance
sudo -u postgres psql -d chattrix_db

# Check for slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# Vacuum and analyze
VACUUM ANALYZE;
```

**2. Application Performance**
```bash
# Check system resources
htop
iotop

# Monitor application logs
sudo tail -f /var/log/chattrix/error.log

# Adjust worker count if needed
sudo nano /opt/chattrix/app/gunicorn.conf.py
```

**3. Nginx Performance**
```bash
# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Monitor access patterns
sudo tail -f /var/log/nginx/access.log

# Test compression
curl -H "Accept-Encoding: gzip" -v https://yourdomain.com
```

### Memory Issues

#### Symptoms
- Out of memory errors
- Application crashes
- System becomes unresponsive

#### Solutions

**1. Check Memory Usage**
```bash
# Current memory usage
free -h

# Memory usage by process
ps aux --sort=-%mem | head -10

# Check for memory leaks
sudo journalctl -u chattrix | grep -i memory
```

**2. Optimize Application**
```bash
# Reduce Gunicorn workers if needed
sudo nano /opt/chattrix/app/gunicorn.conf.py

# Restart application
sudo systemctl restart chattrix

# Monitor memory usage
watch -n 5 'free -h'
```

**3. Add Swap Space (if needed)**
```bash
# Create swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 📊 Monitoring and Logs

### Log File Locations

**Application Logs:**
```bash
# Error logs
tail -f /var/log/chattrix/error.log

# Access logs
tail -f /var/log/chattrix/access.log

# Application logs
sudo journalctl -u chattrix -f
```

**System Logs:**
```bash
# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# System logs
sudo tail -f /var/log/syslog
```

### Useful Monitoring Commands

```bash
# Real-time system monitoring
htop

# Disk I/O monitoring
iotop

# Network monitoring
nethogs

# Check open files/connections
lsof -i
ss -tuln

# Monitor specific process
watch -n 2 'ps aux | grep chattrix'
```

### Performance Metrics

```bash
# Database connection count
sudo -u postgres psql -d chattrix_db -c "SELECT count(*) FROM pg_stat_activity;"

# Nginx connection status
curl http://localhost/nginx_status

# Application response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000

# System load average
uptime
```

## 🔧 Recovery Procedures

### Application Recovery

**1. Quick Restart**
```bash
sudo systemctl restart chattrix nginx postgresql
```

**2. Full Recovery from Backup**
```bash
# Stop services
sudo systemctl stop chattrix nginx

# Restore database
sudo -u postgres psql -d chattrix_db < /path/to/backup.sql

# Restore application files
sudo tar -xzf /path/to/app_backup.tar.gz -C /

# Fix permissions
sudo chown -R chattrix:chattrix /opt/chattrix

# Start services
sudo systemctl start postgresql nginx chattrix
```

### Database Recovery

**1. From SQL Backup**
```bash
# Stop application
sudo systemctl stop chattrix

# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE chattrix_db;"
sudo -u postgres psql -c "CREATE DATABASE chattrix_db OWNER chattrix_user;"

# Restore from backup
sudo -u postgres psql -d chattrix_db < backup.sql

# Start application
sudo systemctl start chattrix
```

**2. Point-in-Time Recovery (if WAL enabled)**
```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Restore from base backup and replay WAL files
# (Requires advanced PostgreSQL knowledge)

# Start PostgreSQL
sudo systemctl start postgresql
```

### Configuration Recovery

**1. Reset to Default Configuration**
```bash
# Backup current config
sudo cp /opt/chattrix/app/.env /opt/chattrix/app/.env.backup

# Copy from template
sudo cp /opt/chattrix/app/.env.example /opt/chattrix/app/.env

# Edit with correct values
sudo nano /opt/chattrix/app/.env

# Restart application
sudo systemctl restart chattrix
```

## 📞 Getting Help

### Before Contacting Support

1. **Gather Information:**
   - Error messages (exact text)
   - Steps to reproduce the issue
   - When the issue started
   - System information (OS, browser, etc.)

2. **Check Logs:**
   - Application logs for errors
   - System logs for related issues
   - Browser console errors (for client issues)

3. **Try Basic Solutions:**
   - Restart browser/clear cache
   - Restart application services
   - Check network connectivity

### Support Resources

**Documentation:**
- This troubleshooting guide
- [Installation Guide](installation.md)
- [Deployment Guide](deployment.md)
- [API Reference](api-reference.md)

**Community Support:**
- GitHub Issues
- Discussion Forums
- Community Chat

**Professional Support:**
- Email: support@chattrix.com
- Enterprise support available
- Professional consulting services

### Submitting Bug Reports

Include this information:

1. **System Information:**
   - Operating system and version
   - Browser type and version
   - Chattrix version

2. **Error Details:**
   - Exact error message
   - Steps to reproduce
   - Screenshots if applicable

3. **Log Files:**
   - Relevant log excerpts
   - Configuration files (remove sensitive data)

4. **Environment:**
   - Production vs development
   - Recent changes made
   - Other software installed

---

**🆘 Emergency Procedures:** For critical issues affecting service availability, follow the [disaster recovery procedures](deployment.md#backup-strategy) or contact emergency support.

---

*Last updated: August 2025*
