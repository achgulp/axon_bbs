# Axon BBS Deployment Guide for Ubuntu 24.04 WSL

## Quick Start

Deploy Axon BBS to a fresh Ubuntu 24.04 WSL instance in 5 minutes:

```bash
# From your local machine
cd /home/dukejer/axon_bbs
scp deploy_to_wsl.sh sysadmin@192.168.58.8:/tmp/
ssh sysadmin@192.168.58.8 'sudo bash /tmp/deploy_to_wsl.sh'
```

That's it! The script will:
- ✓ Install all dependencies (Python, PostgreSQL, Node.js, Tor, Git)
- ✓ Clone the Axon BBS repository
- ✓ Set up PostgreSQL database with secure random password
- ✓ Configure Python virtual environment
- ✓ Run Django migrations
- ✓ Build React frontend
- ✓ Configure Tor hidden service
- ✓ Create systemd service
- ✓ Start Axon BBS

## Post-Installation

### 1. Retrieve Credentials

```bash
ssh sysadmin@192.168.58.8 'sudo cat /root/axon_bbs_admin_credentials.txt'
```

This shows:
- Django admin username and password
- Web interface URL
- Tor hidden service .onion address

### 2. Access the Admin Panel

```
http://192.168.58.8:8000/admin/
```

Log in with the credentials from step 1.

### 3. Initialize Applets

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon bash -c "cd /opt/axon_bbs && source venv/bin/activate && python manage.py update_applet_manifests"'
```

### 4. Configure Federation (Optional)

If you want to federate with other Axon BBS instances:

1. Go to Admin → Trusted Instances → Add
2. Enter the peer's .onion URL
3. Mark as "Is Trusted Peer"
4. Save

## Service Management

### Check Service Status

```bash
ssh sysadmin@192.168.58.8 'sudo systemctl status axon-bbs.service'
```

### View Logs

```bash
ssh sysadmin@192.168.58.8 'sudo journalctl -u axon-bbs.service -f'
```

### Restart Service

```bash
ssh sysadmin@192.168.58.8 'sudo systemctl restart axon-bbs.service'
```

### Stop Service

```bash
ssh sysadmin@192.168.58.8 'sudo systemctl stop axon-bbs.service'
```

## File Locations

| Item | Location |
|------|----------|
| Installation Directory | `/opt/axon_bbs` |
| Virtual Environment | `/opt/axon_bbs/venv` |
| Configuration File | `/opt/axon_bbs/.env` |
| Admin Credentials | `/root/axon_bbs_admin_credentials.txt` |
| Database Credentials | `/root/axon_bbs_db_credentials.txt` |
| Tor Hidden Service | `/var/lib/tor/axon_bbs/` |
| Systemd Service | `/etc/systemd/system/axon-bbs.service` |
| Logs | `journalctl -u axon-bbs.service` |

## Common Tasks

### Update Axon BBS Code

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon bash -c "cd /opt/axon_bbs && git pull && source venv/bin/activate && pip install -r requirements.txt && cd frontend && npm install && npm run build && cd .. && python manage.py migrate && python manage.py collectstatic --noinput"'
ssh sysadmin@192.168.58.8 'sudo systemctl restart axon-bbs.service'
```

### Backup Database

```bash
ssh sysadmin@192.168.58.8 'sudo -u postgres pg_dump axon_bbs > ~/axon_bbs_backup_$(date +%Y%m%d).sql'
```

### Backup Applets

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon bash -c "cd /opt/axon_bbs && source venv/bin/activate && python manage.py backup_applets --output /home/axon/backups"'
```

### Run Django Shell

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon bash -c "cd /opt/axon_bbs && source venv/bin/activate && python manage.py shell"'
```

### Create Additional Admin User

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon bash -c "cd /opt/axon_bbs && source venv/bin/activate && python manage.py createsuperuser"'
```

## Troubleshooting

### Service Won't Start

Check the logs:
```bash
ssh sysadmin@192.168.58.8 'sudo journalctl -u axon-bbs.service -n 100'
```

Common issues:
- Database not running: `sudo systemctl status postgresql`
- Tor not running: `sudo systemctl status tor`
- Port 8000 in use: `sudo lsof -i :8000`

### Can't Access Web Interface

1. Check if service is running:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo systemctl status axon-bbs.service'
   ```

2. Check if port is listening:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo ss -tlnp | grep 8000'
   ```

3. Check firewall (if enabled):
   ```bash
   ssh sysadmin@192.168.58.8 'sudo ufw status'
   ```

### Database Connection Errors

1. Check PostgreSQL is running:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo systemctl status postgresql'
   ```

