from app.models.signal_models import ReEnqueueAfterRequestModel, SignalResponseModel
from fastapi import HTTPException, status
from beanie import PydanticObjectId
import time

from app.models.db.state import State
from app.models.state_status_enum import StateStatusEnum
from app.singletons.logs_manager import LogsManager

logger = LogsManager().get_logger()

async def re_queue_after_signal(namespace_name: str, state_id: PydanticObjectId, body: ReEnqueueAfterRequestModel, x_exosphere_request_id: str) -> SignalResponseModel:

    try:
        logger.info(f"Received re-queue after signal for state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)

        state = await State.find_one(State.id == state_id)

        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")

        state.status = StateStatusEnum.CREATED
        state.enqueue_after = int(time.time() * 1000) + body.enqueue_after
        state.timeout_at = None
        state.queued_at = None
        await state.save()

        return SignalResponseModel(status=StateStatusEnum.CREATED, enqueue_after=state.enqueue_after)

    except Exception as e:
        logger.error(f"Error re-queueing state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id, error=e)
        raise