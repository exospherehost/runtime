from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.models.db.trigger import DatabaseTriggers
from app.models.trigger_models import TriggerStatusEnum, TriggerTypeEnum
from app.singletons.logs_manager import LogsManager
from app.controller.trigger_graph import trigger_graph
from app.models.trigger_graph_model import TriggerGraphRequestModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.config.settings import get_settings
import croniter
import asyncio

logger = LogsManager().get_logger()

async def get_due_triggers(cron_time: datetime) -> DatabaseTriggers | None:
    data = await DatabaseTriggers.get_pymongo_collection().find_one_and_update(
        {
            "trigger_time": {"$lte": cron_time},
            "trigger_status": TriggerStatusEnum.PENDING
        },
        {
            "$set": {"trigger_status": TriggerStatusEnum.TRIGGERING}
        },
        return_document=ReturnDocument.AFTER
    )
    return DatabaseTriggers(**data) if data else None

async def call_trigger_graph(trigger: DatabaseTriggers):
    await trigger_graph(
        namespace_name=trigger.namespace,
        graph_name=trigger.graph_name,
        body=TriggerGraphRequestModel(),
        x_exosphere_request_id=str(uuid4())
    )

async def mark_as_failed(trigger: DatabaseTriggers, retention_hours: int):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=retention_hours)

    await DatabaseTriggers.get_pymongo_collection().update_one(
        {"_id": trigger.id},
        {"$set": {
            "trigger_status": TriggerStatusEnum.FAILED,
            "expires_at": expires_at
        }}
    )

async def create_next_triggers(trigger: DatabaseTriggers, cron_time: datetime, retention_hours: int):
    assert trigger.expression is not None
    iter = croniter.croniter(trigger.expression, trigger.trigger_time)

    while True:
        next_trigger_time = iter.get_next(datetime)
        expires_at = next_trigger_time + timedelta(hours=retention_hours)

        try:
            await DatabaseTriggers(
                type=TriggerTypeEnum.CRON,
                expression=trigger.expression,
                graph_name=trigger.graph_name,
                namespace=trigger.namespace,
                trigger_time=next_trigger_time,
                trigger_status=TriggerStatusEnum.PENDING,
                expires_at=expires_at
            ).insert()
        except DuplicateKeyError:
            logger.error(f"Duplicate trigger found for expression {trigger.expression}")
        except Exception as e:
            logger.error(f"Error creating next trigger: {e}")
            raise

        if next_trigger_time > cron_time:
            break

async def mark_as_triggered(trigger: DatabaseTriggers, retention_hours: int):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=retention_hours)

    await DatabaseTriggers.get_pymongo_collection().update_one(
        {"_id": trigger.id},
        {"$set": {
            "trigger_status": TriggerStatusEnum.TRIGGERED,
            "expires_at": expires_at
        }}
    )

async def handle_trigger(cron_time: datetime, retention_hours: int):
    while(trigger:= await get_due_triggers(cron_time)):
        try:
            await call_trigger_graph(trigger)
            await mark_as_triggered(trigger, retention_hours)
        except Exception as e:
            await mark_as_failed(trigger, retention_hours)
            logger.error(f"Error calling trigger graph: {e}")
        finally:
            await create_next_triggers(trigger, cron_time, retention_hours)

async def trigger_cron():
    cron_time = datetime.now()
    settings = get_settings()
    logger.info(f"starting trigger_cron: {cron_time}")
    await asyncio.gather(*[handle_trigger(cron_time, settings.trigger_retention_hours) for _ in range(settings.trigger_workers)])

async def mark_as_cancelled(trigger: DatabaseTriggers, retention_hours: int):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=retention_hours)

    await DatabaseTriggers.get_pymongo_collection().update_one(
        {"_id": trigger.id},
        {"$set": {
            "trigger_status": TriggerStatusEnum.CANCELLED,
            "expires_at": expires_at
        }}
    )