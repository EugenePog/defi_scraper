import os
from dotenv import load_dotenv

load_dotenv()

class Configuration:
    PROJECT_NAME = "Defi scraper"
    LOG_FOLDER = "data/logs/"
    LOG_FILE = "defi_scraper.log"
    SETTINGS_FILE_PATH = "data/settings.json"

    # Browser settings
    HEADLESS = True
    TIMEOUT = 60000  # 60 seconds

    # Telegram settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Monitoring settings
    TARGET_URL = 'https://yieldbasis.com/earn'
    CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', 60))
    STORAGE_FOLDER = "data/out/"
    STORAGE_FILE_LAST_DATA = 'capacity_data.json'
    STORAGE_FILE_HISTORY_DATA = 'capacity_data_history.csv'

configuration = Configuration()