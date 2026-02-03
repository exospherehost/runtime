from pymongo.errors import DuplicateKeyError
from app.models.manual_retry import ManualRetryRequestModel, ManualRetryResponseModel
from beanie import PydanticObjectId
from app.singletons.logs_manager import LogsManager
from app.models.state_status_enum import StateStatusEnum
from fastapi import HTTPException, status
from app.models.db.state import State


logger = LogsManager().get_logger()

async def manual_retry_state(namespace_name: str, state_id: PydanticObjectId, body: ManualRetryRequestModel, x_exosphere_request_id: str):
    try:
        logger.info(f"Manual retry state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)

        state = await State.find_one(State.id == state_id, State.namespace_name == namespace_name)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
        
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
                fanout_id=body.fanout_id, # this will ensure that multiple unwanted retries are not formed because of index in database
                manual_retry_fanout_id=body.fanout_id, # This is included in the state fingerprint to allow unique manual retries of unite nodes.
                timeout_minutes=state.timeout_minutes
            )
            retry_state = await retry_state.insert()
            logger.info(f"Retry state {retry_state.id} created for state {state_id}", x_exosphere_request_id=x_exosphere_request_id)

            state.status = StateStatusEnum.RETRY_CREATED
            await state.save()

            return ManualRetryResponseModel(id=str(retry_state.id), status=retry_state.status)
        except DuplicateKeyError:
            logger.info(f"Duplicate retry state detected for state {state_id}. A retry state with the same unique key already exists.", x_exosphere_request_id=x_exosphere_request_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate retry state detected")


    except Exception as _:
        logger.error(f"Error manual retry state {state_id} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise
