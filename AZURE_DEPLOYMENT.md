# Azure Functions Deployment Guide - Water Report Automation

## Important Notice

> [!WARNING]
> **Playwright + Azure Functions Challenges**
> 
> Running Playwright (browser automation) in Azure Functions has significant limitations:
> - **Execution Time**: Consumption plan limited to 10 minutes (Premium plan allows 60+ minutes)
> - **Browser Binaries**: Playwright requires ~300MB of browser files
> - **Memory**: Browser automation needs 1GB+ RAM
> - **Cold Starts**: Browser initialization adds 10-30 seconds
> 
> **This guide focuses on Azure Functions Premium Plan**, which addresses most of these issues but costs more (~$150-300/month).

---

## Alternative Deployment Options

Before proceeding with Azure Functions, consider these alternatives:

### Option 1: Azure Container Apps (Recommended)
**Best for Playwright automation**

- ✅ Full control over environment
- ✅ Longer execution times
- ✅ Better for browser automation
- ✅ More cost-effective (~$50-100/month)
- ❌ Requires Docker knowledge

### Option 2: Azure Virtual Machine
**Traditional approach**

- ✅ Complete control
- ✅ Simple to set up
- ✅ Cheapest option (~$30-50/month)
- ✅ Can use existing cron setup
- ❌ Manual management required
- ❌ No auto-scaling

### Option 3: Azure Functions Premium Plan
**Serverless with more resources**

- ✅ Managed service
- ✅ Auto-scaling
- ✅ Supports longer execution
- ❌ More expensive (~$150-300/month)
- ❌ Still has some limitations

---

## Prerequisites

### Azure Resources Required

- [ ] **Azure Subscription** with sufficient credits
- [ ] **Resource Group** for organizing resources
- [ ] **Azure CLI** installed locally
- [ ] **Azure Functions Core Tools** v4.x
- [ ] **Existing Azure AD App** (already configured from SETUP_GUIDE.md)

### Local Development Tools

- [ ] **Python 3.9-3.11** (Azure Functions supports these versions)
- [ ] **Visual Studio Code** with Azure Functions extension (recommended)
- [ ] **Git** for version control
- [ ] **Azure Storage Explorer** (optional, for debugging)

### Azure Subscription Limits

Check your subscription has:
- Premium Function App quota available
- Sufficient storage quota
- Application Insights quota

---

## Part 1: Prepare the Application

### Step 1: Install Azure Functions Core Tools

**macOS:**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Windows:**
```powershell
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

**Linux:**
```bash
wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

### Step 2: Install Azure CLI

**macOS:**
```bash
brew install azure-cli
```

**Windows:**
Download from: https://aka.ms/installazurecliwindows

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 3: Login to Azure

```bash
az login
```

This will open a browser for authentication.

---

## Part 2: Create Azure Resources

### Step 4: Set Variables

```bash
# Configuration
RESOURCE_GROUP="WaterReportAutomation-RG"
LOCATION="eastus"
STORAGE_ACCOUNT="waterreportstorage"  # Must be globally unique, lowercase, no hyphens
FUNCTION_APP="water-report-automation"  # Must be globally unique
APP_INSIGHTS="water-report-insights"
```

### Step 5: Create Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 6: Create Storage Account

```bash
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS
```

### Step 7: Create Application Insights

```bash
az monitor app-insights component create \
  --app $APP_INSIGHTS \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web
```

Get the instrumentation key:
```bash
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app $APP_INSIGHTS \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)
```

### Step 8: Create Function App (Premium Plan)

```bash
# Create App Service Plan (Premium EP1)
az functionapp plan create \
  --name "${FUNCTION_APP}-plan" \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku EP1 \
  --is-linux

# Create Function App
az functionapp create \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --plan "${FUNCTION_APP}-plan" \
  --storage-account $STORAGE_ACCOUNT \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux \
  --app-insights $APP_INSIGHTS
```

---

## Part 3: Configure the Function App

### Step 9: Configure Application Settings

Add all environment variables from your `.env` file:

```bash
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    "PORTAL_URL=https://precisionagrilab.com/Portal/Login.aspx" \
    "PORTAL_USERNAME=your_username" \
    "PORTAL_PASSWORD=your_password" \
    "SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite" \
    "SHAREPOINT_FOLDER_PATH=WaterReport" \
    "SHAREPOINT_TENANT_ID=your-tenant-id" \
    "SHAREPOINT_CLIENT_ID=your-client-id" \
    "SHAREPOINT_CLIENT_SECRET=your-client-secret" \
    "EMAIL_SENDER_ADDRESS=sender@domain.com" \
    "EMAIL_TO=recipient@domain.com" \
    "DOWNLOAD_PATH=/tmp/downloads"
```

