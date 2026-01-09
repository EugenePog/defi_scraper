import asyncio
from app import logger

from app.yield_basis.monitor import YieldBasisMonitor

async def run_all_monitors():
    """Run multiple monitors concurrently"""
    
    # Create monitor objects for usage in asyncio
    yield_basis_monitor = YieldBasisMonitor()
    
    # Run all monitors concurrently
    await asyncio.gather(
        yield_basis_monitor.run_scheduled(),
        return_exceptions=True  # Continue if one monitor fails
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_all_monitors())
        
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)