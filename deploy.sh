#!/bin/bash
#
# One-Command Deployment Script for Axon BBS
# Run this from your local machine to deploy to the remote WSL instance
#
# Usage: ./deploy.sh [ssh_user@remote_host]
# Example: ./deploy.sh sysadmin@192.168.58.8
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default target
TARGET="${1:-sysadmin@192.168.58.8}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info "Deploying Axon BBS to $TARGET"

# Check if deployment script exists
if [ ! -f "$SCRIPT_DIR/deploy_to_wsl.sh" ]; then
    log_error "deploy_to_wsl.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Check SSH connection
log_info "Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$TARGET" echo "Connected" 2>/dev/null; then
    log_error "Cannot connect to $TARGET"
    log_error "Make sure SSH keys are set up or you can authenticate"
    exit 1
fi

log_info "✓ SSH connection successful"

# Copy deployment script to remote
log_info "Copying deployment script to remote..."
scp "$SCRIPT_DIR/deploy_to_wsl.sh" "$TARGET:/tmp/" || {
    log_error "Failed to copy deployment script"
    exit 1
}

log_info "✓ Deployment script copied"

# Execute deployment on remote
log_info "Starting remote installation..."
log_warn "This will take 5-10 minutes. Please be patient..."

ssh -t "$TARGET" 'sudo bash /tmp/deploy_to_wsl.sh' || {
    log_error "Deployment failed"
    exit 1
}

log_info "✓ Deployment complete!"

# Retrieve credentials
log_info "Retrieving admin credentials..."
echo ""
echo "=========================================="
echo "  ADMIN CREDENTIALS"
echo "=========================================="
ssh "$TARGET" 'sudo cat /root/axon_bbs_admin_credentials.txt' 2>/dev/null || {
    log_warn "Could not retrieve credentials automatically"
    log_info "Run: ssh $TARGET 'sudo cat /root/axon_bbs_admin_credentials.txt'"
}
echo "=========================================="
echo ""

# Get remote IP for convenience
REMOTE_IP=$(echo "$TARGET" | cut -d'@' -f2)
log_info "Access your Axon BBS at:"
log_info "  Local Network: http://$REMOTE_IP:8000"
log_info "  Admin Panel:   http://$REMOTE_IP:8000/admin/"

# Get .onion address if available
ONION=$(ssh "$TARGET" 'sudo cat /var/lib/tor/axon_bbs/hostname 2>/dev/null' || echo "")
if [ -n "$ONION" ]; then
    log_info "  Tor Hidden:    http://$ONION"
fi

echo ""
log_info "Next steps:"
echo "  1. Visit http://$REMOTE_IP:8000/admin/"
echo "  2. Log in with credentials above"
echo "  3. Initialize applets:"
echo "     ssh $TARGET 'sudo -u axon bash -c \"cd /opt/axon_bbs && source venv/bin/activate && python manage.py update_applet_manifests\"'"
echo ""
log_info "View logs: ssh $TARGET 'sudo journalctl -u axon-bbs.service -f'"
log_info "Service status: ssh $TARGET 'sudo systemctl status axon-bbs.service'"
echo ""
log_info "Deployment successful! 🎉"
