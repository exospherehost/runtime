from beanie import PydanticObjectId
from fastapi import HTTPException, status, BackgroundTasks

from app.models.executed_models import ExecutedRequestModel, ExecutedResponseModel
from app.models.db.state import State
from app.models.state_status_enum import StateStatusEnum
from app.singletons.logs_manager import LogsManager
from app.tasks.create_next_states import create_next_states

logger = LogsManager().get_logger()


async def executed_state(
    namespace_name: str,
    state_id: PydanticObjectId,
    body: ExecutedRequestModel,
    x_exosphere_request_id: str,
    background_tasks: BackgroundTasks,
) -> ExecutedResponseModel:
    try:
        logger.info(
            f"Executed state {state_id} for namespace {namespace_name}",
            x_exosphere_request_id=x_exosphere_request_id,
        )

        state = await State.find_one(State.id == state_id)
        if not state or not state.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State not found",
            )

        if state.status != StateStatusEnum.QUEUED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State is not queued",
            )

        next_state_ids: list[PydanticObjectId] = []

        # ---- Handle outputs ----
        if len(body.outputs) == 0:
            state.status = StateStatusEnum.EXECUTED
            state.outputs = {}
            await state.save()

            next_state_ids.append(state.id)

        else:
            # First output updates the current state
            state.outputs = body.outputs[0]
            state.status = StateStatusEnum.EXECUTED
            await state.save()

            next_state_ids.append(state.id)

            # Remaining outputs create new states
            new_states = []
            for output in body.outputs[1:]:
                new_states.append(
                    State(
                        node_name=state.node_name,
                        namespace_name=state.namespace_name,
                        identifier=state.identifier,
                        graph_name=state.graph_name,
                        run_id=state.run_id,
                        status=StateStatusEnum.EXECUTED,
                        inputs=state.inputs,
                        outputs=output,
                        error=None,
                        parents=state.parents,
                    )
                )

            if new_states:
                inserted_ids = (
                    await State.insert_many(new_states)
                ).inserted_ids
                next_state_ids.extend(inserted_ids)

        # ---- Create next states ----
        background_tasks.add_task(
            create_next_states,
            next_state_ids,
            state.identifier,
            state.namespace_name,
            state.graph_name,
            state.parents,
        )

        return ExecutedResponseModel(
            status=StateStatusEnum.EXECUTED
        )

    except Exception as e:
        logger.error(
            f"Error executing state {state_id} for namespace {namespace_name}",
            x_exosphere_request_id=x_exosphere_request_id,
            error=e,
        )
        raise
