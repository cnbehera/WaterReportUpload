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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
            
            # Look for checkboxes in the water reports grid
            checkbox_selector = 'input[id*="grdWaterReports_chkWater"]'
            checkboxes = await page.locator(checkbox_selector).all()
            
            report_count = len(checkboxes)
            
            if report_count == 0:
                print("No water reports found in the table for the selected date range.")
                print("Please verify the date range or check if reports are available on the portal.")
                return
            
            print(f"Found {report_count} water report(s) in the table")
            
            # Click "Select All" checkbox to select all water reports
            print("\nSelecting all water reports...")
            try:
                select_all_checkbox = page.locator('#ContentPlaceHolder1_portalContent_grdWaterReports_chkAllWater')
                if await select_all_checkbox.count() > 0:
                    await select_all_checkbox.click()
                    print("Clicked 'Select All' checkbox")
                    await asyncio.sleep(2)  # Wait for postback to complete
                else:
                    print("Warning: 'Select All' checkbox not found")
            except Exception as e:
                print(f"Error clicking 'Select All' checkbox: {e}")
                self.errors.append(f"Failed to select all reports: {e}")
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
    
    def upload_to_sharepoint(self):
        """Upload downloaded PDFs to SharePoint using Microsoft Graph API"""
        if not self.downloaded_files:
            print("No files to upload to SharePoint")
            return
        
        try:
            import msal
            
            print(f"Connecting to SharePoint via Microsoft Graph API...")
            
            # Get configuration
            site_url = self.sharepoint_site
            folder_path = self.sharepoint_folder
            tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
            client_id = os.getenv('SHAREPOINT_CLIENT_ID')
            client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
            
            # Validate configuration
            if not all([site_url, tenant_id, client_id, client_secret]):
                error_msg = "SharePoint Graph API credentials not configured. Please set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET in .env"
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
                return
            
            access_token = result["access_token"]
            print("Successfully authenticated with Microsoft Graph API")
            
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
            
        except ImportError:
            error_msg = "MSAL library not installed. Run: pip install msal"
            print(error_msg)
            self.errors.append(error_msg)
        except Exception as e:
            error_msg = f"SharePoint Graph API error: {str(e)}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def send_notification_email(self):
        """Send email notification about the automation results"""
        try:
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            email_from = os.getenv('EMAIL_FROM')
            email_to = os.getenv('EMAIL_TO')
            
            # Determine status
            if not self.errors and self.downloaded_files and len(self.uploaded_files) == len(self.downloaded_files):
                status = "SUCCESS"
                subject = "✅ Water Reports Automation - Success"
            elif not self.errors and not self.downloaded_files:
                status = "NO REPORTS FOUND"
                subject = "ℹ️ Water Reports Automation - No Reports Found"
            elif self.downloaded_files and self.uploaded_files:
                status = "PARTIAL SUCCESS"
                subject = "⚠️ Water Reports Automation - Partial Success"
            else:
                status = "ERROR"
                subject = "❌ Water Reports Automation - Error"
            
            # Create email body with URL-decoded filenames
            import urllib.parse
            
            def clean_filename(name):
                """Remove URL encoding like %20 and clean up filename"""
                return urllib.parse.unquote(str(name))
            
            downloaded_list = "\n".join(
                f"  {i+1}. {clean_filename(f.name)}" 
                for i, f in enumerate(self.downloaded_files)
            ) if self.downloaded_files else "  None"
            
            uploaded_list = "\n".join(
                f"  {i+1}. {clean_filename(f)}" 
                for i, f in enumerate(self.uploaded_files)
            ) if self.uploaded_files else "  None"
            
            error_list = "\n".join(
                f"  - {e}" 
                for e in self.errors
            ) if self.errors else "  None"
            
            body = f"""Water Reports Automation Summary
{'=' * 50}

Status: {status}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Downloaded Reports ({len(self.downloaded_files)}):
{downloaded_list}

Uploaded to SharePoint ({len(self.uploaded_files)}):
{uploaded_list}

Errors ({len(self.errors)}):
{error_list}

{'=' * 50}
This is an automated message from the Meras Water Report Automation system.
"""
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_from
            msg['To'] = email_to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            print("Sending notification email...")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            print("Notification email sent successfully!")
            
        except Exception as e:
            print(f"Error sending notification email: {str(e)}")
    
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
