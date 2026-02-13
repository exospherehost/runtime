from fastapi import HTTPException

from app.singletons.logs_manager import LogsManager
from app.models.trigger_graph_model import TriggerGraphRequestModel, TriggerGraphResponseModel
from app.models.state_status_enum import StateStatusEnum
from app.models.db.state import State
from app.models.db.store import Store
from app.models.db.run import Run
from app.models.db.graph_template_model import GraphTemplate
from app.models.db.registered_node import RegisteredNode
from app.models.node_template_model import NodeTemplate
from app.models.dependent_string import DependentString
from app.config.settings import get_settings

import uuid
import time

logger = LogsManager().get_logger()

def check_required_store_keys(graph_template: GraphTemplate, store: dict[str, str]) -> None:
    required_keys = set(graph_template.store_config.required_keys)
    provided_keys = set(store.keys())

    missing_keys = required_keys - provided_keys
    if missing_keys:
        raise HTTPException(status_code=400, detail=f"Missing store keys: {missing_keys}")
    

def construct_inputs(node: NodeTemplate, inputs: dict[str, str]) -> dict[str, str]:
    return {key: inputs.get(key, value) for key, value in node.inputs.items()}
    

async def trigger_graph(namespace_name: str, graph_name: str, body: TriggerGraphRequestModel, x_exosphere_request_id: str) -> TriggerGraphResponseModel:
    try:
        run_id = str(uuid.uuid4())
        logger.info(f"Triggering graph {graph_name} with run_id {run_id}", x_exosphere_request_id=x_exosphere_request_id)

        try:
            graph_template = await GraphTemplate.get(namespace_name, graph_name)
        except ValueError as e:
            logger.error(f"Graph template not found for namespace {namespace_name} and graph {graph_name}", x_exosphere_request_id=x_exosphere_request_id)
            if "Graph template not found" in str(e):
                raise HTTPException(status_code=404, detail=f"Graph template not found for namespace {namespace_name} and graph {graph_name}")
            else:
                raise e
            
        if not graph_template.is_valid():
            raise HTTPException(status_code=400, detail="Graph template is not valid")
        
        root = graph_template.get_root_node()
        inputs = construct_inputs(root, body.inputs)

        try:
            for field, value in inputs.items():
                dependent_string = DependentString.create_dependent_string(value)

                for dependent in dependent_string.dependents.values():
                    if dependent.identifier != "store":
                        raise HTTPException(status_code=400, detail=f"Root node can have only store identifier as dependent but got {dependent.identifier}")
                    elif dependent.field not in body.store:
                        if dependent.field in graph_template.store_config.default_values.keys():
                            dependent_string.set_value(dependent.identifier, dependent.field, graph_template.store_config.default_values[dependent.field])
                        else:
                            raise HTTPException(status_code=400, detail=f"Dependent {dependent.field} not found in store for root node {root.identifier}")
                    else:
                        dependent_string.set_value(dependent.identifier, dependent.field, body.store[dependent.field])

                inputs[field] = dependent_string.generate_string()

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {e}")


        check_required_store_keys(graph_template, body.store)

        new_run = Run(
            run_id=run_id,
            namespace_name=namespace_name,
            graph_name=graph_name
        )
        await new_run.insert()

        new_stores = [
            Store(
                run_id=run_id,
                namespace=namespace_name,
                graph_name=graph_name,
                key=key,
                value=value
            ) for key, value in body.store.items()
        ]

        if len(new_stores) > 0:
            await Store.insert_many(new_stores)
        
        # Get node timeout setting
        registered_node = await RegisteredNode.get_by_name_and_namespace(root.node_name, root.namespace)
        timeout_minutes = None
        if registered_node and registered_node.timeout_minutes:
            timeout_minutes = registered_node.timeout_minutes
        else:
            # Fall back to global setting
            settings = get_settings()
            timeout_minutes = settings.node_timeout_minutes
        
        new_state = State(
            node_name=root.node_name,
            namespace_name=namespace_name,
            identifier=root.identifier,
            graph_name=graph_name,
            run_id=run_id,
            status=StateStatusEnum.CREATED,
            enqueue_after=int(time.time() * 1000) + body.start_delay,
            inputs=inputs,
            outputs={},
            error=None,
            timeout_minutes=timeout_minutes
        )
        await new_state.insert()

        return TriggerGraphResponseModel(
            status=StateStatusEnum.CREATED,
            run_id=run_id
        )

    except Exception as e:
        logger.error(f"Error triggering graph {graph_name} for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        raise e
