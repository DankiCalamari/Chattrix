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
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgA3dGz3rKYLqXI8r8oALzmJJKh6I6yXDMbEa8dOGGo')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BHpyTs0vPvs6J2qHEIQPQxuzZ-BO3MEdVXMR3CP_AP1LMEZhfUOKIdDstklsqhQ8Tp5XCwGlUfwEuACBXk_EcB8')
    VAPID_CLAIMS = {"sub": os.environ.get('VAPID_SUBJECT', 'mailto:admin@chattrix.com')}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_chattrix.db'
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Use PostgreSQL in production (recommended)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        os.environ.get('POSTGRES_URL') or \
        'postgresql://user:password@localhost/chattrix_prod'
    
    # If using SQLite in production (not recommended for scale)
    if not os.environ.get('DATABASE_URL') and not os.environ.get('POSTGRES_URL'):
        SQLALCHEMY_DATABASE_URI = 'sqlite:///chattrix_prod.db'
    
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
