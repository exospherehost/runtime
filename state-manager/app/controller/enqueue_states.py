import asyncio
import time

from ..models.enqueue_request import EnqueueRequestModel
from ..models.enqueue_response import EnqueueResponseModel, StateModel
from ..models.db.state import State
from ..models.state_status_enum import StateStatusEnum

from app.singletons.logs_manager import LogsManager
from app.config.settings import get_settings
from pymongo import ReturnDocument

logger = LogsManager().get_logger()


async def find_state(namespace_name: str, nodes: list[str]) -> State | None:
    current_time_ms = int(time.time() * 1000)
    settings = get_settings()
    
    data = await State.get_pymongo_collection().find_one_and_update(
        {
            "namespace_name": namespace_name,
            "status": StateStatusEnum.CREATED,
            "node_name": {"$in": nodes},
            "enqueue_after": {"$lte": current_time_ms}
        },
        [
            {
                "$set": {
                    "status": StateStatusEnum.QUEUED,
                    "queued_at": current_time_ms,
                    "timeout_at": {
                        "$add": [
                            current_time_ms,
                            {
                                "$multiply": [
                                    {
                                        "$ifNull": [
                                            "$timeout_minutes", 
                                            settings.node_timeout_minutes
                                        ]
                                    },
                                    60000  # Convert minutes to milliseconds
                                ]
                            }
                        ]
                    }
                }
            }
        ],
        return_document=ReturnDocument.AFTER
    )
    return State(**data) if data else None

async def enqueue_states(namespace_name: str, body: EnqueueRequestModel, x_exosphere_request_id: str) -> EnqueueResponseModel:
    
    try:
        logger.info(f"Enqueuing states for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)

        # Create tasks for parallel execution
        tasks = [find_state(namespace_name, body.nodes) for _ in range(body.batch_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        states = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error finding state: {result}", x_exosphere_request_id=x_exosphere_request_id)
                continue
            if result is not None:
                states.append(result)

        response = EnqueueResponseModel(
            count=len(states),
            namespace=namespace_name,
            status=StateStatusEnum.QUEUED,
            states=[
                StateModel(
                    state_id=str(state.id),
                    node_name=state.node_name,
                    identifier=state.identifier,
                    inputs=state.inputs,
                    created_at=state.created_at
                )
                for state in states
            ]
        )
        return response
    
    except Exception as e:
        logger.error(f"Error enqueuing states for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id, error=e)
        raise e