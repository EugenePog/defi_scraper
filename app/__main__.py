import asyncio
from app import logger

from app.yield_basis.monitor import main_yield_basis

if __name__ == "__main__":
    try:
        asyncio.run(main_yield_basis())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)