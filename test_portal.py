#!/usr/bin/env python3
"""
Test script to explore the Precision Agri-Lab portal structure
and understand how to filter and download water reports
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright

load_dotenv()


async def test_portal():
    """Test portal navigation and report filtering"""
    
    portal_url = os.getenv('PORTAL_URL')
    username = os.getenv('PORTAL_USERNAME')
    password = os.getenv('PORTAL_PASSWORD')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login
            print("Logging in...")
            await page.goto(portal_url, wait_until='networkidle')
            await page.fill('input[type="text"]', username)
            await page.fill('input[type="password"]', password)
            await page.click('input[type="submit"]')
            await page.wait_for_load_state('networkidle')
            print("Login successful!")
            
            # Click on Water tab
            print("\nClicking Water tab...")
            water_tab = page.locator('a:has-text("Water")')
            if await water_tab.count() > 0:
                await water_tab.click()
                await page.wait_for_load_state('networkidle')
                print("Water tab clicked!")
            
            # Look for date filters
            print("\nLooking for date filters...")
            date_inputs = await page.locator('input[type="date"], input[type="text"][placeholder*="date" i]').all()
            print(f"Found {len(date_inputs)} date input fields")
            
            # Get yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime('%m/%d/%Y')
            print(f"Target date: {date_str}")
            
            # Look for report rows
            print("\nLooking for report rows...")
            rows = await page.locator('tr[class*="row"], div[class*="report"]').all()
            print(f"Found {len(rows)} potential report rows")
            
            # Look for download links/buttons
            print("\nLooking for download elements...")
            download_links = await page.locator('a[href$=".pdf"], a:has-text("Download"), button:has-text("Download"), a[title*="Download" i]').all()
            print(f"Found {len(download_links)} download elements")
            
            # Print page HTML structure for analysis
            print("\nPage structure analysis:")
            print("=" * 60)
            
            # Get the main content area
            content = await page.content()
            
            # Save HTML for inspection
            with open('portal_structure.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Saved page HTML to portal_structure.html")
            
            # Wait for manual inspection
            print("\nBrowser will stay open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_portal())
