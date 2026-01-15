import asyncio
import json
from app import logger
from app.config import configuration
from pathlib import Path
from typing import Dict, List
import re
import os
import csv

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.yield_basis.telegram_bot import TelegramNotifier


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

        # Full path for the current and history storage files
        file_path_last_data = os.path.join(configuration.STORAGE_FOLDER, configuration.STORAGE_FILE_YIELDBASIS_LAST_DATA)
        self.file_last_data = Path(file_path_last_data)

        file_path_history_data = os.path.join(configuration.STORAGE_FOLDER, configuration.STORAGE_FILE_YIELDBASIS_HISTORY_DATA)
        self.file_history_data = Path(file_path_history_data)
        
    def load_previous_data(self) -> Dict:
        """Load previously stored capacity data"""
        try:
            if self.file_last_data.exists():
                with open(self.file_last_data, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} previous entries")
                    return data
        except Exception as e:
            logger.error(f"Error loading previous data: {e}")
        return {}
    
    def save_current_data(self, data: Dict):
        """Save current capacity data"""
        try:
            with open(self.file_last_data, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(data)} entries to storage")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def save_history_data(self, data_list: List):
        """
        Add current capacity data to the history storage
        Creates file with header if it doesn't exist.
        """
        try:
            # Define the header/field names
            field_names = ['timestamp', 'token', 'capacity', 'ft_apy_30d', 'token_apr', 'tvl']

            # Check if file exists
            file_exists_flag = os.path.isfile(self.file_history_data)
        
            # Open file in append mode
            with open(self.file_history_data, 'a', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=field_names)
                
                # Write header only if file is new
                if not file_exists_flag:
                    writer.writeheader()
                    logger.info(f"Created new CSV file to store history data: {self.file_history_data}")
                
                # Write all data rows
                for data in data_list:
                    writer.writerow(data)
                
                logger.info(f"Successfully appended {len(data_list)} row(s) to {self.file_history_data}")
                
        except Exception as e:
            logger.error(f"Error saving data to history CSV file: {e}")
    
    async def scrape_capacity_data(self) -> List[Dict]:
        """Scrape capacity data from YieldBasis using Playwright"""
        logger.info(f"Starting scrape of {configuration.TARGET_URL_YIELDBASIS}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=configuration.HEADLESS)
            
            try:
                page = await browser.new_page()
                
                # Navigate to page
                logger.info("Navigating to YieldBasis...")
                await page.goto(configuration.TARGET_URL_YIELDBASIS, wait_until='networkidle', timeout=configuration.TIMEOUT)
                
                # Wait for table to load
                logger.info("Waiting for table to load...")
                await page.wait_for_selector('table', timeout=configuration.TIMEOUT)
                
                # Additional wait for dynamic content
                await asyncio.sleep(configuration.PAGE_LOAD_WAITING_TIME)
                
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

            # Save scrapped data to the history storage
            self.save_history_data(current_data_list)
            
            # Convert to dict for actual storage and comparison
            current_data = {}
            for item in current_data_list:
                key = f"{item['token']}"
                current_data[key] = item
            
            # Detect changes
            changes = self.detect_changes(previous_data, current_data)
            
            # This ensures that if any notification fails, the previous data will be retained 
            # and the same changes will be detected again on the next check.
            if changes:
                logger.info(f"Detected {len(changes)} change(s)")
                
                # Send notifications for each change
                all_notifications_successful = True
                for change in changes:
                    try:
                        await self.notifier.send_capacity_change(change)
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to send notification for change: {e}")
                        all_notifications_successful = False
            
                # Save current data
                if all_notifications_successful:
                    self.save_current_data(current_data)
                    logger.info("All notifications sent successfully, data saved")
                else:
                    logger.warning("Some notifications failed, data not saved, changes will be detected again on the next check")

            else:
                logger.info("No changes detected")
            
            logger.info("Check iteration completed")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Check failed: {e}", exc_info=True)
#            await self.notifier.send_error_alert(f"Monitor check failed: {str(e)}")
    
    async def run_scheduled(self):
        """Run checks on schedule"""
        logger.info(f"Starting scheduled monitoring (every {configuration.CHECK_INTERVAL_SECONDS_YIELDBASIS} seconds)")
        
        # Send startup notification
        await self.notifier.send_status_update(
            f"Monitor started\n"
            f"Checking every {configuration.CHECK_INTERVAL_SECONDS_YIELDBASIS} seconds\n"
            f"Target: {configuration.TARGET_URL_YIELDBASIS}"
        )
        
        # Run immediately
        await self.check_and_notify()
        
        # Keep running with async sleep
        while True:
            await asyncio.sleep(configuration.CHECK_INTERVAL_SECONDS_YIELDBASIS)
            await self.check_and_notify()