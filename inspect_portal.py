#!/usr/bin/env python3
"""
Script to save portal HTML for analysis
"""

import asyncio
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright

load_dotenv()


async def save_portal_html():
    """Save portal HTML after login for analysis"""
    
    portal_url = os.getenv('PORTAL_URL')
    username = os.getenv('PORTAL_USERNAME')
    password = os.getenv('PORTAL_PASSWORD')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("Navigating to portal...")
            await page.goto(portal_url, wait_until='networkidle')
            
            print("Logging in...")
            # Use generic selectors that worked before
            await page.fill('input[type="text"]', username)
            await page.fill('input[type="password"]', password)
            await page.click('input[type="submit"]')
            
            await page.wait_for_load_state('networkidle')
            print("Login successful!")
            
            # Save main page HTML
            content = await page.content()
            with open('portal_main.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Saved main page HTML to portal_main.html")
            
            # Take screenshot
            await page.screenshot(path='portal_main.png', full_page=True)
            print("Saved screenshot to portal_main.png")
            
            # Try to click Water tab
            print("\nLooking for Water tab...")
            # Try multiple possible selectors
            water_selectors = [
                'a:has-text("Water")',
                'a#lnkWater',
                'a[href*="Water"]',
                'li:has-text("Water") a',
                'tab:has-text("Water")'
            ]
            
            water_clicked = False
            for selector in water_selectors:
                try:
                    water_tab = page.locator(selector).first
                    if await water_tab.count() > 0:
                        print(f"Found Water tab with selector: {selector}")
                        await water_tab.click()
                        await page.wait_for_load_state('networkidle')
                        water_clicked = True
                        break
                except:
                    continue
            
            if water_clicked:
                print("Clicked Water tab successfully!")
                
                # Save Water page HTML
                content = await page.content()
                with open('portal_water.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("Saved Water page HTML to portal_water.html")
                
                # Take screenshot
                await page.screenshot(path='portal_water.png', full_page=True)
                print("Saved screenshot to portal_water.png")
            else:
                print("Could not find Water tab")
            
            # Analyze page structure
            print("\n" + "="*60)
            print("Analyzing page structure...")
            print("="*60)
            
            # Look for tables
            tables = await page.locator('table').all()
            print(f"\nFound {len(tables)} table(s)")
            
            # Look for links with PDF
            pdf_links = await page.locator('a[href*=".pdf"]').all()
            print(f"Found {len(pdf_links)} PDF link(s)")
            
            # Look for download-related elements
            download_elements = await page.locator('[class*="download"], [id*="download"], img[alt*="download" i], img[src*="download" i]').all()
            print(f"Found {len(download_elements)} download-related element(s)")
            
            # Print first few download elements
            if download_elements:
                print("\nFirst 5 download elements:")
                for i, elem in enumerate(download_elements[:5]):
                    try:
                        tag = await elem.evaluate('el => el.tagName')
                        classes = await elem.get_attribute('class') or ''
                        id_attr = await elem.get_attribute('id') or ''
                        href = await elem.get_attribute('href') or ''
                        src = await elem.get_attribute('src') or ''
                        print(f"  {i+1}. <{tag}> class='{classes}' id='{id_attr}' href='{href}' src='{src}'")
                    except:
                        pass
            
            print("\n" + "="*60)
            print("Browser will stay open for 30 seconds for manual inspection")
            print("="*60)
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(save_portal_html())
