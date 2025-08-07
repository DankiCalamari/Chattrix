#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""
import os
from app import app, socketio

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# For gunicorn with eventlet worker
application = socketio

if __name__ == "__main__":
    # This won't be called when using gunicorn, but useful for testing
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
