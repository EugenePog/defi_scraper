import os
from dotenv import load_dotenv

load_dotenv()

class Configuration:
    PROJECT_NAME = "Defi data scraper"
    LOG_FOLDER = "data/logs/"
    LOG_FILE = "defi_scraper.log"
    SETTINGS_FILE_PATH = "data/settings.json"
    MONITOR_FLAGS = {'YIELDBASIS': 1} # Future development: switch to reading dictionary of flags from SETTINGS_FILE_PATH

    # Browser settings
    HEADLESS = True
    TIMEOUT = 60000  # 60 seconds
    PAGE_LOAD_WAITING_TIME = 10  # 10 seconds

    # Telegram settings (general)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    # Telegram settings (object dependent)
    # YIELDBASIS
    TELEGRAM_CHAT_ID_YIELDBASIS = os.getenv('TELEGRAM_CHAT_ID_YIELDBASIS')

    # Monitoring settings (object dependent)
    # YIELDBASIS
    TARGET_URL_YIELDBASIS = 'https://yieldbasis.com/earn'
    CHECK_INTERVAL_SECONDS_YIELDBASIS = int(os.getenv('CHECK_INTERVAL_SECONDS', 120)) # Future development: switch to reading from SETTINGS_FILE_PATH

    # Storage settings (general)
    STORAGE_FOLDER = "data/out/"
    # Storage settings (object dependent)
    # YIELDBASIS
    STORAGE_FILE_YIELDBASIS_LAST_DATA = 'yieldbasis_capacity_data.json'
    STORAGE_FILE_YIELDBASIS_HISTORY_DATA = 'yieldbasis_capacity_data_history.csv'

    # Blockchain settings
    ALCHEMY_URL_ETH = os.getenv('ALCHEMY_URL_ETH')
    YIELDBASIS_Stake_Zap = '0xE862bC39B8D5F12D8c4117d3e2D493Dc20051EC6'
    YIELDBASIS_cbBTC_Leverage = '0xAC0cfa7742069a8af0c63e14FFD0fe6b3e1Bf8D2'
    YIELDBASIS_cbBTC_POOL = '0x83f24023d15d835a213df24fd309c47dAb5BEb32'

configuration = Configuration()