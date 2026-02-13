import time
from app.models.db.state import State
from app.models.state_status_enum import StateStatusEnum
from app.singletons.logs_manager import LogsManager

logger = LogsManager().get_logger()


async def check_node_timeout():
    try:
        current_time_ms = int(time.time() * 1000)

        logger.info(f"Checking for timed out nodes at {current_time_ms}")

        # Use database query to find and update timed out states in one operation
        result = await State.get_pymongo_collection().update_many(
            {
                "status": StateStatusEnum.QUEUED,
                "timeout_at": {"$ne": None, "$lte": current_time_ms}
            },
            {
                "$set": {
                    "status": StateStatusEnum.TIMEDOUT,
                    "error": "Node execution timed out"
                }
            }
        )

        if result.modified_count > 0:
            logger.info(f"Marked {result.modified_count} states as TIMEDOUT")
        
    except Exception:
        logger.error("Error checking node timeout", exc_info=True)
