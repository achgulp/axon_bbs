#!/bin/bash
#
# Axon BBS Installation Script for Ubuntu 24.04 (WSL)
# Target: sysadmin@192.168.58.8
#
# This script installs and configures:
# - System dependencies (Python, PostgreSQL, Node.js, Tor, Git)
# - Axon BBS Django backend
# - React frontend
# - Tor hidden service
# - PostgreSQL database
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/axon_bbs"
REPO_URL="https://github.com/achgulp/axon_bbs.git"
DB_NAME="axon_bbs"
DB_USER="axon"
DB_PASS="$(openssl rand -base64 32)"
VENV_DIR="${INSTALL_DIR}/venv"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo bash $0)"
    exit 1
fi

log_info "Starting Axon BBS installation..."

# Update system
log_info "Updating system packages..."
apt update
apt upgrade -y

# Install system dependencies
log_info "Installing system dependencies..."
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nodejs \
    npm \
    tor \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    curl \
    wget

# Install Node.js 18+ (if not already at correct version)
log_info "Checking Node.js version..."
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    log_warn "Node.js version too old, installing v18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
fi

# Create axon user if doesn't exist
if ! id "axon" &>/dev/null; then
    log_info "Creating axon user..."
    useradd -r -m -d /home/axon -s /bin/bash axon
fi

# Clone repository
log_info "Cloning Axon BBS repository..."
if [ -d "$INSTALL_DIR" ]; then
    log_warn "Directory $INSTALL_DIR already exists, removing..."
    rm -rf "$INSTALL_DIR"
fi

git clone "$REPO_URL" "$INSTALL_DIR"
chown -R axon:axon "$INSTALL_DIR"

# Set up Python virtual environment
log_info "Setting up Python virtual environment..."
su - axon -c "cd $INSTALL_DIR && python3.12 -m venv venv"
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && pip install --upgrade pip"
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && pip install -r requirements.txt"

# Set up PostgreSQL
log_info "Configuring PostgreSQL database..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || log_warn "User $DB_USER might already exist"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || log_warn "Database $DB_NAME might already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"  # For running tests

# Create .env file
log_info "Creating .env configuration file..."
cat > "$INSTALL_DIR/.env" <<EOF
# Django settings
SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.58.8,.onion

# Database
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME

# Tor configuration
TOR_PROXY=socks5h://127.0.0.1:9050

# BBS Identity (will be generated)
# BBS_IDENTITY_PUBKEY=
# BBS_IDENTITY_PRIVKEY=
# BBS_IDENTITY_ENCRYPTION_KEY=
EOF

chown axon:axon "$INSTALL_DIR/.env"
chmod 600 "$INSTALL_DIR/.env"

# Save database credentials for admin
cat > /root/axon_bbs_db_credentials.txt <<EOF
Axon BBS Database Credentials
=============================
Database: $DB_NAME
User: $DB_USER
Password: $DB_PASS

PostgreSQL Connection String:
postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
EOF
chmod 600 /root/axon_bbs_db_credentials.txt

log_info "Database credentials saved to /root/axon_bbs_db_credentials.txt"

# Run Django migrations
log_info "Running Django database migrations..."
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && python manage.py migrate"

# Create Django superuser (non-interactive)
log_info "Creating Django superuser..."
DJANGO_SUPERUSER_PASSWORD=$(openssl rand -base64 24)
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && \
    DJANGO_SUPERUSER_PASSWORD='$DJANGO_SUPERUSER_PASSWORD' \
    python manage.py createsuperuser \
    --noinput \
    --username admin \
    --email admin@localhost" || log_warn "Superuser might already exist"

# Save superuser credentials
cat > /root/axon_bbs_admin_credentials.txt <<EOF
Axon BBS Admin Credentials
==========================
Username: admin
Password: $DJANGO_SUPERUSER_PASSWORD

Web Interface: http://192.168.58.8:8000/admin/
EOF
chmod 600 /root/axon_bbs_admin_credentials.txt

log_info "Admin credentials saved to /root/axon_bbs_admin_credentials.txt"

# Initialize BBS identity
log_info "Initializing BBS cryptographic identity..."
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && python manage.py init_bbs_identity"

# Create default message boards
log_info "Creating default message boards..."
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && python manage.py create_default_boards" || log_warn "Boards might already exist"

