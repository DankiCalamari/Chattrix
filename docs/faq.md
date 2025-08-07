---
layout: default
title: FAQ
---

# ❓ Frequently Asked Questions

Common questions and answers about Chattrix messaging application.

## 🚀 Getting Started

### What is Chattrix?

Chattrix is a real-time messaging application built with Flask and Socket.IO. It features instant messaging, file sharing, push notifications, and secure communication for individuals and teams.

### What are the system requirements?

**Minimum Requirements:**
- **Server:** 1 vCPU, 1GB RAM, 10GB storage
- **Client:** Any modern web browser (Chrome 70+, Firefox 65+, Safari 12+, Edge 79+)
- **Network:** Stable internet connection

**Recommended for Production:**
- **Server:** 2+ vCPUs, 4GB+ RAM, 50GB+ SSD storage
- **Database:** PostgreSQL 12+ for production use

### Is Chattrix free to use?

Yes! Chattrix is open-source software released under the MIT License. You can use, modify, and distribute it freely. However, you're responsible for your own hosting and infrastructure costs.

### Can I use Chattrix for commercial purposes?

Absolutely! The MIT License allows commercial use. You can deploy Chattrix for your business, modify it for your needs, and even offer it as a service to your customers.

## 📱 Features

### What messaging features are available?

- **Real-time messaging** with instant delivery
- **File sharing** (images, documents, up to 16MB)
- **Push notifications** for desktop and mobile
- **Message editing and deletion**
- **Typing indicators** and read receipts
- **User profiles** with custom avatars
- **Conversation history** with search
- **Emoji support** and reactions (planned)

### Does Chattrix support group chats?

