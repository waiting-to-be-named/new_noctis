# NOCTIS DICOM Viewer - Ubuntu 18.04 Quick Start Guide

## 🚀 Quick Deployment (10-15 minutes)

This guide will get NOCTIS DICOM Viewer running on Ubuntu 18.04 VM quickly.

## Prerequisites
- Ubuntu 18.04 VM with internet access
- At least 4GB RAM and 50GB storage
- sudo/root access

## Step 1: Prepare Your VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git wget curl
```

## Step 2: Download and Run Deployment Script

```bash
# Clone or download the application
# Option A: If you have git access
git clone <your-repo-url> noctis-viewer
cd noctis-viewer

# Option B: If you have the files locally, transfer them
# From your local machine:
scp -r /path/to/noctis-viewer/ user@vm-ip:/home/user/

# On the VM:
cd ~/noctis-viewer

# Make deployment script executable
chmod +x deploy_ubuntu_18.04.sh

# Run the deployment script
sudo ./deploy_ubuntu_18.04.sh
```

## Step 3: Create Admin User

When prompted during deployment, create your admin user:
- Username: admin (or your choice)
- Email: your-email@example.com
- Password: (choose a strong password)

## Step 4: Access the Application

After deployment completes, you'll see output like:
```
Application URL: http://192.168.1.100
Django Admin: http://192.168.1.100/admin
```

Open your browser and navigate to the URL shown.

## 🔧 Common VM Network Configurations

### VirtualBox Users

#### Option A: Bridged Network (Recommended)
1. VM Settings → Network → Adapter 1
2. Attached to: Bridged Adapter
3. Name: (select your network adapter)

#### Option B: NAT with Port Forwarding
1. VM Settings → Network → Adapter 1 → Advanced → Port Forwarding
2. Add rules:
   - Name: HTTP, Host Port: 8080, Guest Port: 80
   - Name: DICOM, Host Port: 11112, Guest Port: 11112
3. Access via: http://localhost:8080

### VMware Users
1. VM Settings → Network Adapter → Bridged
2. Or use NAT and configure port forwarding in Virtual Network Editor

## 📋 Post-Installation Checklist

✅ **Test Web Access**
```bash
# From the VM
curl http://localhost

# From your host machine
# Replace with your VM's IP
curl http://192.168.1.100
```

✅ **Check Services**
```bash
sudo systemctl status noctis
sudo systemctl status nginx
sudo systemctl status noctis-scp
```

✅ **Upload Test DICOM**
1. Go to http://your-vm-ip
2. Click on "Upload DICOM"
3. Select a .dcm file
4. Verify it appears in worklist

## 🛠️ Troubleshooting

### Can't access from host machine?
```bash
# Check VM IP address
ip addr show

# Check firewall
sudo ufw status

# If firewall is blocking:
sudo ufw allow 80/tcp
sudo ufw allow 11112/tcp
```

### Services not starting?
```bash
# Check logs
sudo journalctl -u noctis -n 50
sudo tail -f /opt/noctis/logs/django.log

# Restart services
sudo systemctl restart noctis
sudo systemctl restart nginx
```

### Database issues?
```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Reset database (WARNING: deletes all data)
sudo -u postgres dropdb noctis_db
sudo -u postgres createdb noctis_db
# Then re-run migrations
```

## 📱 Quick Commands Reference

```bash
# Service management
sudo systemctl start|stop|restart|status noctis
sudo systemctl start|stop|restart|status noctis-scp

# View logs
tail -f /opt/noctis/logs/django.log
sudo journalctl -u noctis -f

# Update application
cd /opt/noctis
sudo -u noctis git pull
sudo -u noctis venv/bin/pip install -r requirements.txt
sudo -u noctis venv/bin/python manage.py migrate
sudo systemctl restart noctis

# Backup database
pg_dump -U noctis_user -h localhost noctis_db > backup.sql
```

## 🔐 Default Credentials

After installation, you'll have:
- **Django Admin**: Use the superuser you created
- **Database**: 
  - User: noctis_user
  - Password: (shown in deployment output - SAVE IT!)
- **DICOM SCP**:
  - AE Title: NOCTIS_SCP
  - Port: 11112

## 💡 Tips for VM Performance

1. **Allocate adequate resources**:
   - CPU: 2-4 cores
   - RAM: 4-8 GB
   - Enable VT-x/AMD-V in BIOS

2. **Install VM tools**:
   ```bash
   # VirtualBox
   sudo apt install -y virtualbox-guest-dkms virtualbox-guest-utils
   
   # VMware
   sudo apt install -y open-vm-tools
   ```

3. **Use SSD** for VM storage if possible

## 🆘 Need Help?

1. Check the detailed guide: `UBUNTU_18.04_DEPLOYMENT.md`
2. Review logs in `/opt/noctis/logs/`
3. Verify all services are running
4. Ensure network connectivity

---

**Quick Start Complete!** 🎉

Your NOCTIS DICOM Viewer should now be running on Ubuntu 18.04.

Access it at: `http://YOUR_VM_IP`