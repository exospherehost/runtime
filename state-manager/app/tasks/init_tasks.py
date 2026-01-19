# tasks to run when the server starts
from datetime import datetime, timedelta, timezone
import asyncio

from app.config.settings import get_settings
from app.models.db.trigger import DatabaseTriggers
from app.models.trigger_models import TriggerStatusEnum
from app.singletons.logs_manager import LogsManager

logger = LogsManager().get_logger()


async def mark_old_triggers_cancelled() -> None:
    """
    Migrate legacy TRIGGERED/FAILED triggers that predate TTL.

    These documents have expires_at = None, so we mark them as CANCELLED and
    set expires_at so the TTL index can eventually clean them up.
    """
    settings = get_settings()
    retention_hours = settings.trigger_retention_hours
    expires_at = datetime.now(timezone.utc) + timedelta(hours=retention_hours)

    # Use the same filter used before by delete_many()
    filter_query = {
        "trigger_status": {
            "$in": [
                TriggerStatusEnum.TRIGGERED.value,
                TriggerStatusEnum.FAILED.value,
            ]
        },
        "expires_at": None,
    }

    logger.info(
        "Init task marking legacy TRIGGERED/FAILED triggers as CANCELLED "
        f"for filter={filter_query}, expires_at={expires_at.isoformat()}"
    )

    await DatabaseTriggers.get_pymongo_collection().update_many(
        filter_query,
        {
            "$set": {
                "trigger_status": TriggerStatusEnum.CANCELLED.value,
                "expires_at": expires_at,
            }
        },
    )


async def init_tasks() -> None:
    await asyncio.gather(
        mark_old_triggers_cancelled(),
    )
