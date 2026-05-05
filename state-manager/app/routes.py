from fastapi import APIRouter, status, Request, Depends, HTTPException, BackgroundTasks
from uuid import uuid4
from beanie import PydanticObjectId

from app.utils.check_secret import check_api_key
from app.singletons.logs_manager import LogsManager

from .models.enqueue_response import EnqueueResponseModel
from .models.enqueue_request import EnqueueRequestModel
from .controller.enqueue_states import enqueue_states

from .models.trigger_graph_model import TriggerGraphRequestModel, TriggerGraphResponseModel
from .controller.trigger_graph import trigger_graph

from .models.executed_models import ExecutedRequestModel, ExecutedResponseModel
from .controller.executed_state import executed_state

from .models.errored_models import ErroredRequestModel, ErroredResponseModel
from .controller.errored_state import errored_state

from .models.graph_models import UpsertGraphTemplateRequest, UpsertGraphTemplateResponse
from .controller.upsert_graph_template import upsert_graph_template as upsert_graph_template_controller
from .controller.get_graph_template import get_graph_template as get_graph_template_controller

from .models.register_nodes_request import RegisterNodesRequestModel
from .models.register_nodes_response import RegisterNodesResponseModel
from .controller.register_nodes import register_nodes

from .models.secrets_response import SecretsResponseModel
from .controller.get_secrets import get_secrets

from .models.list_models import ListRegisteredNodesResponse, ListGraphTemplatesResponse, ListNamespacesResponse
from .controller.list_registered_nodes import list_registered_nodes
from .controller.list_graph_templates import list_graph_templates
from .controller.list_namespaces import list_namespaces

from .models.run_models import RunsResponse
from .controller.get_runs import get_runs

from .models.graph_structure_models import GraphStructureResponse
from .controller.get_graph_structure import get_graph_structure

from .models.node_run_details_models import NodeRunDetailsResponse
from .controller.get_node_run_details import get_node_run_details

### signals
from .models.signal_models import SignalResponseModel
from .models.signal_models import PruneRequestModel
from .controller.prune_signal import prune_signal
from .models.signal_models import ReEnqueueAfterRequestModel
from .controller.re_queue_after_signal import re_queue_after_signal

# manual_retry
from .models.manual_retry import ManualRetryRequestModel, ManualRetryResponseModel
from .controller.manual_retry_state import manual_retry_state

# cancel_triggers
from .models.cancel_trigger_models import CancelTriggerResponse
from .controller.cancel_triggers import cancel_triggers


logger = LogsManager().get_logger()

# Global router for non-namespace specific endpoints
global_router = APIRouter(prefix="/v0")

# Namespace-specific router
router = APIRouter(prefix="/v0/namespace/{namespace_name}")


@router.post(
    "/states/enqueue",
    response_model=EnqueueResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State enqueued on node queue successfully",
    tags=["state"]
)
async def enqueue_state(namespace_name: str, body: EnqueueRequestModel, request: Request, api_key: str = Depends(check_api_key)):

    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await enqueue_states(namespace_name, body, x_exosphere_request_id)


@router.post(
    "/graph/{graph_name}/trigger",
    response_model=TriggerGraphResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="Graph triggered successfully with new run ID",
    tags=["graph"]
)
async def trigger_graph_route(namespace_name: str, graph_name: str, body: TriggerGraphRequestModel, request: Request, api_key: str = Depends(check_api_key)):

    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await trigger_graph(namespace_name, graph_name, body, x_exosphere_request_id)

@router.post(
    "/state/{state_id}/executed",
    response_model=ExecutedResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State executed successfully",
    tags=["state"]
)
async def executed_state_route(namespace_name: str, state_id: str, body: ExecutedRequestModel, request: Request, background_tasks: BackgroundTasks, api_key: str = Depends(check_api_key)):

    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await executed_state(namespace_name, PydanticObjectId(state_id), body, x_exosphere_request_id, background_tasks)


@router.post(
    "/state/{state_id}/errored",
    response_model=ErroredResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State errored successfully",
    tags=["state"]
)
async def errored_state_route(namespace_name: str, state_id: str, body: ErroredRequestModel, request: Request, api_key: str = Depends(check_api_key)):

    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await errored_state(namespace_name, PydanticObjectId(state_id), body, x_exosphere_request_id)


