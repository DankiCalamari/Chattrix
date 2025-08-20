import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Upload folders
    PROFILE_PICS_FOLDER = os.path.join('static', 'profile_pics')
    UPLOADS_FOLDER = os.path.join('static', 'uploads')
    
    # VAPID keys for push notifications
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgk1G_g2fw9ue16OEq-OUXGLKrtS7m_ur-IGCeBKzuVuyhRANCAARzgd5E2wmcER-BN-dhz95Qoezig7TFZ-4Yr7fJY-NVuoKT7MXPzcTR3O7SxEsMyCpXmqvNUw1O9-MpYPL_0oy6')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BHOB3kTbCZwRH4E352HP3lCh7OKDtMVn7hivt8lj41W6gpPsxc_NxNHc7tLESwzIKleaq81TDU734ylg8v_SjLo')
    VAPID_CLAIMS = {"sub": os.environ.get('VAPID_SUBJECT', 'mailto:admin@chattrix.com')}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_chattrix.db?check_same_thread=False'
    SESSION_COOKIE_SECURE = False
    
    # SQLite-specific options for development to handle threading
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'check_same_thread': False} if 'sqlite' in (os.environ.get('DEV_DATABASE_URL') or 'sqlite') else {}
    }

def get_database_uri():
    """Get database URI, handling postgres:// to postgresql:// conversion"""
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if database_url:
        # Fix Heroku postgres:// URL to postgresql:// for SQLAlchemy compatibility
        if database_url.startswith('postgres://'):
            return database_url.replace('postgres://', 'postgresql://', 1)
        else:
            return database_url
    else:
        # Fallback to SQLite if no PostgreSQL URL provided
        return 'sqlite:///chattrix_prod.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # This will be set after load_dotenv() is called
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chattrix_prod.db'  # Temporary fallback
    
    # PostgreSQL-specific engine options for better connection handling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Additional security headers
    FORCE_HTTPS = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
