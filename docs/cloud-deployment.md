# ☁️ Cloud Deployment Guide

Deploy Chattrix to various cloud platforms with ease. This guide covers the most popular cloud hosting options.

## 🚀 Quick Start

Choose your preferred cloud platform:

- **[Heroku](#heroku)** - Easiest deployment, free tier available
- **[Railway](#railway)** - Modern platform, great developer experience
- **[Render](#render)** - Simple deployment with automatic HTTPS
- **[DigitalOcean App Platform](#digitalocean-app-platform)** - Managed platform service
- **[AWS Elastic Beanstalk](#aws-elastic-beanstalk)** - AWS managed platform
- **[Google Cloud Run](#google-cloud-run)** - Serverless container platform
- **[Azure Container Instances](#azure-container-instances)** - Microsoft's container service
- **[Fly.io](#flyio)** - Edge deployment platform

---

## 🟣 Heroku

Heroku offers the simplest deployment process with a generous free tier.

### Prerequisites
- Heroku account
- Heroku CLI installed
- Git repository

### 1. Install Heroku CLI

**Windows:**
```powershell
# Using Chocolatey
choco install heroku-cli

# Or download from heroku.com
```

**macOS:**
```bash
# Using Homebrew
brew tap heroku/brew && brew install heroku
```

**Linux:**
```bash
# Using snap
sudo snap install --classic heroku
```

### 2. Prepare Your Application

Create `Procfile` in your root directory:
```
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

Create `runtime.txt`:
```
python-3.11.9
```

### 3. Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create your-chattrix-app

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set VAPID_PRIVATE_KEY=your-vapid-private-key
heroku config:set VAPID_PUBLIC_KEY=your-vapid-public-key

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Open your app
heroku open
```

### 4. Environment Variables

Set these in Heroku dashboard or CLI:
```bash
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set VAPID_PRIVATE_KEY=your-vapid-private-key
heroku config:set VAPID_PUBLIC_KEY=your-vapid-public-key
heroku config:set FLASK_ENV=production
```

---

## 🚂 Railway

Railway provides modern deployment with automatic HTTPS and easy database setup.

### 1. Deploy from GitHub

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "Deploy from GitHub repo"
4. Select your Chattrix repository

### 2. Configure Environment

Add these environment variables in Railway dashboard:
```
SECRET_KEY=your-secret-key-here
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
FLASK_ENV=production
PORT=5000
```

### 3. Add PostgreSQL Database

1. Click "New" → "Database" → "PostgreSQL"
2. Railway automatically sets `DATABASE_URL`

### 4. Custom Domain (Optional)

1. Go to Settings → Domains
2. Add your custom domain
3. Update DNS records as shown

---

## 🎨 Render

Render offers simple deployment with automatic SSL and CDN.

### 1. Create Web Service

1. Go to [render.com](https://render.com)
2. Connect your GitHub account
3. Click "New Web Service"
4. Select your Chattrix repository

### 2. Configure Service

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

### 3. Environment Variables

Add in Render dashboard:
```
SECRET_KEY=your-secret-key-here
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
FLASK_ENV=production
PYTHON_VERSION=3.11.9
```

### 4. Add PostgreSQL Database

1. Create new "PostgreSQL" service
2. Copy the connection string
3. Add as `DATABASE_URL` environment variable

---

## 🌊 DigitalOcean App Platform

DigitalOcean's managed platform service with competitive pricing.

### 1. Create App

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository

### 2. Configure App Spec

Create `app.yaml` in your repository:
```yaml
name: chattrix
services:
- name: web
  source_dir: /
  github:
    repo: your-username/chattrix
    branch: main
  run_command: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: SECRET_KEY
    value: your-secret-key-here
  - key: VAPID_PRIVATE_KEY
    value: your-vapid-private-key
  - key: VAPID_PUBLIC_KEY
    value: your-vapid-public-key
  - key: FLASK_ENV
    value: production
databases:
- name: db
  engine: PG
  size: db-s-dev-database
```

### 3. Deploy

```bash
# Install doctl CLI
# Then deploy
doctl apps create --spec app.yaml
```

---

## 🟠 AWS Elastic Beanstalk

AWS managed platform service with extensive configuration options.

### 1. Prepare Application

Create `.ebextensions/python.config`:
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app.py
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: /opt/python/current/app
```

Create `application.py` (Elastic Beanstalk entry point):
```python
from app import app as application

if __name__ == "__main__":
    application.run()
```

### 2. Install EB CLI

```bash
pip install awsebcli
```

### 3. Deploy

```bash
# Initialize EB application
eb init -p python-3.11 chattrix

# Create environment
eb create chattrix-env

# Set environment variables
eb setenv SECRET_KEY=your-secret-key-here
eb setenv VAPID_PRIVATE_KEY=your-vapid-private-key
eb setenv VAPID_PUBLIC_KEY=your-vapid-public-key
eb setenv FLASK_ENV=production

# Deploy
eb deploy

# Open application
eb open
```

### 4. Add RDS Database

1. Go to AWS RDS console
2. Create PostgreSQL database
3. Update environment variables with connection string

---

## 🟦 Google Cloud Run

Serverless container platform that scales to zero.

### 1. Prepare Application

Create `Dockerfile` (if needed):
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

### 2. Deploy

```bash
# Install Google Cloud CLI
# Then authenticate
gcloud auth login
gcloud config set project your-project-id

# Build and deploy
gcloud run deploy chattrix \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="SECRET_KEY=your-secret-key,VAPID_PRIVATE_KEY=your-vapid-private-key,VAPID_PUBLIC_KEY=your-vapid-public-key,FLASK_ENV=production"
```

### 3. Add Cloud SQL Database

```bash
# Create Cloud SQL instance
gcloud sql instances create chattrix-db \
  --database-version=POSTGRES_13 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create chattrix --instance=chattrix-db

# Connect to Cloud Run
gcloud run services update chattrix \
  --add-cloudsql-instances=your-project:us-central1:chattrix-db
```

---

## 🔷 Azure Container Instances

Microsoft's container hosting service.

### 1. Prepare Application

Create `azure-deploy.json`:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "containerName": {
      "type": "string",
      "defaultValue": "chattrix"
    }
  },
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2019-12-01",
      "name": "[parameters('containerName')]",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "[parameters('containerName')]",
            "properties": {
              "image": "your-registry/chattrix:latest",
              "ports": [
                {
                  "port": 5000,
                  "protocol": "TCP"
                }
              ],
              "environmentVariables": [
                {
                  "name": "SECRET_KEY",
                  "value": "your-secret-key"
                },
                {
                  "name": "FLASK_ENV",
                  "value": "production"
                }
              ],
              "resources": {
                "requests": {
                  "cpu": 1,
                  "memoryInGB": 1
                }
              }
            }
          }
        ],
        "osType": "Linux",
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "port": 5000,
              "protocol": "TCP"
            }
          ]
        }
      }
    }
  ]
}
```

### 2. Deploy

```bash
# Install Azure CLI
# Then login
az login

# Create resource group
az group create --name chattrix-rg --location eastus

# Deploy container
az deployment group create \
  --resource-group chattrix-rg \
  --template-file azure-deploy.json \
  --parameters containerName=chattrix
```

---

## 🦋 Fly.io

Edge deployment platform with global distribution.

### 1. Install Fly CLI

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh
```

### 2. Prepare Application

Create `fly.toml`:
```toml
app = "your-chattrix-app"
primary_region = "ord"

[build]
  image = "python:3.11-slim"

[env]
  FLASK_ENV = "production"
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

### 3. Deploy

```bash
# Login to Fly
fly auth login

# Launch app
fly launch

# Set secrets
fly secrets set SECRET_KEY=your-secret-key-here
fly secrets set VAPID_PRIVATE_KEY=your-vapid-private-key
fly secrets set VAPID_PUBLIC_KEY=your-vapid-public-key

# Deploy
fly deploy
```

### 4. Add PostgreSQL

```bash
# Create Postgres cluster
fly postgres create --name chattrix-db

# Attach to app
fly postgres attach --app your-chattrix-app chattrix-db
```

---

## 🔧 Common Configuration

### Environment Variables

All platforms need these environment variables:

```
SECRET_KEY=your-secret-key-here
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### Required Files

Ensure these files are in your repository:

1. **requirements.txt** - Python dependencies
2. **Procfile** (for Heroku) - Process definition
3. **runtime.txt** (optional) - Python version
4. **gunicorn.conf.py** - Gunicorn configuration

### Database Setup

Most platforms offer managed PostgreSQL:

- **Heroku:** `heroku addons:create heroku-postgresql`
- **Railway:** Built-in PostgreSQL service
- **Render:** PostgreSQL service
- **DigitalOcean:** Managed databases
- **AWS:** RDS PostgreSQL
- **GCP:** Cloud SQL
- **Azure:** Azure Database for PostgreSQL
- **Fly.io:** Fly Postgres

---

## 🔍 Troubleshooting

### Common Issues

**Port binding errors:**
```bash
# Ensure your app uses environment PORT
PORT = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=PORT)
```

**Static file serving:**
```python
# Use WhiteNoise for static files
pip install whitenoise
```

**Database connection issues:**
```python
# Check DATABASE_URL format
DATABASE_URL=postgresql://user:password@host:port/database
```

**WebSocket issues:**
```python
# Ensure eventlet worker for Socket.IO
gunicorn --worker-class eventlet -w 1 app:app
```

### Platform-Specific Tips

**Heroku:**
- Use hobby dynos for production
- Enable automatic deploys from GitHub
- Monitor dyno hours usage

**Railway:**
- Use Railway CLI for local development
- Automatic deploys on git push
- Built-in metrics and logging

**Render:**
- Free tier has limitations
- Automatic SSL certificates
- Built-in CDN

---

## 💰 Cost Comparison

| Platform | Free Tier | Paid Plans Start | Database |
|----------|-----------|------------------|----------|
| Heroku | 550-1000 hours/month | $7/month | $9/month |
| Railway | $5 credit/month | $10/month | Included |
| Render | 750 hours/month | $7/month | $7/month |
| DigitalOcean | $200 credit | $5/month | $8/month |
| AWS | 750 hours/month | $8.50/month | $13/month |
| GCP | $300 credit | $6/month | $10/month |
| Azure | $200 credit | $7/month | $12/month |
| Fly.io | $5 credit/month | $2.67/month | $3/month |

---

## 🚀 Next Steps

After deployment:

1. **Configure custom domain**
2. **Set up monitoring**
3. **Configure backups**
4. **Set up CI/CD**
5. **Monitor performance**

---

## 📞 Support

Need help with cloud deployment?

- **Platform Documentation:** Check each platform's official docs
- **Community Support:** GitHub Issues and Discussions
- **Professional Support:** Available for enterprise deployments

---

*Last updated: August 2025*