# Install frontend dependencies
log_info "Installing frontend dependencies..."
su - axon -c "cd $INSTALL_DIR/frontend && npm install"

# Build React frontend
log_info "Building React frontend (this may take a few minutes)..."
su - axon -c "cd $INSTALL_DIR/frontend && npm run build"

# Collect static files
log_info "Collecting Django static files..."
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && python manage.py collectstatic --noinput"

# Configure Tor
log_info "Configuring Tor hidden service..."
cat >> /etc/tor/torrc <<EOF

# Axon BBS Hidden Service
HiddenServiceDir /var/lib/tor/axon_bbs/
HiddenServicePort 80 127.0.0.1:8000
EOF

# Restart Tor to generate .onion address
systemctl restart tor
systemctl enable tor

# Wait for Tor to generate hostname
sleep 5

# Get .onion address
if [ -f /var/lib/tor/axon_bbs/hostname ]; then
    ONION_ADDR=$(cat /var/lib/tor/axon_bbs/hostname)
    log_info "Tor hidden service created: http://$ONION_ADDR"

    # Update .env with onion address
    echo "ONION_ADDRESS=$ONION_ADDR" >> "$INSTALL_DIR/.env"

    # Save to credentials file
    echo "" >> /root/axon_bbs_admin_credentials.txt
    echo "Tor Hidden Service: http://$ONION_ADDR" >> /root/axon_bbs_admin_credentials.txt
else
    log_warn "Tor hostname not generated yet. Check /var/lib/tor/axon_bbs/hostname later."
fi

# Create systemd service
log_info "Creating systemd service..."
cat > /etc/systemd/system/axon-bbs.service <<EOF
[Unit]
Description=Axon BBS Django Application
After=network.target postgresql.service tor.service
Requires=postgresql.service tor.service

[Service]
Type=simple
User=axon
Group=axon
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind 0.0.0.0:8000 --timeout 120 axon_project.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install gunicorn if not already installed
su - axon -c "cd $INSTALL_DIR && source venv/bin/activate && pip install gunicorn"

# Reload systemd and start service
systemctl daemon-reload
systemctl enable axon-bbs.service
systemctl start axon-bbs.service

# Create log directory
mkdir -p /var/log/axon_bbs
chown axon:axon /var/log/axon_bbs

# Final status check
sleep 3
if systemctl is-active --quiet axon-bbs.service; then
    log_info "✓ Axon BBS service is running"
else
    log_error "✗ Axon BBS service failed to start. Check: journalctl -u axon-bbs.service -n 50"
fi

# Display summary
echo ""
echo "========================================"
echo "  Axon BBS Installation Complete!"
echo "========================================"
echo ""
echo "Installation Directory: $INSTALL_DIR"
echo "Virtual Environment: $VENV_DIR"
echo "Database: PostgreSQL ($DB_NAME)"
echo ""
echo "Services:"
echo "  - Axon BBS: systemctl status axon-bbs.service"
echo "  - PostgreSQL: systemctl status postgresql"
echo "  - Tor: systemctl status tor"
echo ""
echo "Access Points:"
echo "  - Local: http://192.168.58.8:8000"
echo "  - Admin: http://192.168.58.8:8000/admin/"
if [ -f /var/lib/tor/axon_bbs/hostname ]; then
    echo "  - Tor: http://$(cat /var/lib/tor/axon_bbs/hostname)"
fi
echo ""
echo "Credentials stored in:"
echo "  - /root/axon_bbs_admin_credentials.txt"
echo "  - /root/axon_bbs_db_credentials.txt"
echo ""
echo "Next steps:"
echo "  1. View admin password: cat /root/axon_bbs_admin_credentials.txt"
echo "  2. Log in to admin panel: http://192.168.58.8:8000/admin/"
echo "  3. Configure trusted peers for federation"
echo "  4. Update applet manifests: cd $INSTALL_DIR && source venv/bin/activate && python manage.py update_applet_manifests"
echo ""
echo "Useful commands:"
echo "  - View logs: journalctl -u axon-bbs.service -f"
echo "  - Restart: systemctl restart axon-bbs.service"
echo "  - Django shell: cd $INSTALL_DIR && source venv/bin/activate && python manage.py shell"
echo ""
echo "========================================"
