import asyncio
from app import logger

from app.yield_basis.monitor import YieldBasisMonitor
from app.yield_basis.smart_api import get_smart_contract_data

if __name__ == "__main__":
    try:
        yield_basis_monitor = YieldBasisMonitor()

        asyncio.run(yield_basis_monitor.run_scheduled())
        #get_smart_contract_data()
        
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)