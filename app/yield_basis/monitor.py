import asyncio
import json
from app import logger
from app.config import configuration
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import schedule
import time
import re
import os

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.yield_basis.telegram_bot import TelegramNotifier

TARGET_URL = configuration.TARGET_URL
CHECK_INTERVAL_SECONDS = configuration.CHECK_INTERVAL_SECONDS 
HEADLESS = configuration.HEADLESS
TIMEOUT = configuration.TIMEOUT


MULTIPLIERS = {
    'K': 1_000,
    'M': 1_000_000,
    'B': 1_000_000_000,
}

def parse_token_name_and_tvl(text: str) -> tuple[float, str]:
    # normalize weird spaces
    text = text.replace('\xa0', ' ').strip()

    pattern = r'^(\d+(?:\.\d+)?)([KMB]?)\s+([A-Za-z0-9]+)\s*\$'
    m = re.search(pattern, text)

    if not m:
        raise ValueError(f"Invalid token name and TVL format: {repr(text)}")

    number = float(m.group(1))
    suffix = m.group(2)
    token = m.group(3)

    tvl = number * MULTIPLIERS.get(suffix, 1)

    return tvl, token

class YieldBasisMonitor:
    def __init__(self):
        self.notifier = TelegramNotifier()

        # Create the storage folder if it doesn't exist
        if not os.path.exists(configuration.STORAGE_FOLDER):
            os.makedirs(configuration.STORAGE_FOLDER)

        # Full path for the storage file
        file_path = os.path.join(configuration.STORAGE_FOLDER, configuration.STORAGE_FILE)
        self.storage_file = Path(file_path)
        
    def load_previous_data(self) -> Dict:
        """Load previously stored capacity data"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} previous entries")
                    return data
        except Exception as e:
            logger.error(f"Error loading previous data: {e}")
        return {}
    
    def save_current_data(self, data: Dict):
        """Save current capacity data"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(data)} entries to storage")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    async def scrape_capacity_data(self) -> List[Dict]:
        """Scrape capacity data from YieldBasis using Playwright"""
        logger.info(f"Starting scrape of {TARGET_URL}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)
            
            try:
                page = await browser.new_page()
                
                # Navigate to page
                logger.info("Navigating to YieldBasis...")
                await page.goto(TARGET_URL, wait_until='networkidle', timeout=TIMEOUT)
                
                # Wait for table to load
                logger.info("Waiting for table to load...")
                await page.wait_for_selector('table', timeout=TIMEOUT)
                
                # Additional wait for dynamic content
                await asyncio.sleep(5)
                
                # Extract table data
                logger.info("Extracting table data...")
                capacity_data = await page.evaluate('''() => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    
                    return rows.map(row => {
                        const cells = Array.from(row.querySelectorAll('td'));
                        
                        // Extract text from each cell
                        const getText = (index) => {
                            return cells[index]?.textContent?.trim() || '';
                        };
                        
                        // Get all data from columns 1-6
                        return {
                            col1_asset: getText(1),      // Asset symbol
                            col2_ft_apy: getText(2),     // FT APY (3D%)
                            col3_ot: getText(3),         // OT info
                            col4_token_apr: getText(4),  // Token APR
                            col5_tvl: getText(5),        // TVL
                            col6_capacity: getText(6),   // Capacity status
                            
                            // Keep all columns as array for flexibility
                            all_columns: [
                                getText(1),
                                getText(2),
                                getText(3),
                                getText(4),
                                getText(5),
                                getText(6)
                            ],
                            
                            timestamp: new Date().toISOString()
                        };
                    }).filter(item => item.col1_asset); // Filter out empty rows
                }''')
                
                logger.info(f"Successfully scraped {len(capacity_data)} rows")

                return_data = []
                for row in capacity_data:
                    tvl, token = parse_token_name_and_tvl(row['col4_token_apr'])
                    if row['col5_tvl'] == 'FILLED':
                        capacity = '100.00%'
                    else:
                        capacity = row['col5_tvl']
                    return_data.append({'timestamp': row['timestamp'], 'token': token, 'capacity': capacity, 'ft_apy_30d': row['col1_asset'], 'token_apr': row['col3_ot'], 'tvl': tvl})

                logger.info(f"Scraped data: {return_data}")
                return return_data
                
            except PlaywrightTimeout as e:
                logger.error(f"Timeout error: {e}")
                await self.notifier.send_error_alert(f"Scraping timeout: {str(e)}")
                raise
            
            except Exception as e:
                logger.error(f"Scraping error: {e}")
                await self.notifier.send_error_alert(f"Scraping failed: {str(e)}")
                raise
            
            finally:
                await browser.close()
    
    def detect_changes(self, previous_data: Dict, current_data: Dict) -> List[Dict]:
        """Compare previous and current data to detect changes"""
        changes = []
        
        # Check for changes
        for key, current in current_data.items():
            if key not in previous_data:
                # New entry
                changes.append({
                    'type': 'NEW',
                    'token': current['token'],
                    'capacity': current['capacity'],
                    'token_apr': current['token_apr'],
                    'tvl': current['tvl']
                })
                logger.info(f"New pool detected: {current['token']}, capacity: {current['capacity']}")
            
            else:
                previous = previous_data[key]
                
                # Check capacity change
                if previous['capacity'] != current['capacity']:
                    changes.append({
                        'type': 'CAPACITY_CHANGE',
                        'token': current['token'],
                        'new_capacity': current['capacity'],
                        'old_capacity': previous['capacity'],
                        'token_apr': current['token_apr'],
                        'tvl': current['tvl']
                    })
                    logger.info(f"Capacity changed: {current['token']}: current: {current['capacity']}, previous: {previous['capacity']}")
        
        return changes
    
    async def check_and_notify(self):
        """Main monitoring function"""
        try:
            logger.info("="*60)
            logger.info("Starting capacity check...")
            
            # Load previous data
            previous_data = self.load_previous_data()
            
            # Scrape current data
            current_data_list = await self.scrape_capacity_data()
            logger.info(f"current_data_list: {current_data_list}")
            
            # Convert to dict for storage and comparison
            current_data = {}
            for item in current_data_list:
                key = f"{item['token']}"
                current_data[key] = item
            
            # Detect changes
            changes = self.detect_changes(previous_data, current_data)
            
            if changes:
                logger.info(f"Detected {len(changes)} change(s)")
                
                # Send notifications for each change
                for change in changes:
                    await self.notifier.send_capacity_change(change)
                    await asyncio.sleep(1)  # Rate limiting
            else:
                logger.info("No changes detected")
            
            # Save current data
            self.save_current_data(current_data)
            
            logger.info("Check completed successfully")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Check failed: {e}", exc_info=True)
            await self.notifier.send_error_alert(f"Monitor check failed: {str(e)}")
    
    async def run_once(self):
        """Run check once (for testing)"""
        await self.check_and_notify()
    
    async def run_scheduled(self):
        """Run checks on schedule"""
        logger.info(f"Starting scheduled monitoring (every {CHECK_INTERVAL_SECONDS} seconds)")
        
        # Send startup notification
        await self.notifier.send_status_update(
            f"Monitor started\n"
            f"Checking every {CHECK_INTERVAL_SECONDS} seconds\n"
            f"Target: {TARGET_URL}"
        )
        
        # Run immediately
        await self.check_and_notify()
        
        # Schedule subsequent runs
        def job():
            asyncio.create_task(self.check_and_notify())
        
        schedule.every(CHECK_INTERVAL_SECONDS).seconds.do(job)
        
        # Keep running
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

async def main_yield_basis():
    """Main entry point to yield basis monitor"""
    import sys
    
    monitor = YieldBasisMonitor()
    
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        logger.info("Running in TEST mode (single check)")
        await monitor.run_once()
    else:
        logger.info("Running in SCHEDULED mode")
        await monitor.run_scheduled()

