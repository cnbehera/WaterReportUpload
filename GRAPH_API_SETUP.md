# Microsoft Graph API Setup Guide

## Overview

The automation now uses Microsoft Graph API for both SharePoint upload and email sending with Azure AD app registration for secure, modern authentication.

## Setup Steps

### 1. Register an Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Enter application name (e.g., "Water Report Automation")
5. Select **Accounts in this organizational directory only**
6. Click **Register**

### 2. Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Application permissions**
5. Add these permissions:
   - `Sites.ReadWrite.All` (for SharePoint upload)
   - `Files.ReadWrite.All` (for SharePoint upload)
   - `Mail.Send` (for email notifications)
6. Click **Grant admin consent** (requires admin)

### 3. Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add description (e.g., "Water Report Automation Secret")
4. Choose expiration period
5. Click **Add**
6. **IMPORTANT:** Copy the secret value immediately (you won't see it again)

### 4. Get Required IDs

**Tenant ID:**
- Found in **Azure Active Directory** > **Overview** > **Tenant ID**

**Client ID (Application ID):**
- Found in your app registration **Overview** > **Application (client) ID**

**SharePoint Site URL:**
- Your SharePoint site URL, e.g., `https://bloomsmobility.sharepoint.com/sites/internalApp`

**Folder Path:**
- Just the folder name, e.g., `WaterReport` or `Water Reports`
- Do NOT include `/Shared Documents/` or leading slashes

**Email Sender Address:**
- The email address that will send notifications
- Must be a valid mailbox in your Microsoft 365 tenant
- Can be a user account or shared mailbox
- Example: `waterreports@bloomsmobility.onmicrosoft.com` or `service-account@bloomsmobility.com`

### 5. Update .env File

```bash
# SharePoint Configuration (Microsoft Graph API)
SHAREPOINT_SITE_URL=https://bloomsmobility.sharepoint.com/sites/internalApp
SHAREPOINT_FOLDER_PATH=WaterReport
SHAREPOINT_TENANT_ID=93763517-5ec9-4e25-836b-621f1916f963
SHAREPOINT_CLIENT_ID=70b646d2-fbb9-42f1-bb06-2251f930f905
SHAREPOINT_CLIENT_SECRET=your_client_secret_here

# Email Configuration (Microsoft Graph API)
EMAIL_SENDER_ADDRESS=waterreports@bloomsmobility.onmicrosoft.com
EMAIL_TO=recipient@example.com
```

## Features

### SharePoint Upload
- Automatically uploads downloaded water reports to SharePoint
- Creates folder structure if it doesn't exist
- Uses secure OAuth 2.0 authentication

### Email Notifications
- Sends HTML-formatted email notifications via Graph API
- Color-coded status indicators (green for success, red for errors, etc.)
- Detailed summary of downloaded and uploaded files
- Error reporting if any issues occur

## Testing

Run the automation to test SharePoint upload:

```bash
python3 water_report_automation.py
```

## Troubleshooting

### "Failed to acquire access token"
- Verify tenant ID, client ID, and client secret are correct
- Ensure client secret hasn't expired
- Check that admin consent was granted for API permissions

### "Failed to get site information"
- Verify SharePoint site URL format: `https://tenant.sharepoint.com/sites/sitename`
- Ensure the app has `Sites.ReadWrite.All` permission

### "Failed to get document library"
- The site must have a default document library
- Verify `Files.ReadWrite.All` permission is granted

### "Error uploading file"
- Check folder path doesn't include `/Shared Documents/`
- Folder will be created automatically if it doesn't exist
- Verify file isn't locked or checked out in SharePoint

### "Email configuration missing"
- Ensure `EMAIL_SENDER_ADDRESS` and `EMAIL_TO` are set in .env
- Verify sender email address is a valid mailbox in your tenant

### "Failed to send email"
- Verify `Mail.Send` permission is granted with admin consent
- Check that sender email address exists and is accessible
- Ensure the mailbox is not disabled or restricted

## Security Notes

- Client secret should be kept secure and never committed to version control
- Consider using Azure Key Vault for production deployments
- Rotate client secrets periodically
- Use least-privilege permissions (only what's needed)
