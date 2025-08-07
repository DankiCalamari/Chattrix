#!/usr/bin/env python3
"""
Test script to verify PostgreSQL database connection
"""
import os
from dotenv import load_dotenv
from config import config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection and configuration"""
    
    # Import the app creation function
    from app import create_app
    
    # Force production config to test PostgreSQL
    config_name = 'production'
    
    # Debug environment variables
    print("Environment variables:")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')}")
    print(f"POSTGRES_URL: {os.environ.get('POSTGRES_URL', 'NOT SET')}")
    print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")
    
    # Create app using the actual create_app function
    app = create_app(config_name)
    
    print(f"\nTesting with config: {config_name}")
    print(f"App Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Initialize SQLAlchemy
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    # Test connection within app context
    with app.app_context():
        try:
            # Try to execute a simple query using text() for newer SQLAlchemy
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1")).fetchone()
            print("✅ Database connection successful!")
            print(f"Test query result: {result}")
            
            # Check if we can create tables
            db.create_all()
            print("✅ Database tables created/verified successfully!")
            
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

if __name__ == "__main__":
    test_database_connection()
