#!/usr/bin/env python3
"""
Debug script to inspect the water reports table structure
"""

import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

async def debug_table():
    portal_url = os.getenv('PORTAL_URL')
    portal_username = os.getenv('PORTAL_USERNAME')
    portal_password = os.getenv('PORTAL_PASSWORD')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel='chrome',
            headless=False,
            slow_mo=100
        )
        
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        
        try:
            # Login
            print(f"Navigating to portal: {portal_url}")
            await page.goto(portal_url, wait_until='networkidle', timeout=30000)
            
            print("Entering credentials...")
            await page.fill('input[name*="UserName"], input[type="text"]', portal_username)
            await page.fill('input[name*="Password"], input[type="password"]', portal_password)
            await page.click('input[type="submit"], button[type="submit"]')
            await page.wait_for_load_state('networkidle', timeout=30000)
            print("Login successful!")
            
            # Click View All Reports
            await asyncio.sleep(2)
            view_all_link = page.locator('xpath=//*[@id="content"]/h4/a')
            if await view_all_link.count() > 0:
                await view_all_link.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            
            # Click Water tab
            water_tab = page.locator('//*[@id="tabs"]/ul/li[3]/a')
            if await water_tab.count() > 0:
                await water_tab.first.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            
            # Set date range
            target_date = "2025-12-11"
            await page.fill('#ContentPlaceHolder1_portalContent_txtStartDate', target_date)
            await asyncio.sleep(1)
            await page.fill('#ContentPlaceHolder1_portalContent_txtEndDate', target_date)
            await asyncio.sleep(1)
            await page.click('#ContentPlaceHolder1_portalContent_btnSubmitDateChanges')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # Debug: Check table structure
            print("\n=== DEBUGGING TABLE STRUCTURE ===")
            
            # Try to find the table
            table_selector = '#ContentPlaceHolder1_portalContent_grdWaterReports'
            table = page.locator(table_selector)
            table_count = await table.count()
            print(f"Table found: {table_count > 0}")
            
            if table_count > 0:
                # Get all rows
                all_rows = await page.locator(f'{table_selector} tr').all()
                print(f"Total rows (including header): {len(all_rows)}")
                
                # Try different row selectors
                selectors_to_try = [
                    f'{table_selector} tr[id*="grdWaterReports"]',
                    f'{table_selector} tbody tr',
                    f'{table_selector} tr:not(:first-child)',
                ]
                
                for selector in selectors_to_try:
                    rows = await page.locator(selector).all()
                    print(f"\nSelector: {selector}")
                    print(f"Rows found: {len(rows)}")
                    
                    if len(rows) > 0:
                        print(f"\nFirst row details:")
                        first_row = rows[0]
                        cells = await first_row.locator('td').all()
                        print(f"  Cells in first row: {len(cells)}")
                        
                        for i, cell in enumerate(cells):
                            text = await cell.inner_text()
                            print(f"  Cell {i}: {text.strip()}")
                        
                        # Check for checkbox
                        checkbox = first_row.locator('input[type="checkbox"]')
                        checkbox_count = await checkbox.count()
                        print(f"  Checkbox found: {checkbox_count > 0}")
                        
                        break
            
            # Keep browser open for manual inspection
            print("\n\nBrowser will stay open for 60 seconds for manual inspection...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_table())
