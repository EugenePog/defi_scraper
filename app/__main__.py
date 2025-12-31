import asyncio
from app import logger

from app.yield_basis.monitor import YieldBasisMonitor

if __name__ == "__main__":
    try:
        yield_basis_monitor = YieldBasisMonitor()

        asyncio.run(yield_basis_monitor.run_scheduled())
        
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)