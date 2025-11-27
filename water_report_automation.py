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
from requests.auth import HTTPBasicAuth

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
        self.sharepoint_username = os.getenv('SHAREPOINT_USERNAME')
        self.sharepoint_password = os.getenv('SHAREPOINT_PASSWORD')
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
            # Calculate previous day's date
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime('%m/%d/%Y')
            
            print(f"Filtering reports for date: {date_str}")
            
            # Wait for the page to load completely
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Additional wait for dynamic content
            
            # Click on Water tab to filter for water reports
            print("Looking for Water tab...")
            water_tab_selectors = [
                'a:has-text("Water")',
                'a#lnkWater',
                'li:has-text("Water") a',
                '[href*="Water"]'
            ]
            
            water_clicked = False
            for selector in water_tab_selectors:
                try:
                    water_tab = page.locator(selector).first
                    if await water_tab.count() > 0 and await water_tab.is_visible():
                        print(f"Found Water tab, clicking...")
                        await water_tab.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                        water_clicked = True
                        print("Water tab clicked successfully!")
                        break
                except Exception as e:
                    continue
            
            if not water_clicked:
                print("Warning: Could not find Water tab, proceeding with all reports")
            
            # Look for date filter and apply if available
            # This is optional - if no date filter exists, we'll download all water reports
            try:
                date_inputs = await page.locator('input[type="date"], input[placeholder*="date" i]').all()
                if date_inputs:
                    print(f"Found {len(date_inputs)} date filter(s), applying date: {date_str}")
                    for date_input in date_inputs:
                        await date_input.fill(date_str)
                    
                    # Look for search/filter button
                    filter_btn = page.locator('button:has-text("Search"), button:has-text("Filter"), input[value*="Search"]').first
                    if await filter_btn.count() > 0:
                        await filter_btn.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
            except Exception as e:
                print(f"Note: Date filtering not available or failed: {str(e)}")
            
            # Find all download links/buttons
            print("Looking for PDF reports...")
            
            # Try multiple strategies to find download elements
            download_selectors = [
                'a[href$=".pdf"]',  # Direct PDF links
                'a[href*=".pdf"]',  # PDF in URL
                'a:has-text("Download")',  # Download text
                'img[alt*="download" i]',  # Download images
                'img[src*="download" i]',  # Download icon images
                '[onclick*="download"]',  # Download onclick
                '[onclick*=".pdf"]',  # PDF onclick
            ]
            
            all_download_elements = []
            for selector in download_selectors:
                try:
                    elements = await page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            all_download_elements.append(elem)
                except:
                    continue
            
            # Remove duplicates by getting unique elements
            unique_elements = []
            seen_positions = set()
            for elem in all_download_elements:
                try:
                    box = await elem.bounding_box()
                    if box:
                        pos = (box['x'], box['y'])
                        if pos not in seen_positions:
                            seen_positions.add(pos)
                            unique_elements.append(elem)
                except:
                    continue
            
            if not unique_elements:
                print("No visible PDF download links found")
                return
            
            print(f"Found {len(unique_elements)} visible download element(s)")
            
            # Extract PDF URLs from elements
            pdf_urls = []
            for elem in unique_elements:
                try:
                    href = await elem.get_attribute('href')
                    if href and '.pdf' in href.lower():
                        # Make URL absolute if relative
                        if not href.startswith('http'):
                            base_url = page.url.split('/Portal')[0]
                            href = base_url + href if href.startswith('/') else base_url + '/' + href
                        pdf_urls.append(href)
                except:
                    continue
            
            if not pdf_urls:
                print("No direct PDF URLs found")
                return
            
            print(f"Found {len(pdf_urls)} PDF URL(s), downloading...")
            
            # Get cookies for authentication
            cookies = await page.context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # Download each PDF using requests
            for idx, url in enumerate(pdf_urls):
                try:
                    print(f"Downloading report {idx + 1}/{len(pdf_urls)}...")
                    print(f"  URL: {url}")
                    
                    # Download using requests with cookies for authentication
                    response = requests.get(url, cookies=cookie_dict, timeout=30)
                    
                    if response.status_code == 200:
                        # Extract filename from URL or Content-Disposition header
                        filename = url.split('/')[-1]
                        if 'Content-Disposition' in response.headers:
                            cd = response.headers['Content-Disposition']
                            filename_match = re.findall('filename=(.+)', cd)
                            if filename_match:
                                filename = filename_match[0].strip('\"')
                        
                        if not filename.endswith('.pdf'):
                            filename = f"water_report_{idx+1}.pdf"
                        
                        filepath = self.download_path / filename
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        self.downloaded_files.append(filepath)
                        print(f"  Downloaded: {filename} ({len(response.content)} bytes)")
                    else:
                        error_msg = f"Failed to download {url}: HTTP {response.status_code}"
                        print(error_msg)
                        self.errors.append(error_msg)
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error downloading {url}: {str(e)}"
                    print(error_msg)
                    self.errors.append(error_msg)
            
            print(f"Successfully downloaded {len(self.downloaded_files)} report(s)")
            
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
            elif self.downloaded_files and self.uploaded_files:
                status = "PARTIAL SUCCESS"
                subject = "⚠️ Water Reports Automation - Partial Success"
            else:
                status = "ERROR"
                subject = "❌ Water Reports Automation - Error"
            
            # Create email body
            body = f"""
Water Reports Automation Summary
{'=' * 50}

Status: {status}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Downloaded Reports: {len(self.downloaded_files)}
{chr(10).join(f"  - {f.name}" for f in self.downloaded_files) if self.downloaded_files else "  None"}

Uploaded to SharePoint: {len(self.uploaded_files)}
{chr(10).join(f"  - {f}" for f in self.uploaded_files) if self.uploaded_files else "  None"}

Errors: {len(self.errors)}
{chr(10).join(f"  - {e}" for e in self.errors) if self.errors else "  None"}

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
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Set to True for production
            context = await browser.new_context(
                accept_downloads=True
            )
            page = await context.new_page()
            
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
