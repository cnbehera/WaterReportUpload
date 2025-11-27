#!/usr/bin/env python3
"""
Interactive script to manually explore the portal and identify the correct selectors
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright

load_dotenv()


async def explore_portal():
    """Interactively explore the portal to find correct selectors"""
    
    portal_url = os.getenv('PORTAL_URL')
    username = os.getenv('PORTAL_USERNAME')
    password = os.getenv('PORTAL_PASSWORD')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login
            print("Logging in...")
            await page.goto(portal_url, wait_until='networkidle')
            
            # Wait a bit to see the page
            await asyncio.sleep(2)
            
            # Find and fill username
            await page.fill('input[name="txtUserName"]', username)
            await page.fill('input[name="txtPassword"]', password)
            await page.click('input[name="btnLogin"]')
            
            await page.wait_for_load_state('networkidle')
            print("Login successful!")
            
            # Wait to see the main page
            await asyncio.sleep(3)
            
            # Click Water tab if it exists
            print("\nLooking for Water tab...")
            water_tab = page.locator('a#lnkWater, a:has-text("Water")')
            if await water_tab.count() > 0:
                print("Found Water tab, clicking...")
                await water_tab.first.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            
            # Look for the table with reports
            print("\nAnalyzing page structure...")
            
            # Save page screenshot
            await page.screenshot(path='portal_screenshot.png', full_page=True)
            print("Saved screenshot to portal_screenshot.png")
            
            # Get all links
            all_links = await page.locator('a').all()
            print(f"\nFound {len(all_links)} links on the page")
            
            # Look for PDF-related links
            print("\nLooking for PDF download links...")
            for i, link in enumerate(all_links[:20]):  # Check first 20 links
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and ('.pdf' in href.lower() or 'download' in href.lower() or 'report' in href.lower()):
                        print(f"  Link {i}: text='{text}', href='{href}'")
                except:
                    pass
            
            # Look for buttons
            all_buttons = await page.locator('button, input[type="button"], input[type="submit"]').all()
            print(f"\nFound {len(all_buttons)} buttons")
            
            # Check for download-related buttons
            print("\nLooking for download buttons...")
            for i, button in enumerate(all_buttons[:20]):
                try:
                    text = await button.inner_text()
                    value = await button.get_attribute('value')
                    if text or value:
                        display_text = text or value
                        if 'download' in display_text.lower() or 'pdf' in display_text.lower():
                            print(f"  Button {i}: '{display_text}'")
                except:
                    pass
            
            # Save HTML
            content = await page.content()
            with open('portal_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("\nSaved HTML to portal_page.html")
            
            # Keep browser open for manual inspection
            print("\n" + "="*60)
            print("Browser will stay open for 60 seconds")
            print("Please manually inspect the page to identify:")
            print("1. How to filter by date")
            print("2. Where the download buttons/links are")
            print("3. The exact selectors needed")
            print("="*60)
            
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(30)
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(explore_portal())
