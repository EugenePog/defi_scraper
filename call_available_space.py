from pathlib import Path
import sys
import asyncio

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import configuration
from app import logger
from typing import Dict
import aiohttp
import hmac
import hashlib
import time
import json
import os
from cryptography.fernet import Fernet


class PoolSpaceNotificator:
    def __init__(self):
        self.api_base_url = f"http://localhost:{configuration.API_PORT}"
        self.api_key = os.getenv("DEPOSIT_API_KEY")
        self.api_secret = os.getenv("DEPOSIT_API_SECRET")
        self.encryption_key = os.getenv("DEPOSIT_ENCRYPTION_KEY")
        self.cipher = Fernet(self.encryption_key.encode()) if self.encryption_key else None
        
        if not all([self.api_key, self.api_secret, self.encryption_key]):
            raise ValueError("Missing API credentials in environment variables!")
    
    def _generate_signature(self, payload: Dict, timestamp: int) -> str:
        """Generate HMAC signature for request authentication"""
        message = f"{timestamp}{json.dumps(payload, sort_keys=True)}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _encrypt_field(self, value: str) -> str:
        """Encrypt sensitive field"""
        str_value = str(value)
        return self.cipher.encrypt(str_value.encode()).decode()
    
    async def notify_available_pool_space(self, currect_data: Dict):
        try:
            logger.info(f"Send notification about this pool: {currect_data}")
            
            # Prepare deposit request payload
            deposit_payload = {
                "token": self._encrypt_field(currect_data['token']),
                "available_space": self._encrypt_field(currect_data['tvl'] * (100-float(currect_data['capacity'].replace("%", ""))) / 100)
            }
            
            # Generate timestamp and signature
            timestamp = int(time.time())
            signature = self._generate_signature(deposit_payload, timestamp)
            
            # Prepare headers with authentication
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": str(timestamp),
                "Content-Type": "application/json"
            }
            
            # Make async HTTPS request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/available_space_notify",
                    json=deposit_payload,
                    headers=headers,
                    ssl=True,  # Enforce SSL/TLS
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Deposit successful")
                        return result
                    elif response.status == 401:
                        logger.error("Authentication failed - invalid API key or signature")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Deposit failed with status {response.status}: {error_text}")
                        return None
    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request error: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")

async def run_deposit_executor():
    pool_space_notificator = PoolSpaceNotificator()
    test_pool_position = {
        'timestamp': '2026-01-11T11:34:01.477Z', 
        'token': 'WETH', 
        'capacity': '99.00%', 
        'ft_apy_30d': '9.87%', 
        'token_apr': '10.62%', 
        'tvl': 575.35}

    result = await pool_space_notificator.notify_available_pool_space(test_pool_position)
    logger.info(f"Result: {result}")

if __name__ == "__main__":
    try:
        asyncio.run(run_deposit_executor())
        
    except KeyboardInterrupt:
        logger.info(f"{configuration.PROJECT_NAME} stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)