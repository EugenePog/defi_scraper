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
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 5))
    STORAGE_FILE = 'data/out/capacity_data.json'

configuration = Configuration()