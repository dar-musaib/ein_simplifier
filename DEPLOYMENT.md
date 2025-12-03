# Deployment Guide

This guide covers deploying the EIN Names Editor application to a production server.

**Choose your deployment method:**

- **[Docker Deployment](#docker-deployment-recommended)** - Easier, recommended for most users
- **[Manual Deployment](#manual-deployment)** - Traditional method with more control

---

## Docker Deployment (Recommended)

Docker provides an isolated, reproducible environment that's easier to deploy and maintain.

### Prerequisites

- SSH access to the server
- Docker and Docker Compose installed on the server
- Domain name (optional, for production)

### Step 1: Install Docker on Server

```bash
# Connect to server
ssh username@your-server-ip

# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (to run without sudo)
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect

# Verify installation
docker --version
```

### Step 2: Transfer Application Files

From your local machine:

```bash
# Navigate to project directory
cd /path/to/ein_simplifier

# Transfer files to server
rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' --exclude='.git' \
  ./ username@your-server-ip:/opt/ein_simplifier/
```

Or use SCP:

```bash
scp -r . username@your-server-ip:/opt/ein_simplifier/
```

### Step 3: Set Up on Server

```bash
# SSH to server
ssh username@your-server-ip

# Navigate to application directory
cd /opt/ein_simplifier

# Ensure data directories exist
mkdir -p storage files

# Transfer source CSV file (if not already there)
# From local machine:
# scp files/unique_ein_spons.csv username@your-server-ip:/opt/ein_simplifier/files/
```

### Step 4: Configure Environment Variables

```bash
# Create .env file from example
cp env.example .env

# Edit environment variables
nano .env
```

Update `.env` with production settings:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false
LOG_LEVEL=info

# CORS Configuration - IMPORTANT: Set your actual domain(s)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# File Paths (inside container)
STORAGE_DIR=/app/storage
SOURCE_FILE=/app/files/unique_ein_spons.csv
WORKING_FILE=/app/storage/working_data.csv
```

### Step 5: Build and Run with Docker

```bash
cd /opt/ein_simplifier

# Build the Docker image
make docker-build
# or: docker build -t ein-simplifier .

# Start the container
make docker-up
# or use the script: ./docker-run.sh start

# View logs
make docker-logs
# or: docker logs -f ein-simplifier

# Check container status
make docker-status
# or: docker ps | grep ein-simplifier
```

### Step 6: Verify Deployment

```bash
# Check application health
curl http://localhost:8000/health

# View container logs
make docker-logs
# or: docker logs -f ein-simplifier

# Check if container is running
make docker-status
# or: docker ps | grep ein-simplifier
```

### Step 7: Set Up Nginx Reverse Proxy (Optional)

For production, you can set up Nginx on the host (not in Docker) to proxy to the container:

1. **Install Nginx on host:**

```bash
sudo apt install -y nginx
```

2. **Create Nginx config:**

```bash
sudo nano /etc/nginx/sites-available/ein-simplifier
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Enable and restart:**

```bash
sudo ln -s /etc/nginx/sites-available/ein-simplifier /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 8: Set Up SSL with Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com
```

### Docker Management Commands

```bash
# Build image
make docker-build
# or: docker build -t ein-simplifier .

# Start container
make docker-up
# or: ./docker-run.sh start

# Stop container
make docker-down
# or: ./docker-run.sh stop

# Restart container
make docker-restart
# or: ./docker-run.sh restart

# View logs
make docker-logs
# or: docker logs -f ein-simplifier

# Open shell in container
make docker-shell
# or: docker exec -it ein-simplifier /bin/bash

# Check status
make docker-status
```

### Update Application

```bash
cd /opt/ein_simplifier

# Pull latest code (if using git)
git pull

# Rebuild and restart
make docker-build
make docker-restart

# Or use the script
./docker-run.sh build
./docker-run.sh restart
```

### Backup Data

```bash
# Backup storage directory
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz storage/

# Restore from backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
```

### Troubleshooting Docker Deployment

**Container won't start:**

```bash
# Check logs
docker logs ein-simplifier

# Check container status
docker ps -a | grep ein-simplifier

# Rebuild container
make docker-build
make docker-up
```

**Port already in use:**

```bash
# Check what's using the port
sudo lsof -i :8000

# Change port by setting PORT variable
PORT=8001 make docker-up
# or edit docker-run.sh or Makefile
```

**Permission issues:**

```bash
# Fix storage directory permissions
sudo chown -R $USER:$USER storage/ files/
```

**Data not persisting:**

- Ensure volumes are properly mounted in `docker-compose.yml`
- Check volume paths are correct

---

## Manual Deployment

### Prerequisites

- SSH access to the server
- Server with Python 3.7+ installed
- Root or sudo access (for systemd service and nginx configuration)
- Domain name (optional, for production)

### Step 1: Connect to Server

```bash
ssh username@your-server-ip
# or
ssh username@your-domain.com
```

### Step 2: Prepare Server Environment

### 2.1 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y  # For Ubuntu/Debian
# or
sudo yum update -y  # For CentOS/RHEL
```

### 2.2 Install Python and Required Tools

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git

# CentOS/RHEL
sudo yum install -y python3 python3-pip git
```

### 2.3 Create Application Directory

```bash
# Create directory for the application
sudo mkdir -p /opt/ein_simplifier
sudo chown $USER:$USER /opt/ein_simplifier
cd /opt/ein_simplifier
```

### Step 3: Transfer Application Files

### Option A: Using SCP (from your local machine)

From your local machine terminal:

```bash
# Navigate to project directory
cd /path/to/ein_simplifier

# Transfer all files (excluding __pycache__ and venv)
scp -r \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.git' \
  . username@your-server-ip:/opt/ein_simplifier/
```

Or use rsync (recommended):

```bash
rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' --exclude='.git' \
  ./ username@your-server-ip:/opt/ein_simplifier/
```

### Option B: Using Git (if repository is available)

On the server:

```bash
cd /opt/ein_simplifier
git clone <your-repo-url> .
# or if you have a private repo, set up SSH keys first
```

### Option C: Manual File Transfer

1. Create a tarball on your local machine:

```bash
cd /path/to/ein_simplifier
tar -czf ein_simplifier.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.git' \
  .
```

2. Transfer to server:

```bash
scp ein_simplifier.tar.gz username@your-server-ip:/opt/ein_simplifier/
```

3. Extract on server:

```bash
cd /opt/ein_simplifier
tar -xzf ein_simplifier.tar.gz
```

### Step 4: Set Up Python Environment

```bash
cd /opt/ein_simplifier

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

```bash
# Copy example environment file
cp env.example .env

# Edit environment file
nano .env
```

Update `.env` with production settings:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false
LOG_LEVEL=info

# CORS Configuration - IMPORTANT: Set your actual domain(s)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# File Paths
STORAGE_DIR=/opt/ein_simplifier/storage
SOURCE_FILE=/opt/ein_simplifier/files/unique_ein_spons.csv
WORKING_FILE=/opt/ein_simplifier/storage/working_data.csv
```

**Security Note:** Never commit `.env` file to version control!

### Step 6: Set Up Data Files

```bash
# Ensure directories exist
mkdir -p /opt/ein_simplifier/files
mkdir -p /opt/ein_simplifier/storage

# Transfer your source CSV file
# From local machine:
scp files/unique_ein_spons.csv username@your-server-ip:/opt/ein_simplifier/files/
```

### Step 7: Test the Application

```bash
cd /opt/ein_simplifier
source venv/bin/activate

# Test run (will create working_data.csv on first run)
python main.py
```

Press `Ctrl+C` to stop. If it runs successfully, proceed to the next step.

### Step 8: Create Systemd Service

Create a systemd service file for automatic startup and management:

```bash
sudo nano /etc/systemd/system/ein-simplifier.service
```

Add the following content:

```ini
[Unit]
Description=EIN Names Editor API
After=network.target

[Service]
Type=simple
User=your-username
Group=your-username
WorkingDirectory=/opt/ein_simplifier
Environment="PATH=/opt/ein_simplifier/venv/bin"
EnvironmentFile=/opt/ein_simplifier/.env
ExecStart=/opt/ein_simplifier/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ein-simplifier

[Install]
WantedBy=multi-user.target
```

**Important:** Replace `your-username` with your actual username.

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ein-simplifier

# Start the service
sudo systemctl start ein-simplifier

# Check status
sudo systemctl status ein-simplifier

# View logs
sudo journalctl -u ein-simplifier -f
```

### Step 9: Set Up Nginx Reverse Proxy (Recommended)

### 9.1 Install Nginx

```bash
sudo apt install -y nginx  # Ubuntu/Debian
# or
sudo yum install -y nginx  # CentOS/RHEL
```

### 9.2 Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/ein-simplifier
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS (optional, after setting up SSL)
    # return 301 https://$server_name$request_uri;

    # For now, proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Increase timeouts for large requests
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

**Note:** Replace `your-domain.com` with your actual domain name.

### 9.3 Enable Site

```bash
# Create symlink (Ubuntu/Debian)
sudo ln -s /etc/nginx/sites-available/ein-simplifier /etc/nginx/sites-enabled/

# For CentOS/RHEL, add to /etc/nginx/conf.d/ein-simplifier.conf instead

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 10: Set Up SSL Certificate (Let's Encrypt)

### 10.1 Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu/Debian
# or
sudo yum install -y certbot python3-certbot-nginx  # CentOS/RHEL
```

### 10.2 Obtain SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts. Certbot will automatically update your nginx configuration.

### 10.3 Auto-Renewal

Certbot sets up auto-renewal automatically. Test it:

```bash
sudo certbot renew --dry-run
```

### Step 11: Configure Firewall

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

**Important:** Only allow port 8000 if you're not using nginx reverse proxy.

### Step 12: Verify Deployment

1. **Check Service Status:**

```bash
sudo systemctl status ein-simplifier
```

2. **Check Application Health:**

```bash
curl http://localhost:8000/health
```

3. **Access via Domain:**
   Open your browser and visit:

- `http://your-domain.com` (or `https://your-domain.com` if SSL is set up)
- `http://your-domain.com/docs` (API documentation)

### Step 13: Monitoring and Maintenance

### View Logs

```bash
# Application logs
sudo journalctl -u ein-simplifier -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Service

```bash
sudo systemctl restart ein-simplifier
```

### Update Application

```bash
cd /opt/ein_simplifier
source venv/bin/activate

# Pull latest changes (if using git)
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart ein-simplifier
```

### Backup Working Data

```bash
# Create backup script
sudo nano /opt/ein_simplifier/backup.sh
```

Add:

```bash
#!/bin/bash
BACKUP_DIR="/opt/ein_simplifier/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/working_data_$DATE.tar.gz \
  /opt/ein_simplifier/storage/working_data.csv \
  /opt/ein_simplifier/storage/*_metadata.json
# Keep only last 7 days of backups
find $BACKUP_DIR -name "working_data_*.tar.gz" -mtime +7 -delete
```

Make executable:

```bash
chmod +x /opt/ein_simplifier/backup.sh
```

Add to crontab for daily backups:

```bash
crontab -e
# Add this line:
0 2 * * * /opt/ein_simplifier/backup.sh
```

## Troubleshooting

### Service Won't Start

1. Check logs: `sudo journalctl -u ein-simplifier -n 50`
2. Verify file paths in `.env`
3. Check permissions: `ls -la /opt/ein_simplifier`
4. Verify Python environment: `source venv/bin/activate && python --version`

### 502 Bad Gateway

1. Check if service is running: `sudo systemctl status ein-simplifier`
2. Check if port 8000 is accessible: `curl http://localhost:8000/health`
3. Review nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### CORS Errors

1. Verify `CORS_ORIGINS` in `.env` includes your domain
2. Restart service after changing `.env`: `sudo systemctl restart ein-simplifier`

### Out of Memory

1. Reduce workers in `.env`: `WORKERS=2`
2. Update systemd service file accordingly
3. Consider upgrading server resources

### Data Not Loading

1. Verify source file exists: `ls -lh /opt/ein_simplifier/files/unique_ein_spons.csv`
2. Check file permissions
3. Review application logs for parsing errors

## Security Checklist

- [ ] Changed default SSH port (optional but recommended)
- [ ] Set up SSH key authentication (disable password auth)
- [ ] Configured firewall rules
- [ ] Set `CORS_ORIGINS` to specific domains (not `*`)
- [ ] Installed SSL certificate
- [ ] Set up regular backups
- [ ] Limited file permissions (chmod 600 for `.env`)
- [ ] Regular system updates
- [ ] Monitoring and alerting (optional)

## Quick Reference Commands

```bash
# Service management
sudo systemctl start ein-simplifier
sudo systemctl stop ein-simplifier
sudo systemctl restart ein-simplifier
sudo systemctl status ein-simplifier
sudo journalctl -u ein-simplifier -f

# Nginx
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart nginx

# Application directory
cd /opt/ein_simplifier
source venv/bin/activate
```

## Support

For issues or questions:

1. Check application logs: `sudo journalctl -u ein-simplifier -f`
2. Review nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Test API directly: `curl http://localhost:8000/health`
4. Check service status: `sudo systemctl status ein-simplifier`
