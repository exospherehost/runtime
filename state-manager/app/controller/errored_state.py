import time

from app.models.errored_models import ErroredRequestModel, ErroredResponseModel
from fastapi import HTTPException, status
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from app.models.db.state import State
from app.models.state_status_enum import StateStatusEnum
from app.singletons.logs_manager import LogsManager
from app.models.db.graph_template_model import GraphTemplate
from app.tasks.webhook import dispatch_webhook
from datetime import datetime
from fastapi import BackgroundTasks

logger = LogsManager().get_logger()
async def errored_state(namespace_name: str, state_id: PydanticObjectId, body: ErroredRequestModel, x_exosphere_request_id: str, background_tasks: BackgroundTasks | None = None,) -> ErroredResponseModel:
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    try:
        logger.info(f"Errored state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)

        state = await State.find_one(State.id == state_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
        
        if state.status != StateStatusEnum.QUEUED and state.status != StateStatusEnum.EXECUTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State is not queued or executed")
        
        if state.status == StateStatusEnum.EXECUTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State is already executed")
        
        try:
            graph_template = await GraphTemplate.get(namespace_name, state.graph_name)
        except Exception as e:
            logger.error(f"Error getting graph template {state.graph_name} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id, error=e)
            if isinstance(e, ValueError) and "Graph template not found" in str(e):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph template not found")
            raise e

        retry_created = False

        if state.retry_count < graph_template.retry_policy.max_retries:
            try:
                retry_state = State(
                    node_name=state.node_name,
                    namespace_name=state.namespace_name,
                    identifier=state.identifier,
                    graph_name=state.graph_name,
                    run_id=state.run_id,
                    status=StateStatusEnum.CREATED,
                    inputs=state.inputs,
                    outputs={},
                    error=None,
                    parents=state.parents,
                    does_unites=state.does_unites,
                    enqueue_after= int(time.time() * 1000) + graph_template.retry_policy.compute_delay(state.retry_count + 1),
                    retry_count=state.retry_count + 1,
                    fanout_id=state.fanout_id
                )
                retry_state = await retry_state.insert()
                logger.info(f"Retry state {retry_state.id} created for state {state_id}", x_exosphere_request_id=x_exosphere_request_id)
                retry_created = True
            except DuplicateKeyError:
                logger.info(f"Duplicate retry state detected for state {state_id}. A retry state with the same unique key already exists.", x_exosphere_request_id=x_exosphere_request_id)
                retry_created = True

        if retry_created:
            state.status = StateStatusEnum.RETRY_CREATED
        else:
            state.status = StateStatusEnum.ERRORED
            
        state.error = body.error
        await state.save()

        if (
            not retry_created
            and graph_template.webhook
            and "GRAPH_FAILED" in graph_template.webhook.events
        ):
            background_tasks.add_task(
                dispatch_webhook,
                url=graph_template.webhook.url,
                payload={
                    "event": "GRAPH_FAILED",
                    "namespace": namespace_name,
                    "graph_name": state.graph_name,
                    "run_id": state.run_id,
                    "failed_state_id": str(state.id),
                    "node_name": state.node_name,
                    "error": body.error,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                headers=graph_template.webhook.headers,
            )
        return ErroredResponseModel(status=StateStatusEnum.ERRORED, retry_created=retry_created)

    except Exception as e:
        logger.error(f"Error errored state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id, error=e)
        raise e