Currently, Chattrix focuses on private one-on-one conversations. Group chat functionality is planned for future releases. You can track this feature request on our [GitHub Issues](https://github.com/DankiCalamari/Chattrix/issues).

### Can I send files through Chattrix?

Yes! You can share:
- **Images:** JPG, PNG, GIF, WebP (auto-preview)
- **Documents:** PDF, DOC, DOCX, TXT
- **Archives:** ZIP, RAR, 7Z
- **File size limit:** 16MB per file

### Do push notifications work on mobile?

Yes! Chattrix supports web push notifications on:
- **Mobile browsers:** Chrome, Firefox, Safari (iOS 16.4+)
- **Desktop:** All major browsers
- **Progressive Web App:** Install for native app experience

## 🔧 Technical Questions

### What technologies does Chattrix use?

**Backend:**
- **Python/Flask** - Web framework
- **Socket.IO** - Real-time communication
- **SQLAlchemy** - Database ORM
- **PostgreSQL/SQLite** - Database
- **Gunicorn** - Production server

**Frontend:**
- **HTML5/CSS3/JavaScript** - Web technologies
- **Socket.IO Client** - Real-time client
- **Service Worker** - Push notifications
- **Progressive Web App** - App-like experience

### Can I integrate Chattrix with other systems?

Yes! Chattrix provides:
- **REST API** for integration
- **WebSocket events** for real-time data
- **Webhook support** (planned)
- **SSO integration** capabilities (LDAP, OAuth planned)

### Is Chattrix mobile-friendly?

Absolutely! Chattrix features:
- **Responsive design** that works on all screen sizes
- **Touch-friendly interface** optimized for mobile
- **Progressive Web App** capabilities
- **Mobile push notifications**
- **Offline message viewing** (cached messages)

### How does real-time messaging work?

Chattrix uses **WebSocket** technology via Socket.IO:
- **Instant delivery** - Messages appear immediately
- **Automatic reconnection** - Handles network interruptions
- **Fallback support** - Falls back to polling if WebSockets fail
- **Room-based messaging** - Efficient message routing

## 🔒 Security & Privacy

### How secure is Chattrix?

Chattrix implements multiple security layers:
- **HTTPS encryption** for all communications
- **Secure password hashing** with bcrypt
- **CSRF protection** against cross-site attacks
- **XSS prevention** with content sanitization
- **Rate limiting** to prevent abuse
- **Input validation** on all user data

### Are messages encrypted?

- **In transit:** Yes, all communications use HTTPS/WSS encryption
- **At rest:** Database encryption depends on your PostgreSQL configuration
- **End-to-end:** Not currently implemented (planned for future release)

### What data does Chattrix collect?

Chattrix only collects data necessary for functionality:
- **Account information:** Username, email, display name
- **Messages:** Text and files you send
- **Usage data:** Login times, last seen status
- **Technical data:** IP addresses (for security), browser info

**We don't collect:**
- Personal information beyond what you provide
- Third-party tracking data
- Advertising profiles
- Unnecessary metadata

### Can I delete my account and data?

Yes! You have full control over your data:
- **Account deletion:** Remove your account completely
- **Message deletion:** Delete individual messages
- **Data export:** Download your message history (planned)
- **Right to be forgotten:** Complete data removal available

### Is Chattrix GDPR compliant?

Chattrix is designed with privacy in mind and includes GDPR-friendly features:
- **Minimal data collection**
- **User consent** for data processing
- **Data portability** (export planned)
- **Right to deletion**
- **Privacy by design** principles

However, GDPR compliance also depends on how you deploy and configure Chattrix.

## 🚀 Deployment

### Where can I host Chattrix?

Chattrix can be deployed on:
- **Cloud providers:** AWS, DigitalOcean, Google Cloud, Azure
- **VPS providers:** Linode, Vultr, Hetzner
- **Platform-as-a-Service:** Heroku, Railway, Render
- **Self-hosted:** Your own servers

### Do I need a domain name?

For production use, yes:
- **HTTPS requirement:** Push notifications require HTTPS
- **SSL certificates:** Need domain for Let's Encrypt
- **Professional appearance:** Better user experience
- **Development:** Can use localhost or IP addresses

### What about hosting costs?

Costs vary by provider and usage:
- **Small deployment:** $5-20/month (VPS + domain)
- **Medium deployment:** $20-100/month (managed database, CDN)
- **Large deployment:** $100+/month (load balancing, monitoring)
- **Free options:** Heroku free tier, self-hosting at home

### Can I use Chattrix offline?

Partial offline support:
- **Cached messages:** View recent messages offline
- **Progressive Web App:** Works when installed
- **Service Worker:** Caches static resources
- **Limitations:** Cannot send/receive new messages offline

## 🔧 Configuration

### How do I enable push notifications?

1. **Generate VAPID keys:** Run `python vapid.py`
2. **Configure environment:** Add keys to `.env` file
3. **Enable HTTPS:** Required for push notifications
4. **User permission:** Users must allow notifications in browser

### Can I customize the appearance?

Yes! Several customization options:
- **CSS styling:** Modify `static/style.css`
- **Templates:** Edit HTML templates
- **Logo/branding:** Replace images and text
- **Themes:** Light/dark mode support
- **Colors:** CSS custom properties for easy theming

### How do I backup my data?

Chattrix includes backup tools:
- **Database backup:** Automated PostgreSQL dumps
- **File backup:** User uploads and profile pictures
- **Configuration backup:** Environment and settings
- **Automated scheduling:** Daily backups via cron

### Can I integrate with LDAP/Active Directory?

LDAP integration is planned for future releases. Currently, you can:
- **Disable registration** and create accounts manually
- **Use external authentication** with custom modifications
- **SSO integration** can be implemented with Flask-OIDC

## 🐛 Troubleshooting

### Messages aren't appearing in real-time

**Common solutions:**
1. **Check network connection** - Ensure stable internet
2. **Refresh the page** - Reload browser tab
3. **Clear browser cache** - Remove cached data
4. **Check firewall** - Ensure WebSocket traffic allowed
5. **Try different browser** - Test in incognito mode

### Push notifications aren't working

**Troubleshooting steps:**
1. **Check browser permissions** - Allow notifications
2. **Verify HTTPS** - Push notifications require secure connection
3. **Check VAPID keys** - Ensure keys are correctly configured
4. **Test browser support** - Some browsers have limitations
5. **Check service worker** - Verify SW is registered correctly

### File uploads are failing

**Common causes:**
1. **File too large** - Check 16MB limit
2. **File type not allowed** - Verify allowed extensions
3. **Disk space full** - Check server storage
4. **Permissions issue** - Verify upload directory permissions
5. **Network timeout** - Try smaller files or better connection

### Application won't start

**Diagnostic steps:**
1. **Check logs** - Review error messages
2. **Verify configuration** - Check `.env` file
3. **Database connection** - Test database connectivity
4. **Port conflicts** - Ensure port 5000 is available
5. **Dependencies** - Reinstall Python packages

### Performance is slow

**Optimization tips:**
1. **Database tuning** - Optimize PostgreSQL settings
2. **Increase resources** - More RAM/CPU if needed
3. **Enable compression** - Nginx gzip compression
4. **CDN for static files** - Offload static content
5. **Database indexing** - Add indexes for frequent queries

## 📊 Usage & Limits

### Are there any usage limits?

Default limits (configurable):
- **Message size:** No specific limit on text
- **File upload:** 16MB per file
- **API rate limiting:** 60 requests per minute
- **Login attempts:** 10 per minute
- **Concurrent connections:** Limited by server resources

### How many users can Chattrix support?

Depends on your server configuration:
- **Small VPS:** 50-100 concurrent users
- **Medium server:** 500-1000 concurrent users
- **Load balanced:** 1000+ concurrent users
- **Database performance** is usually the bottleneck

### Can I scale Chattrix horizontally?

Yes, but requires additional configuration:
- **Multiple app servers** with load balancer
- **Redis for sessions** to share state
- **Shared file storage** (NFS, S3)
- **Database clustering** for high availability

## 🤝 Support & Community

### How do I get help?

**Self-help resources:**
1. **Documentation** - Check all guides first
2. **FAQ** - This page covers common issues
3. **Troubleshooting guide** - Step-by-step solutions
4. **GitHub Issues** - Search existing issues

**Community support:**
- **GitHub Discussions** - Ask questions
- **Discord community** - Real-time help
- **Stack Overflow** - Tag questions with 'chattrix'

### How do I report bugs?

1. **Search existing issues** - Avoid duplicates
2. **Gather information** - Error messages, steps to reproduce
3. **Create GitHub issue** - Use bug report template
4. **Provide details** - OS, browser, version info
5. **Be responsive** - Answer follow-up questions

### How can I contribute?

Many ways to help:
- **Bug reports** - Report issues you find
- **Feature requests** - Suggest improvements
- **Code contributions** - Submit pull requests
- **Documentation** - Improve guides and docs
- **Testing** - Test new features
- **Translations** - Help translate interface

### Is commercial support available?

Currently, Chattrix is community-supported. However:
- **Professional consulting** available for custom deployments
- **Enterprise support** planned for future
- **Training and workshops** can be arranged
- **Custom development** for specific needs

## 🔮 Future Plans

### What features are planned?

**Short-term (next 3-6 months):**
- Group chat functionality
- Message reactions and emoji
- Voice/video calling integration
- Advanced admin panel
- Better mobile app experience

**Medium-term (6-12 months):**
- End-to-end encryption
- LDAP/SSO integration
- Message threading
- Advanced search
- API webhooks

**Long-term (1+ years):**
- Mobile native apps
- Enterprise features
- Advanced analytics
- Plugin system
- White-label solutions

### Will Chattrix always be free?

The core Chattrix application will always remain open-source and free. Future plans may include:
- **Hosted service** - Managed Chattrix hosting
- **Enterprise features** - Advanced features for businesses
- **Professional support** - Paid support options
- **Training and consulting** - Professional services

The open-source version will continue to receive updates and new features.

### How can I stay updated?

- **GitHub** - Watch the repository for updates
- **Releases** - Subscribe to release notifications
- **Discord** - Join community for announcements
- **Newsletter** - Subscribe for major updates (planned)
- **Blog** - Development updates and tutorials (planned)

---

**Still have questions?** Check our [documentation](index.md) or ask on [GitHub Discussions](https://github.com/DankiCalamari/Chattrix/discussions).

---

*Last updated: August 2025*
