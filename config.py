"""
Chattrix Application Configuration Module

This module contains all configuration classes for different deployment environments.
Supports development, production, and testing configurations with environment-specific
database connections, security settings, and feature toggles.

Features:
- Environment-based configuration management
- VAPID keys for push notifications
- Database URI handling with PostgreSQL/SQLite support
- Session security configuration
- File upload settings
"""

import os
from datetime import timedelta

class Config:
    """
    Base Configuration Class
    
    Contains default configuration values shared across all environments.
    Provides foundation settings that can be overridden by specific environment configs.
    """
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB maximum file upload size
    
    # File Upload Directory Configuration
    PROFILE_PICS_FOLDER = os.path.join('static', 'profile_pics')  # User profile images
    UPLOADS_FOLDER = os.path.join('static', 'uploads')            # General file uploads
    
    # VAPID Keys for Web Push Notifications
    # These keys enable server-side push notification sending to browsers
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 
        'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgk1G_g2fw9ue16OEq-OUXGLKrtS7m_ur-IGCeBKzuVuyhRANCAARzgd5E2wmcER-BN-dhz95Qoezig7TFZ-4Yr7fJY-NVuoKT7MXPzcTR3O7SxEsMyCpXmqvNUw1O9-MpYPL_0oy6')
    
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 
        'BHOB3kTbCZwRH4E352HP3lCh7OKDtMVn7hivt8lj41W6gpPsxc_NxNHc7tLESwzIKleaq81TDU734ylg8v_SjLo')
    
    VAPID_CLAIMS = {"sub": os.environ.get('VAPID_SUBJECT', 'mailto:admin@chattrix.com')}
    
    # Session Management Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Session expiry duration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks via JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

class DevelopmentConfig(Config):
    """
    Development Environment Configuration
    
    Optimized for local development with debugging enabled,
    SQLite database, and relaxed security settings.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_chattrix.db?check_same_thread=False'
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    
    # SQLite-specific engine options for development environment
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'connect_args': {'check_same_thread': False} if 'sqlite' in (os.environ.get('DEV_DATABASE_URL') or 'sqlite') else {}
    }

def getDatabaseUri():
    """
    Get Database URI with Automatic Protocol Conversion
    
    Handles the conversion from Heroku's postgres:// format to SQLAlchemy's
    required postgresql:// format. Provides fallback to SQLite for local development.
    
    Returns:
        str: Properly formatted database URI for SQLAlchemy connection
    """
    strDatabaseUrl = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if strDatabaseUrl:
        # Fix Heroku postgres:// URL to postgresql:// for SQLAlchemy compatibility
        if strDatabaseUrl.startswith('postgres://'):
            return strDatabaseUrl.replace('postgres://', 'postgresql://', 1)
        else:
            return strDatabaseUrl
    else:
        # Fallback to SQLite if no PostgreSQL URL provided
        return 'sqlite:///chattrix_prod.db'

class ProductionConfig(Config):
    """
    Production Environment Configuration
    
    Optimized for production deployment with enhanced security,
    PostgreSQL database support, and strict session management.
    """
    DEBUG = False
    
    # This will be set after load_dotenv() is called in the application factory
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chattrix_prod.db'  # Temporary fallback
    
    # PostgreSQL-specific engine options for robust connection handling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,     # Connection timeout in seconds
        'pool_recycle': 3600,   # Recycle connections every hour
        'pool_pre_ping': True   # Verify connections before use
    }
    
    # Enhanced security settings for production environment
    SESSION_COOKIE_SECURE = True     # Requires HTTPS connection
    SESSION_COOKIE_HTTPONLY = True   # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE = 'Strict'  # Strict CSRF protection
    
    # Additional production security headers
    FORCE_HTTPS = True  # Enforce HTTPS redirects

class TestingConfig(Config):
    """
    Testing Environment Configuration
    
    Isolated configuration for unit testing with in-memory database
    and disabled security features for easier test execution.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database for testing
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier form testing

# Configuration Dictionary for Environment Selection
dictConfig = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Legacy alias for backward compatibility
config = dictConfig