> [!IMPORTANT]
> Use `/tmp/downloads` for DOWNLOAD_PATH in Azure Functions as it's the only writable directory.

### Step 10: Configure Function Timeout

```bash
az functionapp config set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --linux-fx-version "PYTHON|3.11"

# Set timeout to 20 minutes (Premium plan allows this)
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings "FUNCTIONS_WORKER_PROCESS_COUNT=1"
```

---

## Part 4: Adapt the Code for Azure Functions

### Step 11: Create Function App Structure

In your project directory:

```bash
cd /Users/apple/Documents/MerasWaterReport

# Initialize Azure Functions project
func init . --python
```

This creates:
- `host.json` - Function app configuration
- `local.settings.json` - Local development settings
- `.funcignore` - Files to exclude from deployment

### Step 12: Create Timer Trigger Function

```bash
func new --name WaterReportTimer --template "Timer trigger"
```

This creates a `WaterReportTimer` folder with:
- `__init__.py` - Function code
- `function.json` - Function configuration

### Step 13: Update host.json

Replace content with:

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "functionTimeout": "00:20:00"
}
```

### Step 14: Update function.json (Timer Schedule)

Edit `WaterReportTimer/function.json`:

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 8 * * *"
    }
  ]
}
```

Schedule format: `0 0 8 * * *` = Daily at 8:00 AM UTC

### Step 15: Create Function Code

Edit `WaterReportTimer/__init__.py`:

```python
import azure.functions as func
import logging
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path to import water_report_automation
sys.path.append(str(Path(__file__).parent.parent))

from water_report_automation import WaterReportAutomation


def main(mytimer: func.TimerRequest) -> None:
    """Azure Function entry point"""
    utc_timestamp = datetime.utcnow().isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')
    
    logging.info(f'Water Report Automation started at {utc_timestamp}')
    
    try:
        # Run the automation
        automation = WaterReportAutomation()
        asyncio.run(automation.run())
        
        logging.info(f'Automation completed successfully')
        logging.info(f'Downloaded: {len(automation.downloaded_files)} files')
        logging.info(f'Uploaded: {len(automation.uploaded_files)} files')
        
        if automation.errors:
            logging.warning(f'Completed with {len(automation.errors)} errors:')
            for error in automation.errors:
                logging.warning(f'  - {error}')
        
    except Exception as e:
        logging.error(f'Automation failed: {str(e)}', exc_info=True)
        raise
```

### Step 16: Update requirements.txt

Add Azure Functions dependencies:

```txt
# Azure Functions
azure-functions

# Existing dependencies
playwright==1.40.0
python-dotenv==1.0.0
requests==2.31.0
msal==1.25.0

# Playwright browsers will be installed in startup script
```

### Step 17: Create Startup Script for Playwright

Create `.azure/startup.sh`:

```bash
#!/bin/bash

echo "Installing Playwright browsers..."
python -m playwright install chromium --with-deps

echo "Playwright installation complete"
```

Make it executable:
```bash
chmod +x .azure/startup.sh
```

### Step 18: Configure Startup Command

```bash
az functionapp config set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --startup-file ".azure/startup.sh"
```

### Step 19: Update .funcignore

Edit `.funcignore` to exclude unnecessary files:

```
.git*
.vscode
__pycache__
.pytest_cache
.env
downloads/
*.pyc
*.pyo
.DS_Store
```

---

## Part 5: Deploy the Function

### Step 20: Deploy to Azure

```bash
func azure functionapp publish $FUNCTION_APP --build remote
```

This will:
1. Package your code
2. Upload to Azure
3. Install dependencies
4. Run startup script (install Playwright)
5. Start the function

**Expected output:**
```
Getting site publishing info...
Uploading package...
Upload completed successfully.
Deployment completed successfully.
Functions in water-report-automation:
    WaterReportTimer - [timerTrigger]
```

---

## Part 6: Verify Deployment

### Step 21: Check Function Status

```bash
az functionapp show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query state
```

Should return: `"Running"`

### Step 22: View Logs

**Option 1: Azure Portal**
1. Go to Azure Portal
2. Navigate to your Function App
3. Click "Functions" → "WaterReportTimer"
4. Click "Monitor"
5. View execution history

**Option 2: Azure CLI**
```bash
az functionapp log tail \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP
```

**Option 3: Application Insights**
1. Go to Application Insights in Azure Portal
2. Click "Logs"
3. Query:
```kusto
traces
| where timestamp > ago(1h)
| where message contains "Water Report"
| order by timestamp desc
```

### Step 23: Test Manual Execution

Trigger the function manually:

