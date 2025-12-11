# Azure VM Deployment Guide - Water Report Automation

## Overview

This guide provides comprehensive instructions for deploying the Meras Water Report Automation solution on an Azure Virtual Machine. This approach offers complete control, simplicity, and cost-effectiveness compared to Azure Functions or Container Apps.

## Table of Contents

1. [VM Specifications](#vm-specifications)
2. [Prerequisites](#prerequisites)
3. [Azure VM Setup](#azure-vm-setup)
4. [Environment Configuration](#environment-configuration)
5. [Application Deployment](#application-deployment)
6. [Scheduling with Cron](#scheduling-with-cron)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Cost Optimization](#cost-optimization)

---

## VM Specifications

### Recommended VM Size: **Standard B2s**

**Specifications:**
- **vCPUs:** 2
- **RAM:** 4 GB
- **Temporary Storage:** 8 GB
- **Max Data Disks:** 4
- **Cost:** ~$30-40/month (Pay-as-you-go)

**Why B2s?**
- ✅ Sufficient for Playwright browser automation
- ✅ Handles Python application with headless Chrome
- ✅ Cost-effective for scheduled daily tasks
- ✅ Burstable performance for occasional heavy loads

### Alternative VM Sizes

#### Budget Option: **Standard B1ms**
- **vCPUs:** 1
- **RAM:** 2 GB
- **Cost:** ~$15-20/month
- ⚠️ May struggle with browser automation
- ⚠️ Suitable only for very light workloads

#### Performance Option: **Standard B2ms**
- **vCPUs:** 2
- **RAM:** 8 GB
- **Cost:** ~$60-70/month
- ✅ Better for multiple concurrent operations
- ✅ More headroom for future enhancements

### Operating System: **Ubuntu 22.04 LTS**

**Why Ubuntu?**
- ✅ Free (no Windows licensing costs)
- ✅ Lightweight and efficient
- ✅ Excellent Python and Playwright support
- ✅ Long-term support until 2027

### Storage Configuration

**OS Disk:**
- **Type:** Standard SSD (E10)
- **Size:** 64 GB
- **Cost:** ~$5/month

**Data Disk (Optional):**
- **Type:** Standard HDD (S4)
- **Size:** 32 GB
- **Cost:** ~$2/month
- **Purpose:** Store downloaded reports and logs

---

## Prerequisites

### Azure Account Requirements

- [ ] **Active Azure Subscription**
- [ ] **Sufficient credits** (~$50/month minimum)
- [ ] **Resource Group** (will be created in setup)
- [ ] **SSH Key Pair** (for secure access)

### Local Development Tools

- [ ] **Azure CLI** installed on your local machine
- [ ] **SSH Client** (built-in on macOS/Linux, PuTTY for Windows)
- [ ] **Text Editor** (VS Code recommended for remote editing)

### Existing Configuration

- [ ] **Azure AD App Registration** (from SETUP_GUIDE.md)
  - Tenant ID
  - Client ID
  - Client Secret
- [ ] **SharePoint Site URL** and folder path
- [ ] **Portal Credentials** (username/password)
- [ ] **Email Configuration** (sender and recipient addresses)

---

## Azure VM Setup

### Step 1: Install Azure CLI (if not already installed)

**macOS:**
```bash
brew update && brew install azure-cli
```

**Windows:**
Download from: https://aka.ms/installazurecliwindows

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 2: Login to Azure

```bash
az login
```

This opens a browser for authentication. Select your Azure subscription.

### Step 3: Set Configuration Variables

```bash
# Configuration
RESOURCE_GROUP="WaterReportAutomation-RG"
LOCATION="eastus"  # or your preferred region
VM_NAME="water-report-vm"
VM_SIZE="Standard_B2s"
ADMIN_USERNAME="azureuser"
```

### Step 4: Create Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

**Expected Output:**
```json
{
  "id": "/subscriptions/.../resourceGroups/WaterReportAutomation-RG",
  "location": "eastus",
  "name": "WaterReportAutomation-RG",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

### Step 5: Generate SSH Key Pair (if you don't have one)

```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_water_report_key

# This creates:
# - Private key: ~/.ssh/azure_water_report_key
# - Public key: ~/.ssh/azure_water_report_key.pub
```

> [!IMPORTANT]
> Keep your private key secure! Never share it or commit it to version control.

### Step 6: Create Virtual Machine

```bash
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image Ubuntu2204 \
  --size $VM_SIZE \
  --admin-username $ADMIN_USERNAME \
  --ssh-key-values ~/.ssh/azure_water_report_key.pub \
  --public-ip-sku Standard \
  --storage-sku StandardSSD_LRS \
  --os-disk-size-gb 64 \
  --nsg-rule SSH
```

**This command:**
- Creates Ubuntu 22.04 LTS VM
- Configures SSH access with your public key
- Opens port 22 for SSH
- Uses Standard SSD for OS disk
- Assigns a public IP address

**Expected Output:**
```json
{
  "fqdns": "",
  "id": "/subscriptions/.../virtualMachines/water-report-vm",
  "location": "eastus",
  "macAddress": "...",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "20.XXX.XXX.XXX",
  "resourceGroup": "WaterReportAutomation-RG"
}
```

> [!NOTE]
> Save the `publicIpAddress` - you'll need it to connect to the VM.

### Step 7: Configure Network Security (Optional - for remote access)

If you need to access the VM from specific IPs only:

```bash
# Get your current public IP
MY_IP=$(curl -s ifconfig.me)

# Update NSG to allow SSH only from your IP
az vm open-port \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --port 22 \
  --priority 1000 \
  --source-address-prefixes $MY_IP
```

### Step 8: Connect to VM

```bash
# Get the public IP
VM_IP=$(az vm show \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --show-details \
  --query publicIps \
  --output tsv)

# Connect via SSH
ssh -i ~/.ssh/azure_water_report_key $ADMIN_USERNAME@$VM_IP
```

**First-time connection:**
```
The authenticity of host '20.XXX.XXX.XXX' can't be established.
ECDSA key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no)? yes
```

Type `yes` and press Enter.

---

## Environment Configuration

### Step 9: Update System Packages

Once connected to the VM:

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y
```

### Step 10: Install Python 3.11

```bash
# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3-pip

# Verify installation
python3.11 --version  # Should show: Python 3.11.x
```

### Step 11: Install System Dependencies for Playwright

```bash
# Install required libraries for Chromium
sudo apt install -y \
  libnss3 \
  libnspr4 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libdbus-1-3 \
  libxkbcommon0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libpango-1.0-0 \
  libcairo2 \
  libasound2 \
  libatspi2.0-0 \
  libxshmfence1
```

### Step 12: Install Additional Tools

```bash
# Install Git, curl, and other utilities
sudo apt install -y git curl wget unzip

# Install cron (usually pre-installed)
sudo apt install -y cron
sudo systemctl enable cron
sudo systemctl start cron
```

---

## Application Deployment

### Step 13: Create Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/water-report-automation
sudo chown $USER:$USER /opt/water-report-automation
cd /opt/water-report-automation
```

### Step 14: Transfer Application Files

**Option A: Using SCP (from your local machine)**

Open a new terminal on your **local machine**:

```bash
# Set variables (adjust paths as needed)
VM_IP="<your-vm-public-ip>"
LOCAL_PROJECT_PATH="/Users/apple/Documents/MerasWaterReport"
SSH_KEY="~/.ssh/azure_water_report_key"

# Transfer files
scp -i $SSH_KEY \
  $LOCAL_PROJECT_PATH/water_report_automation.py \
  $LOCAL_PROJECT_PATH/requirements.txt \
  $ADMIN_USERNAME@$VM_IP:/opt/water-report-automation/

# Transfer .env file (contains sensitive data)
scp -i $SSH_KEY \
  $LOCAL_PROJECT_PATH/.env \
  $ADMIN_USERNAME@$VM_IP:/opt/water-report-automation/
```

**Option B: Using Git (if your code is in a private repository)**

On the VM:

```bash
cd /opt/water-report-automation

# Clone your repository
git clone https://github.com/yourusername/water-report-automation.git .

# Create .env file manually
nano .env
```

Then paste your environment variables (see Step 15).

**Option C: Manual File Creation**

On the VM, create files manually:

```bash
cd /opt/water-report-automation

# Create requirements.txt
nano requirements.txt
```

Paste the following:
```
playwright==1.41.0
python-dotenv==1.0.0
requests==2.31.0
msal==1.31.1
```

Save and exit (Ctrl+X, then Y, then Enter).

### Step 15: Create Environment Configuration

```bash
cd /opt/water-report-automation
nano .env
```

Paste your configuration (replace with actual values):

```bash
# Portal Configuration
PORTAL_URL=https://precisionagrilab.com/Portal/Login.aspx
PORTAL_USERNAME=your_username
PORTAL_PASSWORD=your_password

# SharePoint Configuration
SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
SHAREPOINT_FOLDER_PATH=WaterReport
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-client-id
SHAREPOINT_CLIENT_SECRET=your-client-secret

# Email Configuration
EMAIL_SENDER_ADDRESS=sender@domain.com
EMAIL_TO=recipient@domain.com

# Download Path
DOWNLOAD_PATH=/opt/water-report-automation/downloads
```

Save and exit (Ctrl+X, then Y, then Enter).

> [!CAUTION]
> The `.env` file contains sensitive credentials. Ensure proper file permissions:

```bash
chmod 600 .env
```

### Step 16: Create Python Virtual Environment

```bash
cd /opt/water-report-automation

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (prompt should show (venv))
which python  # Should show: /opt/water-report-automation/venv/bin/python
```

### Step 17: Install Python Dependencies

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Expected Output:**
```
Successfully installed playwright-1.41.0 python-dotenv-1.0.0 requests-2.31.0 msal-1.31.1 ...
```

### Step 18: Install Playwright Browsers

```bash
# Install Chromium browser for Playwright
python -m playwright install chromium

# Install system dependencies for Chromium
python -m playwright install-deps chromium
```

**Expected Output:**
```
Downloading Chromium 119.0.6045.9 ...
Chromium 119.0.6045.9 downloaded to /home/azureuser/.cache/ms-playwright/chromium-1084
```

### Step 19: Create Downloads Directory

```bash
mkdir -p /opt/water-report-automation/downloads
```

### Step 20: Update Application for Headless Mode

Since the VM doesn't have a display, we need to run the browser in headless mode.

```bash
nano water_report_automation.py
```

Find this section (around line 677):

```python
browser = await p.chromium.launch(
    channel='chrome',  # Use system Chrome browser
    headless=False,  # Running with visible browser
    slow_mo=100,  # Slow down by 100ms to improve stability
    args=['--start-maximized']  # Launch in maximized window
)
```

Change to:

```python
browser = await p.chromium.launch(
    headless=True,  # Run in headless mode for server
    slow_mo=100,
    args=[
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
    ]
)
```

Also remove the `channel='chrome'` line since we're using Playwright's Chromium.

Save and exit (Ctrl+X, then Y, then Enter).

### Step 21: Test the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python water_report_automation.py
```

**Expected Output:**
```
============================================================
Meras Water Report Automation
============================================================
Start time: 2025-12-09 06:00:00

Navigating to portal: https://precisionagrilab.com/Portal/Login.aspx
Entering credentials...
Login successful!
...
```

> [!NOTE]
> If you encounter errors, check the [Troubleshooting](#troubleshooting) section.

Press Ctrl+C to stop if needed, or let it complete.

---

## Scheduling with Cron

### Step 22: Create Wrapper Script

Create a shell script to run the automation:

```bash
nano /opt/water-report-automation/run_automation.sh
```

Paste the following:

```bash
#!/bin/bash

# Set working directory
cd /opt/water-report-automation

# Activate virtual environment
source venv/bin/activate

# Set display for headless mode
export DISPLAY=:99

# Run the automation
python water_report_automation.py >> /opt/water-report-automation/logs/automation.log 2>&1

# Deactivate virtual environment
deactivate
```

Save and exit.

Make it executable:

```bash
chmod +x /opt/water-report-automation/run_automation.sh
```

### Step 23: Create Logs Directory

```bash
mkdir -p /opt/water-report-automation/logs
```

### Step 24: Configure Cron Job

```bash
# Edit crontab
crontab -e
```

If prompted to select an editor, choose `nano` (usually option 1).

Add the following line to run daily at 8:00 AM IST (2:30 AM UTC):

```bash
# Water Report Automation - Daily at 8:00 AM IST (2:30 AM UTC)
30 2 * * * /opt/water-report-automation/run_automation.sh
```

**Cron Schedule Explanation:**
- `30` - Minute (30)
- `2` - Hour (2 AM UTC = 7:30 AM IST)
- `*` - Day of month (every day)
- `*` - Month (every month)
- `*` - Day of week (every day)

> [!TIP]
> Adjust the time according to your timezone. Use [crontab.guru](https://crontab.guru/) to help create cron expressions.

Save and exit (Ctrl+X, then Y, then Enter).

### Step 25: Verify Cron Job

```bash
# List cron jobs
crontab -l
```

**Expected Output:**
```
# Water Report Automation - Daily at 8:00 AM IST (2:30 AM UTC)
30 2 * * * /opt/water-report-automation/run_automation.sh
```

### Step 26: Test Cron Job Manually

```bash
# Run the script manually to test
/opt/water-report-automation/run_automation.sh

# Check the log file
tail -f /opt/water-report-automation/logs/automation.log
```

Press Ctrl+C to stop tailing the log.

---

## Monitoring and Maintenance

### Step 27: Set Up Log Rotation

Prevent log files from growing too large:

```bash
sudo nano /etc/logrotate.d/water-report-automation
```

Paste the following:

```
/opt/water-report-automation/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 azureuser azureuser
}
```

Save and exit.

### Step 28: Create Monitoring Script

Create a script to check automation health:

```bash
nano /opt/water-report-automation/check_health.sh
```

Paste the following:

```bash
#!/bin/bash

LOG_FILE="/opt/water-report-automation/logs/automation.log"
ALERT_EMAIL="your-email@domain.com"

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found!" | mail -s "Water Report Automation - Log Missing" $ALERT_EMAIL
    exit 1
fi

# Check last run time (should be within last 25 hours)
LAST_RUN=$(stat -c %Y "$LOG_FILE")
CURRENT_TIME=$(date +%s)
TIME_DIFF=$((CURRENT_TIME - LAST_RUN))

if [ $TIME_DIFF -gt 90000 ]; then  # 25 hours in seconds
    echo "Automation hasn't run in over 25 hours!" | mail -s "Water Report Automation - Alert" $ALERT_EMAIL
fi

# Check for errors in last run
if grep -q "ERROR\|FAILED" "$LOG_FILE"; then
    tail -50 "$LOG_FILE" | mail -s "Water Report Automation - Errors Detected" $ALERT_EMAIL
fi
```

Save and exit.

Make it executable:

```bash
chmod +x /opt/water-report-automation/check_health.sh
```

### Step 29: View Logs

**View latest log entries:**
```bash
tail -100 /opt/water-report-automation/logs/automation.log
```

**Follow log in real-time:**
```bash
tail -f /opt/water-report-automation/logs/automation.log
```

**Search for errors:**
```bash
grep -i error /opt/water-report-automation/logs/automation.log
```

**View logs from specific date:**
```bash
grep "2025-12-09" /opt/water-report-automation/logs/automation.log
```

### Step 30: Set Up Azure Monitoring (Optional)

Enable Azure Monitor for the VM:

```bash
# From your local machine
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name OmsAgentForLinux \
  --publisher Microsoft.EnterpriseCloud.Monitoring \
  --version 1.14
```

This enables:
- CPU and memory monitoring
- Disk usage tracking
- Network metrics
- Custom log collection

---

## Troubleshooting

### Issue 1: Playwright Browser Fails to Launch

**Symptoms:**
```
playwright._impl._api_types.Error: Executable doesn't exist at /home/azureuser/.cache/ms-playwright/chromium-1084/chrome-linux/chrome
```

**Solution:**
```bash
# Reinstall Playwright browsers
source /opt/water-report-automation/venv/bin/activate
python -m playwright install chromium
python -m playwright install-deps chromium
```

### Issue 2: Permission Denied Errors

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/opt/water-report-automation/downloads'
```

**Solution:**
```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/water-report-automation
chmod -R 755 /opt/water-report-automation
chmod 600 /opt/water-report-automation/.env
```

### Issue 3: Cron Job Not Running

**Symptoms:**
- No log entries at scheduled time
- Automation doesn't execute

**Solution:**

1. Check cron service status:
```bash
sudo systemctl status cron
```

2. Check cron logs:
```bash
sudo grep CRON /var/log/syslog
```

3. Verify crontab:
```bash
crontab -l
```

4. Test script manually:
```bash
/opt/water-report-automation/run_automation.sh
```

5. Check script permissions:
```bash
ls -l /opt/water-report-automation/run_automation.sh
# Should show: -rwxr-xr-x
```

### Issue 4: Out of Memory Errors

**Symptoms:**
```
Killed
```
or
```
MemoryError
```

**Solution:**

1. Check memory usage:
```bash
free -h
```

2. Add swap space:
```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

3. Or upgrade to B2ms (8GB RAM):
```bash
az vm resize \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --size Standard_B2ms
```

### Issue 5: Network Connectivity Issues

**Symptoms:**
```
Failed to connect to portal
TimeoutError
```

**Solution:**

1. Check internet connectivity:
```bash
ping -c 4 google.com
curl -I https://precisionagrilab.com
```

2. Check DNS resolution:
```bash
nslookup precisionagrilab.com
```

3. Check firewall rules:
```bash
sudo ufw status
```

4. Verify NSG rules in Azure Portal

### Issue 6: SharePoint Upload Fails

**Symptoms:**
```
Failed to upload to SharePoint: HTTP 401
Authentication error
```

**Solution:**

1. Verify credentials in `.env`:
```bash
cat /opt/water-report-automation/.env | grep SHAREPOINT
```

2. Test Graph API authentication:
```bash
source /opt/water-report-automation/venv/bin/activate
python -c "
from water_report_automation import WaterReportAutomation
automation = WaterReportAutomation()
token = automation._get_graph_token()
print('Token obtained!' if token else 'Authentication failed!')
"
```

3. Check Azure AD app permissions (see SETUP_GUIDE.md)

### Issue 7: Email Notifications Not Sending

**Symptoms:**
- No email received after automation runs
- Email errors in logs

**Solution:**

1. Verify email configuration:
```bash
cat /opt/water-report-automation/.env | grep EMAIL
```

2. Check sender has mailbox and permissions

3. Verify Graph API permissions include `Mail.Send`

---

## Cost Optimization

### Estimated Monthly Costs

**Standard B2s Configuration:**
- **VM (B2s):** ~$30-40/month
- **OS Disk (64GB SSD):** ~$5/month
- **Public IP:** ~$3/month
- **Bandwidth:** ~$1-2/month (minimal)
- **Total:** ~$40-50/month

### Ways to Reduce Costs

#### 1. Auto-Shutdown During Off-Hours

```bash
# From your local machine
az vm auto-shutdown \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --time 2000 \
  --timezone "India Standard Time"
```

This shuts down the VM at 8:00 PM IST daily. You'll need to start it manually or via automation.

#### 2. Use Reserved Instances

Save up to 72% with 1-year or 3-year commitments:

```bash
az vm reservation create \
  --resource-group $RESOURCE_GROUP \
  --vm-size Standard_B2s \
  --term P1Y \
  --location eastus
```

#### 3. Downgrade to B1ms (if performance allows)

```bash
az vm resize \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --size Standard_B1ms
```

**Savings:** ~$15-20/month

> [!WARNING]
> B1ms may not have enough resources for reliable browser automation.

#### 4. Use Spot Instances (Not Recommended for Production)

Spot instances can save up to 90% but can be evicted anytime:

```bash
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --priority Spot \
  --max-price -1 \
  --eviction-policy Deallocate \
  ...
```

> [!CAUTION]
> Only use Spot instances for non-critical workloads.

#### 5. Use Standard HDD Instead of SSD

```bash
# When creating VM, use:
--storage-sku Standard_LRS  # instead of StandardSSD_LRS
```

**Savings:** ~$3/month

> [!NOTE]
> May impact boot time and disk performance.

### Cost Monitoring

**Set up budget alerts:**

```bash
az consumption budget create \
  --budget-name water-report-budget \
  --amount 100 \
  --time-grain Monthly \
  --start-date 2025-12-01 \
  --end-date 2026-12-01 \
  --resource-group $RESOURCE_GROUP
```

**View current costs:**

```bash
az consumption usage list \
  --start-date 2025-12-01 \
  --end-date 2025-12-31 \
  --query "[?contains(instanceName, '$VM_NAME')]"
```

---

## Backup and Disaster Recovery

### Create VM Snapshot

```bash
# Stop the VM (recommended)
az vm deallocate \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME

# Create snapshot
az snapshot create \
  --resource-group $RESOURCE_GROUP \
  --name water-report-vm-snapshot-$(date +%Y%m%d) \
  --source $(az vm show \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --query storageProfile.osDisk.managedDisk.id \
    --output tsv)

# Start the VM
az vm start \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME
```

### Backup Application Files

```bash
# On the VM
cd /opt/water-report-automation

# Create backup
tar -czf ~/water-report-backup-$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='downloads' \
  --exclude='logs' \
  .

# Download to local machine (from local terminal)
scp -i ~/.ssh/azure_water_report_key \
  $ADMIN_USERNAME@$VM_IP:~/water-report-backup-*.tar.gz \
  ~/Downloads/
```

---

## Security Best Practices

### 1. Disable Password Authentication

```bash
# On the VM
sudo nano /etc/ssh/sshd_config
```

Ensure these settings:
```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

### 2. Enable Firewall

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Check status
sudo ufw status
```

### 3. Keep System Updated

```bash
# Create update script
sudo nano /opt/update-system.sh
```

Paste:
```bash
#!/bin/bash
apt update
apt upgrade -y
apt autoremove -y
```

Make executable and schedule:
```bash
sudo chmod +x /opt/update-system.sh

# Add to crontab (weekly updates on Sunday at 3 AM)
sudo crontab -e
```

Add:
```
0 3 * * 0 /opt/update-system.sh >> /var/log/system-updates.log 2>&1
```

### 4. Secure Environment Variables

```bash
# Ensure .env is not readable by others
chmod 600 /opt/water-report-automation/.env

# Verify
ls -l /opt/water-report-automation/.env
# Should show: -rw------- (600)
```

---

## Summary

### What You've Deployed

✅ **Azure VM** running Ubuntu 22.04 LTS  
✅ **Python 3.11** environment with all dependencies  
✅ **Playwright** with Chromium browser  
✅ **Automated scheduling** via cron  
✅ **Logging and monitoring** setup  
✅ **Secure configuration** with SSH keys  

### Daily Workflow

1. **8:00 AM IST** - Cron triggers automation
2. **Automation runs:**
   - Logs into portal
   - Downloads previous day's water reports
   - Uploads to SharePoint
   - Sends email notification
3. **Logs saved** to `/opt/water-report-automation/logs/`
4. **Email notification** sent with results

### Next Steps

1. ✅ Monitor first few scheduled runs
2. ✅ Review logs for any issues
3. ✅ Set up cost alerts
4. ✅ Configure backup schedule
5. ✅ Document any custom configurations

### Support Resources

- **Azure VM Documentation:** https://docs.microsoft.com/azure/virtual-machines/
- **Playwright Documentation:** https://playwright.dev/python/
- **Ubuntu Server Guide:** https://ubuntu.com/server/docs
- **Cron Documentation:** https://man7.org/linux/man-pages/man5/crontab.5.html

---

## Quick Reference Commands

### VM Management

```bash
# Start VM
az vm start --resource-group $RESOURCE_GROUP --name $VM_NAME

# Stop VM (deallocate to save costs)
az vm deallocate --resource-group $RESOURCE_GROUP --name $VM_NAME

# Restart VM
az vm restart --resource-group $RESOURCE_GROUP --name $VM_NAME

# Check VM status
az vm get-instance-view --resource-group $RESOURCE_GROUP --name $VM_NAME --query instanceView.statuses[1]

# Connect to VM
ssh -i ~/.ssh/azure_water_report_key azureuser@<VM_IP>
```

### Application Management

```bash
# Run automation manually
/opt/water-report-automation/run_automation.sh

# View logs
tail -f /opt/water-report-automation/logs/automation.log

# Check cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Test Python environment
source /opt/water-report-automation/venv/bin/activate
python --version
pip list
```

### Monitoring

```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check running processes
ps aux | grep python

# Check system logs
sudo tail -f /var/log/syslog
```

---

## Comparison: VM vs Azure Functions vs Container Apps

| Feature | Azure VM | Azure Functions | Container Apps |
|---------|----------|-----------------|----------------|
| **Cost** | ~$40-50/month | ~$165-175/month | ~$50-100/month |
| **Setup Complexity** | Medium | High | High |
| **Maintenance** | Manual | Managed | Managed |
| **Scalability** | Manual | Automatic | Automatic |
| **Execution Time** | Unlimited | 20 min (Premium) | Unlimited |
| **Browser Support** | Excellent | Limited | Excellent |
| **Best For** | Scheduled tasks | Event-driven | Containerized apps |

**Recommendation:** Azure VM is the best choice for this use case due to:
- ✅ Cost-effectiveness
- ✅ Simplicity
- ✅ Full control
- ✅ Excellent Playwright support
- ✅ No execution time limits

---

*Last Updated: December 9, 2025*
