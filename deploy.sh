#!/bin/bash

# Production deployment script for Linux servers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Chattrix Production Deployment Script${NC}"
echo "=========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit .env file with your production values before continuing.${NC}"
    exit 1
fi

# Install dependencies
echo -e "${GREEN}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=production

# Database setup
echo -e "${GREEN}🗄️  Setting up database...${NC}"
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Database initialized')
"

# Create systemd service file
echo -e "${GREEN}⚙️  Creating systemd service...${NC}"
sudo tee /etc/systemd/system/chattrix.service > /dev/null <<EOF
[Unit]
Description=Chattrix Messaging App
After=network.target

[Service]
Type=notify
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin
ExecStart=$(pwd)/.venv/bin/gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 --timeout 120 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable chattrix
sudo systemctl start chattrix

echo -e "${GREEN}✅ Chattrix deployed successfully!${NC}"
echo -e "${GREEN}🌐 Access your app at: http://your-server-ip:5000${NC}"
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo "  - View logs: sudo journalctl -u chattrix -f"
echo "  - Restart: sudo systemctl restart chattrix"
echo "  - Stop: sudo systemctl stop chattrix"