```bash
# Get function key
FUNCTION_KEY=$(az functionapp function keys list \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --function-name WaterReportTimer \
  --query default \
  --output tsv)

# Trigger function
curl -X POST "https://${FUNCTION_APP}.azurewebsites.net/admin/functions/WaterReportTimer" \
  -H "x-functions-key: $FUNCTION_KEY"
```

Monitor the logs to see execution progress.

---

## Part 7: Monitoring and Maintenance

### Step 24: Set Up Alerts

Create alert for function failures:

```bash
az monitor metrics alert create \
  --name "WaterReportFailures" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP" \
  --condition "count FunctionExecutionCount < 1" \
  --window-size 1d \
  --evaluation-frequency 1h \
  --action email your-email@domain.com
```

### Step 25: Monitor Costs

View estimated costs:

```bash
az consumption usage list \
  --start-date 2025-12-01 \
  --end-date 2025-12-31 \
  --query "[?contains(instanceName, '$FUNCTION_APP')]"
```

---

## Troubleshooting

### Issue: Playwright Installation Fails

**Symptoms:**
- Function fails with "Playwright not found"
- Browser binary errors

**Solutions:**
1. Check startup script logs in Kudu console
2. Increase function timeout
3. Verify Premium plan (EP1 or higher)
4. Manually install via Kudu console:
   ```bash
   python -m playwright install chromium --with-deps
   ```

### Issue: Function Timeout

**Symptoms:**
- Execution stops after 5-10 minutes
- "Function timeout" errors

**Solutions:**
1. Verify you're using Premium plan (not Consumption)
2. Check `host.json` has `functionTimeout` set
3. Increase timeout in `host.json`:
   ```json
   "functionTimeout": "00:30:00"
   ```

### Issue: Memory Errors

**Symptoms:**
- Out of memory errors
- Browser crashes

**Solutions:**
1. Upgrade to EP2 or EP3 plan (more memory)
2. Run browser in headless mode (already configured)
3. Close browser properly after execution

### Issue: Environment Variables Not Found

**Symptoms:**
- "Configuration missing" errors
- Authentication failures

**Solutions:**
1. Verify settings in Azure Portal
2. Restart function app:
   ```bash
   az functionapp restart --name $FUNCTION_APP --resource-group $RESOURCE_GROUP
   ```
3. Check for typos in variable names

### Issue: Cold Start Delays

**Symptoms:**
- First execution takes very long
- Timeout on first run

**Solutions:**
1. Enable "Always On" (Premium plan feature):
   ```bash
   az functionapp config set \
     --name $FUNCTION_APP \
     --resource-group $RESOURCE_GROUP \
     --always-on true
   ```
2. Use pre-warmed instances
3. Consider Azure Container Apps for better cold start

---

## Cost Optimization

### Estimated Monthly Costs

**Premium EP1 Plan:**
- Base: ~$150/month
- Execution: ~$0.20 per million executions
- Storage: ~$5/month
- Application Insights: ~$10/month
- **Total: ~$165-175/month**

### Ways to Reduce Costs

1. **Use Azure Container Apps instead**
   - ~$50-100/month
   - Better for Playwright
   - More control

2. **Use Azure VM with cron**
   - ~$30-50/month
   - B2s instance sufficient
   - No serverless benefits

3. **Optimize execution**
   - Run only on weekdays
   - Reduce retention in Application Insights
   - Use cheaper storage tier

---

## Alternative: Azure Container Apps Deployment

If Azure Functions proves too expensive or problematic, consider Azure Container Apps:

### Quick Container Apps Setup

```bash
# Create container app environment
az containerapp env create \
  --name water-report-env \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Create container app with cron schedule
az containerapp create \
  --name water-report-app \
  --resource-group $RESOURCE_GROUP \
  --environment water-report-env \
  --image mcr.microsoft.com/playwright/python:v1.40.0 \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars [your environment variables] \
  --schedule "0 8 * * *"
```

This approach:
- ✅ Better for Playwright
- ✅ More cost-effective
- ✅ Easier to debug
- ❌ Requires Docker knowledge

---

## Summary

### What You've Deployed

- ✅ Azure Function App (Premium Plan)
- ✅ Timer-triggered daily execution
- ✅ Playwright browser automation in cloud
- ✅ Integrated with existing Graph API setup
- ✅ Monitoring via Application Insights
- ✅ Automated email notifications

### Next Steps

1. Monitor first few scheduled executions
2. Review Application Insights for performance
3. Adjust schedule if needed
4. Set up cost alerts
5. Consider alternatives if costs are too high

### Support Resources

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Playwright in Docker](https://playwright.dev/docs/docker)
- [Azure Container Apps](https://docs.microsoft.com/azure/container-apps/)