2. Verify database credentials:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo cat /root/axon_bbs_db_credentials.txt'
   ```

3. Test database connection:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo -u postgres psql -d axon_bbs -c "SELECT 1;"'
   ```

### Tor Hidden Service Not Working

1. Check Tor is running:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo systemctl status tor'
   ```

2. Get .onion address:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo cat /var/lib/tor/axon_bbs/hostname'
   ```

3. Check Tor logs:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo journalctl -u tor -f'
   ```

## Configuration

### Environment Variables

Edit `/opt/axon_bbs/.env`:

```bash
ssh sysadmin@192.168.58.8 'sudo -u axon nano /opt/axon_bbs/.env'
```

Important variables:
- `SECRET_KEY` - Django secret (auto-generated)
- `DEBUG` - Set to `False` for production
- `ALLOWED_HOSTS` - Add your domain/IP
- `DATABASE_URL` - PostgreSQL connection string
- `TOR_PROXY` - Tor SOCKS5 proxy (default: `socks5h://127.0.0.1:9050`)
- `ONION_ADDRESS` - Your .onion address

After changing .env, restart the service:
```bash
ssh sysadmin@192.168.58.8 'sudo systemctl restart axon-bbs.service'
```

## Uninstallation

To completely remove Axon BBS:

```bash
ssh sysadmin@192.168.58.8 'sudo bash' <<'EOF'
systemctl stop axon-bbs.service
systemctl disable axon-bbs.service
rm -f /etc/systemd/system/axon-bbs.service
systemctl daemon-reload
rm -rf /opt/axon_bbs
userdel -r axon
sudo -u postgres dropdb axon_bbs
sudo -u postgres dropuser axon
rm -f /root/axon_bbs_*.txt
sed -i '/# Axon BBS Hidden Service/,+2d' /etc/tor/torrc
systemctl restart tor
rm -rf /var/lib/tor/axon_bbs
echo "Axon BBS uninstalled"
EOF
```

## Security Recommendations

1. **Change default admin password** immediately after installation
2. **Enable firewall**:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo ufw allow 8000/tcp && sudo ufw enable'
   ```
3. **Set up HTTPS** with nginx reverse proxy (for clearnet access)
4. **Regular backups** - Automate database and applet backups
5. **Keep updated** - Regularly pull latest code and update dependencies
6. **Monitor logs** - Set up log monitoring/alerting

## Federation Setup

To federate with other instances:

1. Get your .onion address:
   ```bash
   ssh sysadmin@192.168.58.8 'sudo cat /var/lib/tor/axon_bbs/hostname'
   ```

2. Log in to admin panel: http://192.168.58.8:8000/admin/

3. Go to: Trusted Instances → Add trusted instance

4. Enter peer's .onion URL (e.g., `http://xnjzv3k7...mhid.onion`)

5. Check "Is trusted peer"

6. Save

7. Messages and applets will now sync with the peer!

## Performance Tuning

For production deployments:

1. **Increase Gunicorn workers** (in `/etc/systemd/system/axon-bbs.service`):
   ```
   ExecStart=/opt/axon_bbs/venv/bin/gunicorn --workers 8 --bind 0.0.0.0:8000 axon_project.wsgi:application
   ```

2. **Enable PostgreSQL connection pooling** (in `.env`):
   ```
   DATABASE_URL=postgresql://axon:password@localhost:5432/axon_bbs?options=-c%20work_mem%3D64MB
   ```

3. **Use nginx** as reverse proxy for static files

4. **Enable caching** with Redis

## Maintenance Schedule

Recommended maintenance tasks:

| Task | Frequency | Command |
|------|-----------|---------|
| Update code | Weekly | `git pull && systemctl restart axon-bbs` |
| Backup database | Daily | `pg_dump axon_bbs > backup.sql` |
| Backup applets | Daily | `python manage.py backup_applets` |
| Check logs | Daily | `journalctl -u axon-bbs.service -n 100` |
| Update dependencies | Monthly | `pip install -r requirements.txt --upgrade` |
| Clean old logs | Monthly | `journalctl --vacuum-time=30d` |

## Support

For issues or questions:
- Check logs: `journalctl -u axon-bbs.service -f`
- Review documentation in `/opt/axon_bbs/docs/`
- GitHub Issues: https://github.com/achgulp/axon_bbs/issues

## Version Information

- **Axon BBS Version**: 10.30.0+
- **Python**: 3.12
- **Django**: 5.0.6
- **PostgreSQL**: 14+
- **Node.js**: 18+
- **Tor**: Latest from Ubuntu repos

---

**Installation Date**: $(date)
**Deployed By**: $(whoami)
**Target System**: Ubuntu 24.04 (WSL) @ 192.168.58.8
