# Water Report Automation - Complete Setup Guide

## Overview

This guide provides step-by-step instructions for setting up the Water Report Automation in a new environment. The automation uses Microsoft Graph API for SharePoint uploads and email notifications, requiring Azure AD app registration and proper permissions.

---

## Prerequisites

Before starting, ensure you have:

- [ ] **Azure AD Admin Access** - Required to create app registrations and grant admin consent
- [ ] **Microsoft 365 Tenant** - With SharePoint Online and Exchange Online
- [ ] **Python 3.8+** installed on the system
- [ ] **Google Chrome** browser installed (for Playwright automation)
- [ ] **Portal Credentials** - Access to Precision Agri-Lab portal
- [ ] **SharePoint Site** - Existing SharePoint site where reports will be uploaded
- [ ] **Email Account** - Valid mailbox in your M365 tenant for sending notifications

---

## Part 1: Azure AD App Registration

### Step 1: Access Azure Portal

1. Navigate to [https://portal.azure.com](https://portal.azure.com)
2. Sign in with your Azure AD admin account
3. In the search bar at the top, type **"Azure Active Directory"**
4. Click on **Azure Active Directory** from the results

### Step 2: Create New App Registration

1. In the left sidebar, click **App registrations**
2. Click **+ New registration** button at the top

   **Fill in the registration form:**
   
   - **Name:** `Water Report Automation`
   - **Supported account types:** Select **"Accounts in this organizational directory only (Single tenant)"**
   - **Redirect URI:** Leave blank (not needed for this application)

3. Click **Register** button at the bottom

### Step 3: Copy Application IDs

After registration, you'll see the app's Overview page.

![Azure App Overview](file:///Users/apple/.gemini/antigravity/brain/301e6aa3-6476-44bf-a5be-305eb5183ecb/azure_app_overview_1764642350480.png)

**Copy and save these values** (you'll need them for the `.env` file):

1. **Application (client) ID**
   - Click the copy icon next to the ID
   - Save as: `SHAREPOINT_CLIENT_ID`

2. **Directory (tenant) ID**
   - Click the copy icon next to the ID
   - Save as: `SHAREPOINT_TENANT_ID`

---

## Part 2: Configure API Permissions

### Step 4: Add Microsoft Graph Permissions

1. In the left sidebar, click **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Choose **Application permissions** (NOT Delegated permissions)

**Add the following three permissions:**

**For SharePoint Upload:**
- Search for `Sites.ReadWrite.All` and check it
- Click **Add permissions**
- Repeat: Search for `Files.ReadWrite.All` and check it
- Click **Add permissions**

**For Email Sending:**
- Search for `Mail.Send` and check it
- Click **Add permissions**

### Step 5: Grant Admin Consent

> [!IMPORTANT]
> This step requires Azure AD admin privileges.

1. After adding all three permissions, you'll see them listed in the permissions table
2. Click the **Grant admin consent for [Your Organization]** button
3. Click **Yes** to confirm

![Azure API Permissions](file:///Users/apple/.gemini/antigravity/brain/301e6aa3-6476-44bf-a5be-305eb5183ecb/azure_api_permissions_1764642366344.png)

**Verify:** All three permissions should show a green checkmark under "Status" column:
- ✅ Sites.ReadWrite.All
- ✅ Files.ReadWrite.All
- ✅ Mail.Send

---

## Part 3: Create Client Secret

### Step 6: Generate Client Secret

1. In the left sidebar, click **Certificates & secrets**
2. Click the **Client secrets** tab
3. Click **+ New client secret**

   **Configure the secret:**
   - **Description:** `Water Report Automation Secret`
   - **Expires:** Choose expiration period (recommended: 24 months)

4. Click **Add**

### Step 7: Copy Client Secret Value

> [!CAUTION]
> The secret value is only shown ONCE. Copy it immediately!

1. After creation, you'll see the new secret in the table
2. Click the **Copy** icon next to the **Value** field (NOT the Secret ID)
3. Save this value as: `SHAREPOINT_CLIENT_SECRET`

**Important Notes:**
- The value will look like: `aKh8Q~xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- You cannot retrieve this value later - if lost, you must create a new secret
- Set a calendar reminder to rotate the secret before it expires

---

## Part 4: Get SharePoint Information

### Step 8: Identify SharePoint Site URL

1. Navigate to your SharePoint site in a browser
2. Copy the URL from the address bar

**URL Format:**
```
https://[tenant].sharepoint.com/sites/[sitename]
```

**Example:**
```
https://bloomsmobility.sharepoint.com/sites/internalApp
```

Save as: `SHAREPOINT_SITE_URL`

### Step 9: Determine Folder Path

1. Navigate to the document library where reports should be uploaded
2. Note the folder name where you want reports stored

**Important:**
- Use ONLY the folder name, not the full path
- Do NOT include `/Shared Documents/` or leading slashes
- The folder will be created automatically if it doesn't exist

**Examples:**
- ✅ Correct: `WaterReport`
- ✅ Correct: `Water Reports`
- ❌ Wrong: `/Shared Documents/WaterReport`
- ❌ Wrong: `/WaterReport`

Save as: `SHAREPOINT_FOLDER_PATH`

---

## Part 5: Configure Email Settings

### Step 10: Identify Email Sender

Determine which email address will send the notifications.

**Options:**
1. **User Account:** `user@yourdomain.com`
2. **Shared Mailbox:** `waterreports@yourdomain.com`
3. **Service Account:** `automation@yourdomain.onmicrosoft.com`

**Requirements:**
- Must be a valid mailbox in your Microsoft 365 tenant
- Must be accessible (not disabled or restricted)
- Recommended: Create a dedicated service account or shared mailbox

Save as: `EMAIL_SENDER_ADDRESS`

### Step 11: Set Email Recipient

Determine who should receive the automation notifications.

Save as: `EMAIL_TO`

---

## Part 6: Application Installation

### Step 12: Install Python Dependencies

1. Open terminal/command prompt
2. Navigate to the project directory:
   ```bash
   cd /path/to/MerasWaterReport
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

   **Required packages:**
   - `playwright` - Browser automation
   - `python-dotenv` - Environment variable management
   - `requests` - HTTP requests
   - `msal` - Microsoft Authentication Library

### Step 13: Install Playwright Browser

Install the Chrome browser for Playwright:

```bash
playwright install chrome
```

---

## Part 7: Environment Configuration

### Step 14: Create .env File

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor

### Step 15: Configure Portal Credentials

```bash
# Portal Configuration
PORTAL_URL=https://precisionagrilab.com/Portal/Login.aspx
PORTAL_USERNAME=your_portal_username
PORTAL_PASSWORD=your_portal_password
DOWNLOAD_PATH=./downloads
```

### Step 16: Configure Azure AD Settings

Use the values you copied from Azure Portal:

```bash
# SharePoint Configuration (Microsoft Graph API)
SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
SHAREPOINT_FOLDER_PATH=WaterReport
SHAREPOINT_TENANT_ID=your-tenant-id-here
SHAREPOINT_CLIENT_ID=your-client-id-here
SHAREPOINT_CLIENT_SECRET=your-client-secret-here
```

### Step 17: Configure Email Settings

```bash
# Email Configuration (Microsoft Graph API)
EMAIL_SENDER_ADDRESS=waterreports@yourdomain.com
EMAIL_TO=recipient@example.com
```

**Complete .env Example:**

```bash
# Portal Configuration
PORTAL_URL=https://precisionagrilab.com/Portal/Login.aspx
PORTAL_USERNAME=myusername
PORTAL_PASSWORD=mypassword
DOWNLOAD_PATH=./downloads

# SharePoint Configuration (Microsoft Graph API)
SHAREPOINT_SITE_URL=https://bloomsmobility.sharepoint.com/sites/internalApp
SHAREPOINT_FOLDER_PATH=WaterReport
SHAREPOINT_TENANT_ID=93763517-5ec9-4e25-836b-621f1916f963
SHAREPOINT_CLIENT_ID=70b646d2-fbb9-42f1-bb06-2251f930f905
SHAREPOINT_CLIENT_SECRET=your_client_secret_here

# Email Configuration (Microsoft Graph API)
EMAIL_SENDER_ADDRESS=cnbehera@bloomsmobility.com
EMAIL_TO=recipient@example.com
```

---

## Part 8: Testing

### Step 18: Run Initial Test

1. Open terminal in the project directory
2. Run the automation:
   ```bash
   python3 water_report_automation.py
   ```

### Step 19: Verify Results

**Expected Output:**

```
============================================================
Meras Water Report Automation
============================================================
Start time: 2025-12-02 07:51:40

Navigating to portal: https://precisionagrilab.com/Portal/Login.aspx
Entering credentials...
Login successful!
...
Successfully downloaded X report(s)
...
Successfully uploaded X file(s) to SharePoint
...
Notification email sent successfully!
============================================================
End time: 2025-12-02 07:52:26
Total files downloaded: X
Total files uploaded: X
Total errors: 0
============================================================
```

### Step 20: Verify Email Receipt

1. Check the recipient's inbox
2. Look for email with subject like: **"✅ Water Reports Automation - Success"**
3. Verify the email is HTML-formatted with:
   - Color-coded header (green for success)
   - List of downloaded reports
   - List of uploaded reports
   - No errors

### Step 21: Verify SharePoint Upload

1. Navigate to your SharePoint site
2. Go to the configured folder
3. Verify the PDF reports are present
4. Check file names match the downloaded reports

---

## Part 9: Scheduling (Optional)

### For macOS/Linux (cron)

1. Edit crontab:
   ```bash
   crontab -e
   ```

2. Add daily schedule (example: 8 AM daily):
   ```bash
   0 8 * * * cd /path/to/MerasWaterReport && /usr/bin/python3 water_report_automation.py
   ```

### For Windows (Task Scheduler)

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: `Water Report Automation`
4. Trigger: **Daily** at desired time
5. Action: **Start a program**
   - Program: `python.exe`
   - Arguments: `water_report_automation.py`
   - Start in: `C:\path\to\MerasWaterReport`

---

## Troubleshooting

### Authentication Errors

**Error:** `Failed to acquire access token`

**Solutions:**
- Verify `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, and `SHAREPOINT_CLIENT_SECRET` are correct
- Check that the client secret hasn't expired
- Ensure admin consent was granted for all permissions

---

### SharePoint Upload Errors

**Error:** `Failed to get site information`

**Solutions:**
- Verify SharePoint site URL format: `https://tenant.sharepoint.com/sites/sitename`
- Ensure the app has `Sites.ReadWrite.All` permission with admin consent
- Check that the site exists and is accessible

**Error:** `Failed to get document library`

**Solutions:**
- Verify the site has a default document library
- Ensure `Files.ReadWrite.All` permission is granted

**Error:** `Error uploading file`

**Solutions:**
- Check folder path doesn't include `/Shared Documents/`
- Verify file isn't locked or checked out in SharePoint
- Ensure the app has write permissions

---

### Email Sending Errors

**Error:** `Email configuration missing`

**Solutions:**
- Verify `EMAIL_SENDER_ADDRESS` and `EMAIL_TO` are set in `.env`
- Check for typos in email addresses

**Error:** `Failed to send email: HTTP 403 - Access Denied`

**Solutions:**
- Verify `Mail.Send` permission is granted with admin consent
- Check that the sender email address exists in your tenant
- Ensure the mailbox is not disabled or restricted

**Error:** `Failed to send email: HTTP 404`

**Solutions:**
- Verify the sender email address is correct
- Ensure the mailbox exists and is accessible
- Try using the full email address without display name

---

### Portal Login Errors

**Error:** `Login failed`

**Solutions:**
- Verify `PORTAL_USERNAME` and `PORTAL_PASSWORD` in `.env`
- Check that portal credentials are still valid
- Ensure the portal URL is correct

---

### Download Errors

**Error:** `No water reports found`

**Solutions:**
- Check the date range logic in the script
- Verify reports exist for the specified date range
- Ensure the Water tab is accessible

---

## Security Best Practices

1. **Protect .env file:**
   - Never commit `.env` to version control
   - Set appropriate file permissions: `chmod 600 .env`

2. **Rotate secrets regularly:**
   - Set calendar reminders for secret expiration
   - Rotate secrets every 12-24 months

3. **Use least privilege:**
   - Only grant necessary permissions
   - Use a dedicated service account for automation

4. **Monitor usage:**
   - Review automation logs regularly
   - Check for failed authentications
   - Monitor SharePoint upload activity

5. **Backup configuration:**
   - Document all Azure AD app settings
   - Keep a secure backup of configuration values
   - Document any customizations made

---

## Quick Reference

### Azure AD App Permissions Required

| Permission | Type | Purpose |
|------------|------|---------|
| Sites.ReadWrite.All | Application | SharePoint site access |
| Files.ReadWrite.All | Application | Upload files to SharePoint |
| Mail.Send | Application | Send email notifications |

### Environment Variables Required

| Variable | Example | Description |
|----------|---------|-------------|
| PORTAL_URL | `https://precisionagrilab.com/Portal/Login.aspx` | Portal login URL |
| PORTAL_USERNAME | `myusername` | Portal username |
| PORTAL_PASSWORD | `mypassword` | Portal password |
| DOWNLOAD_PATH | `./downloads` | Local download directory |
| SHAREPOINT_SITE_URL | `https://tenant.sharepoint.com/sites/site` | SharePoint site URL |
| SHAREPOINT_FOLDER_PATH | `WaterReport` | Folder name only |
| SHAREPOINT_TENANT_ID | `93763517-...` | Azure AD tenant ID |
| SHAREPOINT_CLIENT_ID | `70b646d2-...` | Azure AD app client ID |
| SHAREPOINT_CLIENT_SECRET | `aKh8Q~bz9...` | Azure AD app secret |
| EMAIL_SENDER_ADDRESS | `sender@domain.com` | Email sender address |
| EMAIL_TO | `recipient@domain.com` | Email recipient |

---

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the [GRAPH_API_SETUP.md](file:///Users/apple/Documents/MerasWaterReport/GRAPH_API_SETUP.md) for additional details
3. Check application logs for error messages
4. Verify all prerequisites are met

---

## Appendix: File Structure

```
MerasWaterReport/
├── water_report_automation.py    # Main automation script
├── requirements.txt               # Python dependencies
├── .env                          # Configuration (DO NOT COMMIT)
├── .env.example                  # Example configuration
├── .gitignore                    # Git ignore rules
├── README.md                     # Project overview
├── GRAPH_API_SETUP.md           # Graph API setup details
└── downloads/                    # Downloaded reports (auto-created)
    └── YYYY-MM-DD/              # Date-specific folders
```

---

## Changelog

### Version 2.0 (December 2025)
- Migrated from SMTP to Microsoft Graph API for email sending
- Added HTML-formatted email notifications
- Unified authentication for SharePoint and email
- Enhanced security with OAuth 2.0

### Version 1.0 (November 2025)
- Initial release with SharePoint Graph API upload
- SMTP email notifications
- Automated portal login and report download
