#!/usr/bin/env python3
"""
Meras Water Report Automation
Automates downloading water reports from Precision Agri-Lab portal and uploading to SharePoint
"""

import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import requests

# Load environment variables
load_dotenv()


class WaterReportAutomation:
    """Main automation class for water report processing"""
    
    def __init__(self):
        self.portal_url = os.getenv('PORTAL_URL')
        self.portal_username = os.getenv('PORTAL_USERNAME')
        self.portal_password = os.getenv('PORTAL_PASSWORD')
        self.download_path = Path(os.getenv('DOWNLOAD_PATH', './downloads'))
        self.sharepoint_site = os.getenv('SHAREPOINT_SITE_URL')
        self.sharepoint_folder = os.getenv('SHAREPOINT_FOLDER_PATH')
        self.downloaded_files = []
        self.uploaded_files = []
        self.uploaded_files_urls = {}  # Dictionary to store filename -> SharePoint URL mapping
        self.errors = []
        
        # Create download directory if it doesn't exist
        self.download_path.mkdir(parents=True, exist_ok=True)
    
    async def login_to_portal(self, page):
        """Login to Precision Agri-Lab portal"""
        try:
            print(f"Navigating to portal: {self.portal_url}")
            await page.goto(self.portal_url, wait_until='networkidle', timeout=30000)
            
            # Fill in login credentials
            print("Entering credentials...")
            await page.fill('input[name*="UserName"], input[type="text"]', self.portal_username)
            await page.fill('input[name*="Password"], input[type="password"]', self.portal_password)
            
            # Click login button
            await page.click('input[type="submit"], button[type="submit"]')
            
            # Wait for navigation after login
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            print("Login successful!")
            return True
            
        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
            return False
    
    async def filter_and_download_reports(self, page):
        """Filter for previous day reports and download all PDFs"""
        try:
            # Wait for the page to load completely
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Click on "View All Reports" link
            print("Clicking 'View All Reports'...")
            try:
                view_all_link = page.locator('xpath=//*[@id="content"]/h4/a')
                if await view_all_link.count() > 0:
                    await view_all_link.click()
                    await page.wait_for_load_state('networkidle')
                    print("Clicked 'View All Reports' successfully!")
                    await asyncio.sleep(2)
                else:
                    print("'View All Reports' link not found, continuing...")
            except Exception as e:
                print(f"Note: Could not click 'View All Reports': {e}")
            
            # Click on Water tab to filter for water reports
            print("\nLooking for Water tab...")
            water_tab = page.locator('//*[@id="tabs"]/ul/li[3]/a')
            if await water_tab.count() > 0:
                print("Found Water tab, clicking...")
                await water_tab.first.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            else:
                print("Warning: Could not find Water tab, proceeding with all reports")
            
            # Calculate yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            target_date = yesterday.strftime('%Y-%m-%d')
            #starget_date = "2025-11-10"

            # Type text on ContentPlaceHolder1_portalContent_txtStartDate field
            print("\nEntering start date...")
            try:
                # For input type="date", we must use YYYY-MM-DD format with page.fill()
                await page.fill('#ContentPlaceHolder1_portalContent_txtStartDate', target_date)
                print(f"Filled start date: {target_date}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error entering start date: {e}")

            # Type text on ContentPlaceHolder1_portalContent_txtEndDate field
            print("\nEntering end date...")
            try:
                # For input type="date", we must use YYYY-MM-DD format with page.fill()
                await page.fill('#ContentPlaceHolder1_portalContent_txtEndDate', target_date)
                print(f"Filled end date: {target_date}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error entering end date: {e}")

            # Click Update Date Range button
            print("\nClicking 'Update Date Range'...")
            try:
                await page.click('#ContentPlaceHolder1_portalContent_btnSubmitDateChanges')
                print("Clicked 'Update Date Range' button")
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error clicking update button: {e}")
            
            # Check if there are any reports available in the table
            print("Checking for available reports in the table...")
            
            # Look for all rows in the water reports grid
            # We need to check the "report" column value for each row
            table_selector = '#ContentPlaceHolder1_portalContent_grdWaterReports'
            
            # Get all rows in the table body (skip header row)
            rows = await page.locator(f'{table_selector} tr[id*="grdWaterReports"]').all()
            
            if len(rows) == 0:
                print("No water reports found in the table for the selected date range.")
                print("Please verify the date range or check if reports are available on the portal.")
                return
            
            print(f"Found {len(rows)} row(s) in the table")
            
            # Filter and select only reports with status "water" (not "in progress")
            print("\nFiltering reports by status...")
            selected_count = 0
            skipped_count = 0
            
            for i, row in enumerate(rows):
                try:
                    # Get all cells in the row
                    cells = await row.locator('td').all()
                    
                    # Find the "report" column value
                    # The exact column index may vary, so we'll check cell text
                    report_status = None
                    checkbox = None
                    
                    # Look for checkbox in this row
                    checkbox_in_row = row.locator('input[id*="chkWater"]')
                    if await checkbox_in_row.count() > 0:
                        checkbox = checkbox_in_row
                    
                    # Check each cell for the report status
                    for cell in cells:
                        cell_text = (await cell.inner_text()).strip()
                        cell_text_lower = cell_text.lower()
                        # Check for "Water" or "In Progress" (case-insensitive)
                        if cell_text_lower in ['water', 'in progress']:
                            report_status = cell_text_lower
                            break
                    
                    # If we found both checkbox and status, decide whether to select
                    if checkbox and report_status:
                        if report_status == 'water':
                            # Only select if status is "water"
                            if not await checkbox.is_checked():
                                await checkbox.click()
                                await asyncio.sleep(0.5)  # Small delay between clicks
                            selected_count += 1
                            print(f"  Row {i+1}: Status = '{report_status}' - SELECTED")
                        else:
                            # Skip "in progress" reports
                            skipped_count += 1
                            print(f"  Row {i+1}: Status = '{report_status}' - SKIPPED")
                    else:
                        print(f"  Row {i+1}: Could not determine status or find checkbox")
                        
                except Exception as e:
                    print(f"  Error processing row {i+1}: {e}")
            
            print(f"\nSummary: {selected_count} report(s) selected, {skipped_count} report(s) skipped")
            
            if selected_count == 0:
                print("No reports with 'water' status found to download.")
                return
            
            # Click "Download Selected" button
            print("\nClicking 'Download Selected' button...")
            try:
                download_button = page.locator('#ContentPlaceHolder1_portalContent_btnDownloadSelectedWater')
                if await download_button.count() > 0:
                    # Create a date-specific folder
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    date_folder = self.download_path / today_str
                    date_folder.mkdir(parents=True, exist_ok=True)
                    print(f"Created/using folder: {date_folder}")
                    
                    try:
                        # Try to handle as download first
                        async with page.expect_download(timeout=10000) as download_info:
                            await download_button.click()
                            print("Clicked 'Download Selected' button")
                        
                        # Get the download object
                        download = await download_info.value
                        
                        # Save the downloaded file to date-specific folder
                        suggested_filename = download.suggested_filename
                        
                        # Replace hyphens with underscores in filename
                        suggested_filename = suggested_filename.replace('-', '_')
                        
                        filepath = date_folder / suggested_filename
                        
                        await download.save_as(filepath)
                        print(f"Downloaded file: {suggested_filename} to {date_folder}")
                        
                        # Check if it's a zip file (multiple reports) or single PDF
                        if suggested_filename.lower().endswith('.zip'):
                            print(f"Downloaded ZIP file containing {report_count} report(s)")
                            # Extract ZIP file
                            try:
                                import zipfile
                                print(f"Extracting ZIP file...")
                                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                                    zip_ref.extractall(date_folder)
                                    extracted_files = zip_ref.namelist()
                                    print(f"Extracted {len(extracted_files)} file(s)")
                                    
                                    # Add extracted PDF files to downloaded_files list
                                    for filename in extracted_files:
                                        if filename.lower().endswith('.pdf'):
                                            # Replace hyphens with underscores in filename
                                            new_filename = filename.replace('-', '_')
                                            old_path = date_folder / filename
                                            new_path = date_folder / new_filename
                                            
                                            # Rename the file if needed
                                            if old_path != new_path:
                                                old_path.rename(new_path)
                                            
                                            self.downloaded_files.append(new_path)
                                            print(f"  - {new_filename}")
                                
                                # Remove the ZIP file after extraction
                                filepath.unlink()
                                print("ZIP file extracted and removed")
                            except Exception as e:
                                error_msg = f"Error extracting ZIP file: {e}"
                                print(error_msg)
                                self.errors.append(error_msg)
                        else:
                            # Single PDF file
                            self.downloaded_files.append(filepath)
                            print(f"Extracted {1} file(s)")
                            print(f"  - {suggested_filename}")
                        
                    except Exception as download_error:
                        # If download didn't work, PDF likely opened in new tab or current page navigated
                        print(f"Download event not triggered, waiting for page navigation...")
                        
                        # Click the button if not already clicked
                        if 'download_info' not in locals():
                            await download_button.click()
                            print("Clicked 'Download Selected' button")
                        
                        # Wait for navigation or new page
                        await asyncio.sleep(3)
                        
                        # Check if current page has PDF
                        current_url = page.url
                        if '.pdf' in current_url.lower():
                            print(f"PDF loaded in current page: {current_url}")
                            
                            # Get cookies for authentication
                            cookies = await page.context.cookies()
                            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                            
                            # Download the PDF using requests
                            response = requests.get(current_url, cookies=cookie_dict, timeout=30)
                            
                            if response.status_code == 200:
                                filename = current_url.split('/')[-1]
                                if '?' in filename:
                                    filename = filename.split('?')[0]
                                if not filename.endswith('.pdf'):
                                    filename = f"water_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                
                                # Replace hyphens with underscores in filename
                                filename = filename.replace('-', '_')
                                
                                filepath = date_folder / filename
                                with open(filepath, 'wb') as f:
                                    f.write(response.content)
                                
                                self.downloaded_files.append(filepath)
                                print(f"Extracted {1} file(s)")
                                print(f"  - {filename}")
                            else:
                                error_msg = f"Failed to download PDF: HTTP {response.status_code}"
                                print(error_msg)
                                self.errors.append(error_msg)
                        else:
                            # Check for new pages/tabs
                            pages = page.context.pages
                            print(f"Found {len(pages)} page(s) open")
                            
                            for idx, p in enumerate(pages):
                                url = p.url
                                print(f"Page {idx}: {url}")
                                if '.pdf' in url.lower():
                                    print(f"Found PDF in page {idx}")
                                    
                                    # Get cookies
                                    cookies = await page.context.cookies()
                                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                                    
                                    # Download the PDF
                                    response = requests.get(url, cookies=cookie_dict, timeout=30)
                                    
                                    if response.status_code == 200:
                                        filename = url.split('/')[-1]
                                        if '?' in filename:
                                            filename = filename.split('?')[0]
                                        if not filename.endswith('.pdf'):
                                            filename = f"water_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                        
                                        # Replace hyphens with underscores in filename
                                        filename = filename.replace('-', '_')
                                        
                                        filepath = date_folder / filename
                                        with open(filepath, 'wb') as f:
                                            f.write(response.content)
                                        
                                        self.downloaded_files.append(filepath)
                                        print(f"Extracted {1} file(s)")
                                        print(f"  - {filename}")
                                        
                                        # Close the PDF tab if it's not the main page
                                        if p != page:
                                            await p.close()
                                    break
                            
                            if not self.downloaded_files:
                                error_msg = "No PDF found in any open pages"
                                print(error_msg)
                                self.errors.append(error_msg)
                                return
                    
                    print(f"\nSuccessfully downloaded {len(self.downloaded_files)} report(s) to {date_folder}")
                    
                else:
                    print("Warning: 'Download Selected' button not found")
                    self.errors.append("Download Selected button not found")
                    
            except Exception as e:
                error_msg = f"Error downloading reports: {e}"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
        except Exception as e:
            error_msg = f"Error during report filtering/download: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def _get_graph_token(self):
        """Get Microsoft Graph API access token (shared for SharePoint and Email)"""
        try:
            import msal
            
            tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
            client_id = os.getenv('SHAREPOINT_CLIENT_ID')
            client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
            
            # Validate configuration
            if not all([tenant_id, client_id, client_secret]):
                error_msg = "Graph API credentials not configured. Please set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET in .env"
                print(error_msg)
                self.errors.append(error_msg)
                return None
            
            # Authenticate using MSAL
            authority = f"https://login.microsoftonline.com/{tenant_id}"
            scope = ["https://graph.microsoft.com/.default"]
            
            app = msal.ConfidentialClientApplication(
                client_id,
                authority=authority,
                client_credential=client_secret
            )
            
            # Acquire token
            result = app.acquire_token_for_client(scopes=scope)
            
            if "access_token" not in result:
                error_msg = f"Failed to acquire access token: {result.get('error_description', 'Unknown error')}"
                print(error_msg)
                self.errors.append(error_msg)
                return None
            
            return result["access_token"]
            
        except ImportError:
            error_msg = "MSAL library not installed. Run: pip install msal"
            print(error_msg)
            self.errors.append(error_msg)
            return None
        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
            return None
    
    def upload_to_sharepoint(self):
        """Upload downloaded PDFs to SharePoint using Microsoft Graph API"""
        if not self.downloaded_files:
            print("No files to upload to SharePoint")
            return
        
        try:
            print(f"Connecting to SharePoint via Microsoft Graph API...")
            
            # Get access token
            access_token = self._get_graph_token()
            if not access_token:
                return
            
            print("Successfully authenticated with Microsoft Graph API")
            
            # Get configuration
            site_url = self.sharepoint_site
            folder_path = self.sharepoint_folder
            
            if not site_url:
                error_msg = "SharePoint site URL not configured"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
            # Extract site details from URL
            # Format: https://tenant.sharepoint.com/sites/sitename
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(site_url)
                hostname = parsed_url.netloc  # tenant.sharepoint.com
                site_path = parsed_url.path   # /sites/sitename
                
                # Extract tenant name and site name
                if '/sites/' in site_path:
                    site_name = site_path.split('/sites/')[-1].strip('/')
                else:
                    site_name = site_path.strip('/')
                
            except Exception as e:
                error_msg = f"Invalid SharePoint site URL format: {str(e)}"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
            # Get site ID
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get site by hostname and path
            site_api_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
            response = requests.get(site_api_url, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Failed to get site information: HTTP {response.status_code} - {response.text}"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
            site_id = response.json()['id']
            print(f"Found SharePoint site: {site_name}")
            
            # Get drive (document library)
            drive_api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
            response = requests.get(drive_api_url, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Failed to get document library: HTTP {response.status_code} - {response.text}"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
            drive_id = response.json()['id']
            print(f"Found document library")
            
            # Upload each file
            for filepath in self.downloaded_files:
                try:
                    print(f"Uploading {filepath.name} to SharePoint...")
                    
                    # Construct upload URL
                    # Format: /drives/{drive-id}/root:/{folder-path}/{filename}:/content
                    upload_path = f"{folder_path}/{filepath.name}" if folder_path else filepath.name
                    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{upload_path}:/content"
                    
                    # Read file content
                    with open(filepath, 'rb') as f:
                        file_content = f.read()
                    
                    # Upload file
                    upload_headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/pdf'
                    }
                    
                    response = requests.put(upload_url, headers=upload_headers, data=file_content)
                    
                    if response.status_code in [200, 201]:
                        self.uploaded_files.append(filepath.name)
                        
                        # Extract the webUrl from the response to create a direct link
                        response_data = response.json()
                        web_url = response_data.get('webUrl', '')
                        
                        # Store the URL for this file
                        if web_url:
                            self.uploaded_files_urls[filepath.name] = web_url
                        
                        print(f"  Successfully uploaded: {filepath.name}")
                    else:
                        error_msg = f"Error uploading {filepath.name}: HTTP {response.status_code} - {response.text}"
                        print(error_msg)
                        self.errors.append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error uploading {filepath.name}: {str(e)}"
                    print(error_msg)
                    self.errors.append(error_msg)
            
            print(f"Successfully uploaded {len(self.uploaded_files)} file(s) to SharePoint")
            
        except Exception as e:
            error_msg = f"SharePoint Graph API error: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def send_notification_email(self):
        """Send email notification about the automation results using Microsoft Graph API"""
        try:
            email_sender = os.getenv('EMAIL_SENDER_ADDRESS')
            email_to = os.getenv('EMAIL_TO')
            
            if not email_sender or not email_to:
                error_msg = "Email configuration missing. Please set EMAIL_SENDER_ADDRESS and EMAIL_TO in .env"
                print(error_msg)
                self.errors.append(error_msg)
                return
            
            # Get access token
            print("Authenticating for email sending...")
            access_token = self._get_graph_token()
            if not access_token:
                return
            
            # Determine status
            if not self.errors and self.downloaded_files and len(self.uploaded_files) == len(self.downloaded_files):
                status = "SUCCESS"
                subject = "✅ Water Reports Automation - Success"
                status_color = "#28a745"  # Green
            elif not self.errors and not self.downloaded_files:
                status = "NO REPORTS FOUND"
                subject = "ℹ️ Water Reports Automation - No Reports Found"
                status_color = "#17a2b8"  # Blue
            elif self.downloaded_files and self.uploaded_files:
                status = "PARTIAL SUCCESS"
                subject = "⚠️ Water Reports Automation - Partial Success"
                status_color = "#ffc107"  # Yellow
            else:
                status = "ERROR"
                subject = "❌ Water Reports Automation - Error"
                status_color = "#dc3545"  # Red
            
            # Create email body with URL-decoded filenames
            import urllib.parse
            
            def clean_filename(name):
                """Remove URL encoding like %20 and clean up filename"""
                return urllib.parse.unquote(str(name))
            
            downloaded_list = "<br>".join(
                f"&nbsp;&nbsp;{i+1}. {clean_filename(f.name)}" 
                for i, f in enumerate(self.downloaded_files)
            ) if self.downloaded_files else "&nbsp;&nbsp;None"
            
            # Create uploaded list with clickable links to SharePoint
            if self.uploaded_files:
                uploaded_items = []
                for i, filename in enumerate(self.uploaded_files):
                    clean_name = clean_filename(filename)
                    # Check if we have a SharePoint URL for this file
                    if filename in self.uploaded_files_urls:
                        sharepoint_url = self.uploaded_files_urls[filename]
                        # Create clickable link
                        uploaded_items.append(
                            f'&nbsp;&nbsp;{i+1}. <a href="{sharepoint_url}" style="color: #007bff; text-decoration: none;">{clean_name}</a>'
                        )
                    else:
                        # No URL available, just show filename
                        uploaded_items.append(f"&nbsp;&nbsp;{i+1}. {clean_name}")
                uploaded_list = "<br>".join(uploaded_items)
            else:
                uploaded_list = "&nbsp;&nbsp;None"
            
            error_list = "<br>".join(
                f"&nbsp;&nbsp;• {e}" 
                for e in self.errors
            ) if self.errors else "&nbsp;&nbsp;None"
            
            # Create HTML email body
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {status_color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                    .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
                    .section {{ margin-bottom: 20px; }}
                    .section-title {{ font-weight: bold; color: #555; margin-bottom: 10px; }}
                    .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">Water Reports Automation</h2>
                        <p style="margin: 5px 0 0 0;">Status: {status}</p>
                    </div>
                    <div class="content">
                        <div class="section">
                            <div class="section-title">Date:</div>
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </div>
                        
                        <div class="section">
                            <div class="section-title">Downloaded Reports ({len(self.downloaded_files)}):</div>
                            {downloaded_list}
                        </div>
                        
                        <div class="section">
                            <div class="section-title">Uploaded to SharePoint ({len(self.uploaded_files)}):</div>
                            {uploaded_list}
                        </div>
                        
                        <div class="section">
                            <div class="section-title">Errors ({len(self.errors)}):</div>
                            {error_list}
                        </div>
                        
                        <div class="footer">
                            This is an automated message from the Meras Water Report Automation system.
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Prepare Graph API request
            # Extract just the email address if sender has a name format
            sender_email = email_sender.split('<')[-1].strip('>') if '<' in email_sender else email_sender
            
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email_to
                            }
                        }
                    ]
                },
                "saveToSentItems": "true"
            }
            
            # Send email via Graph API
            print("Sending notification email via Microsoft Graph API...")
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            send_mail_url = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
            response = requests.post(send_mail_url, headers=headers, json=email_data)
            
            if response.status_code == 202:
                print("Notification email sent successfully!")
            else:
                error_msg = f"Failed to send email: HTTP {response.status_code} - {response.text}"
                print(error_msg)
                self.errors.append(error_msg)
            
        except Exception as e:
            error_msg = f"Error sending notification email: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
    
    async def run(self):
        """Main execution method"""
        print("=" * 60)
        print("Meras Water Report Automation")
        print("=" * 60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        async with async_playwright() as p:
            # Create a date-specific download folder
            today_str = datetime.now().strftime('%Y-%m-%d')
            date_folder = self.download_path / today_str
            date_folder.mkdir(parents=True, exist_ok=True)
            
            # Launch browser - using system Chrome instead of Chromium
            browser = await p.chromium.launch(
                channel='chrome',  # Use system Chrome browser
                headless=False,  # Running with visible browser
                slow_mo=100,  # Slow down by 100ms to improve stability
                args=['--start-maximized']  # Launch in maximized window
            )
            
            context = await browser.new_context(
                accept_downloads=True,
                no_viewport=True  # Use full window size instead of fixed viewport
            )
            
            page = await context.new_page()
            
            # Set up CDP session to configure download behavior
            cdp = await context.new_cdp_session(page)
            await cdp.send('Browser.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': str(date_folder)
            })
            
            try:
                # Step 1: Login
                if await self.login_to_portal(page):
                    # Step 2: Filter and download reports
                    await self.filter_and_download_reports(page)
                    
                    # Step 3: Upload to SharePoint
                    if self.downloaded_files:
                        self.upload_to_sharepoint()
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(error_msg)
                self.errors.append(error_msg)
            
            finally:
                await browser.close()
        
        # Step 4: Send notification
        self.send_notification_email()
        
        print()
        print("=" * 60)
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total files downloaded: {len(self.downloaded_files)}")
        print(f"Total files uploaded: {len(self.uploaded_files)}")
        print(f"Total errors: {len(self.errors)}")
        print("=" * 60)


def main():
    """Entry point"""
    automation = WaterReportAutomation()
    asyncio.run(automation.run())


if __name__ == "__main__":
    main()
