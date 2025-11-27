# Meras Water Report Automation

This Python automation script uses Playwright to:
- Login to Precision Agri-Lab portal
- Filter and download water reports from the previous day
- Upload reports to SharePoint
- Send email notifications

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Update SharePoint and email settings in `.env`
   - Portal credentials are already configured

4. **Update SharePoint settings in `.env`:**
   
   > **Note:** SharePoint upload now uses Microsoft Graph API for better security and reliability.
   > See [SHAREPOINT_SETUP.md](SHAREPOINT_SETUP.md) for detailed setup instructions.
   
   - `SHAREPOINT_SITE_URL`: Your SharePoint site URL (e.g., `https://tenant.sharepoint.com/sites/sitename`)
   - `SHAREPOINT_FOLDER_PATH`: Folder name only (e.g., `WaterReport` or `Water Reports`)
   - `SHAREPOINT_TENANT_ID`: Azure AD tenant ID
   - `SHAREPOINT_CLIENT_ID`: Azure AD app client ID
   - `SHAREPOINT_CLIENT_SECRET`: Azure AD app client secret

5. **Update email settings in `.env`:**
   - `SMTP_SERVER`: SMTP server (e.g., smtp.gmail.com)
   - `SMTP_PORT`: SMTP port (usually 587)
   - `SMTP_USERNAME`: Email username
   - `SMTP_PASSWORD`: Email password or app-specific password
   - `EMAIL_FROM`: Sender email address
   - `EMAIL_TO`: Recipient email address

## Usage

Run the automation script:
```bash
python water_report_automation.py
```

## Features

- **Automated Login**: Logs into the Precision Agri-Lab portal
- **Date Filtering**: Automatically filters for previous day's reports
- **PDF Download**: Downloads all available PDF reports
- **SharePoint Upload**: Uploads downloaded files to designated SharePoint folder
- **Email Notifications**: Sends status emails (success/partial/error)
- **Error Handling**: Comprehensive error tracking and reporting

## Scheduling

To run this daily, you can use:

**macOS/Linux (cron):**
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 8 AM
0 8 * * * cd /Users/apple/Documents/MerasWaterReport && /usr/bin/python3 water_report_automation.py
```

**Windows (Task Scheduler):**
- Create a new task in Task Scheduler
- Set trigger to daily at desired time
- Set action to run the Python script

## Troubleshooting

- **Login fails**: Verify portal credentials in `.env`
- **No reports found**: Check date filtering logic matches portal interface
- **SharePoint upload fails**: Verify SharePoint credentials and folder path
- **Email not sent**: Check SMTP settings and credentials
