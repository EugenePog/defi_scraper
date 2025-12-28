import asyncio
from telegram import Bot
from telegram.error import TelegramError
from app import logger
from app.config import configuration

class TelegramNotifier:
    def __init__(self):
        self.bot = Bot(token=configuration.TELEGRAM_BOT_TOKEN)
        self.chat_id = configuration.TELEGRAM_CHAT_ID
    
    async def send_message(self, message: str, parse_mode: str = 'HTML'):
        """Send a message to Telegram"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("Telegram notification sent successfully")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def send_capacity_change(self, change: dict):
        """Format and send capacity change notification"""
        message = self._format_change_message(change)
        await self.send_message(message)
    
    def _format_change_message(self, change: dict) -> str:
        """Format change data into readable message"""
        change_type = change.get('type')
        
        if change_type == 'NEW':
            return (
                f"🆕 <b>New Pool Detected</b>\n\n"
                f"Protocol: <b>{change['protocol']}</b>\n"
                f"Asset: <b>{change['asset']}</b>\n"
                f"Capacity: <code>{change['capacity']}</code>\n"
                f"APY: <code>{change.get('apy', 'N/A')}</code>\n"
                f"TVL: <code>{change.get('tvl', 'N/A')}</code>"
            )
        
        elif change_type == 'CAPACITY_CHANGE':
            # Determine if capacity increased or decreased
            emoji = "📈" if self._is_increase(change['old_capacity'], change['new_capacity']) else "📉"
            
            return (
                f"{emoji} <b>Capacity Changed</b>\n\n"
                f"Protocol: <b>{change['protocol']}</b>\n"
                f"Asset: <b>{change['asset']}</b>\n"
                f"Old Capacity: <code>{change['old_capacity']}</code>\n"
                f"New Capacity: <code>{change['new_capacity']}</code>\n"
                f"APY: <code>{change.get('apy', 'N/A')}</code>"
            )
        
        elif change_type == 'APY_CHANGE':
            emoji = "💰" if self._is_increase(change['old_apy'], change['new_apy']) else "💸"
            
            return (
                f"{emoji} <b>APY Changed</b>\n\n"
                f"Protocol: <b>{change['protocol']}</b>\n"
                f"Asset: <b>{change['asset']}</b>\n"
                f"Old APY: <code>{change['old_apy']}</code>\n"
                f"New APY: <code>{change['new_apy']}</code>\n"
                f"Capacity: <code>{change['capacity']}</code>"
            )
        
        else:
            return f"ℹ️ Change detected: {change}"
    
    def _is_increase(self, old_value: str, new_value: str) -> bool:
        """Check if value increased (handles strings with $ and commas)"""
        try:
            old_num = float(old_value.replace('$', '').replace(',', '').replace('%', ''))
            new_num = float(new_value.replace('$', '').replace(',', '').replace('%', ''))
            return new_num > old_num
        except:
            return False
    
    async def send_status_update(self, status: str):
        """Send status update message"""
        message = f"ℹ️ <b>Monitor Status</b>\n\n{status}"
        await self.send_message(message)
    
    async def send_error_alert(self, error_message: str):
        """Send error alert"""
        message = f"⚠️ <b>Error Alert</b>\n\n<code>{error_message}</code>"
        await self.send_message(message)