@router.post(
    "/state/{state_id}/prune",
    response_model=SignalResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State pruned successfully",
    tags=["state"]
)
async def prune_state_route(namespace_name: str, state_id: str, body: PruneRequestModel, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await prune_signal(namespace_name, PydanticObjectId(state_id), body, x_exosphere_request_id)


@router.post(
    "/state/{state_id}/re-enqueue-after",
    response_model=SignalResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State re-enqueued successfully",
    tags=["state"]
)
async def re_enqueue_after_state_route(namespace_name: str, state_id: str, body: ReEnqueueAfterRequestModel, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    
    return await re_queue_after_signal(namespace_name, PydanticObjectId(state_id), body, x_exosphere_request_id)

@router.post(
    "/state/{state_id}/manual-retry",
    response_model=ManualRetryResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="State manual retry successfully",
    tags=["state"]
)
async def manual_retry_state_route(namespace_name: str, state_id: str, body: ManualRetryRequestModel, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))
    
    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    
    return await manual_retry_state(namespace_name, PydanticObjectId(state_id), body, x_exosphere_request_id)


@router.put(
    "/graph/{graph_name}",
    response_model=UpsertGraphTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    response_description="Graph template upserted successfully",
    tags=["graph"]
)   
async def upsert_graph_template(namespace_name: str, graph_name: str, body: UpsertGraphTemplateRequest, request: Request, background_tasks: BackgroundTasks, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await upsert_graph_template_controller(namespace_name, graph_name, body, x_exosphere_request_id, background_tasks)


@router.get(
    "/graph/{graph_name}",
    response_model=UpsertGraphTemplateResponse,
    status_code=status.HTTP_200_OK,
    response_description="Graph template retrieved successfully",
    tags=["graph"]
)
async def get_graph_template(namespace_name: str, graph_name: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await get_graph_template_controller(namespace_name, graph_name, x_exosphere_request_id)


@router.delete(
    "/graph/{graph_name}/triggers",
    response_model=CancelTriggerResponse,
    status_code=status.HTTP_200_OK,
    response_description="Triggers cancelled successfully",
    tags=["graph"]
)
async def cancel_triggers_route(namespace_name: str, graph_name: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await cancel_triggers(namespace_name, graph_name, x_exosphere_request_id)


@router.put(
    "/nodes/",
    response_model=RegisterNodesResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="Nodes registered successfully",
    tags=["nodes"]
)
async def register_nodes_route(namespace_name: str, body: RegisterNodesRequestModel, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await register_nodes(namespace_name, body, x_exosphere_request_id)


@router.get(
    "/state/{state_id}/secrets",
    response_model=SecretsResponseModel,
    status_code=status.HTTP_200_OK,
    response_description="Secrets retrieved successfully",
    tags=["state"]
)
async def get_secrets_route(namespace_name: str, state_id: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info("API key is valid", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error("API key is invalid", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    
    return await get_secrets(namespace_name, state_id, x_exosphere_request_id)


@router.get(
    "/nodes/",
    response_model=ListRegisteredNodesResponse,
    status_code=status.HTTP_200_OK,
    response_description="Registered nodes listed successfully",
    tags=["nodes"]
)
async def list_registered_nodes_route(namespace_name: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    nodes = await list_registered_nodes(namespace_name, x_exosphere_request_id)
    return ListRegisteredNodesResponse(
        namespace=namespace_name,
        count=len(nodes),
        nodes=nodes
    )


@router.get(
    "/graphs/",
    response_model=ListGraphTemplatesResponse,
    status_code=status.HTTP_200_OK,
    response_description="Graph templates listed successfully",
    tags=["graph"]
)
async def list_graph_templates_route(namespace_name: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    templates = await list_graph_templates(namespace_name, x_exosphere_request_id)
    return ListGraphTemplatesResponse(
        namespace=namespace_name,
        count=len(templates),
        templates=templates
    )


@router.get(
    "/runs/{page}/{size}",
    response_model=RunsResponse,
    status_code=status.HTTP_200_OK,
    response_description="Runs listed successfully",
    tags=["runs"]
)
async def get_runs_route(namespace_name: str, page: int, size: int, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    
    return await get_runs(namespace_name, page, size, x_exosphere_request_id)


@router.get(
    "/states/run/{run_id}/graph",
    response_model=GraphStructureResponse,
    status_code=status.HTTP_200_OK,
    response_description="Graph structure for run ID retrieved successfully",
    tags=["runs"]
)
async def get_graph_structure_route(namespace_name: str, run_id: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await get_graph_structure(namespace_name, run_id, x_exosphere_request_id)


@router.get(
    "/graph/{graph_name}/run/{run_id}/node/{node_id}",
    response_model=NodeRunDetailsResponse,
    status_code=status.HTTP_200_OK,
    response_description="Node run details retrieved successfully",
    tags=["runs"]
)
async def get_node_run_details_route(namespace_name: str, graph_name: str, run_id: str, node_id: str, request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info(f"API key is valid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error(f"API key is invalid for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return await get_node_run_details(namespace_name, graph_name, run_id, node_id, x_exosphere_request_id)


# Global endpoints (not namespace-specific)
@global_router.get(
    "/namespaces",
    response_model=ListNamespacesResponse,
    status_code=status.HTTP_200_OK,
    response_description="Namespaces listed successfully",
    tags=["namespaces"]
)
async def list_namespaces_route(request: Request, api_key: str = Depends(check_api_key)):
    x_exosphere_request_id = getattr(request.state, "x_exosphere_request_id", str(uuid4()))

    if api_key:
        logger.info("API key is valid for listing namespaces", x_exosphere_request_id=x_exosphere_request_id)
    else:
        logger.error("API key is invalid for listing namespaces", x_exosphere_request_id=x_exosphere_request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    namespaces = await list_namespaces(x_exosphere_request_id)
    return ListNamespacesResponse(
        namespaces=namespaces,
        count=len(namespaces)
    )