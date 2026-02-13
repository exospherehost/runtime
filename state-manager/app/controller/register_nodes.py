from ..models.register_nodes_request import RegisterNodesRequestModel
from ..models.register_nodes_response import RegisterNodesResponseModel, RegisteredNodeModel
from ..models.db.registered_node import RegisteredNode

from app.singletons.logs_manager import LogsManager
from beanie.operators import Set

logger = LogsManager().get_logger()


async def register_nodes(namespace_name: str, body: RegisterNodesRequestModel, x_exosphere_request_id: str) -> RegisterNodesResponseModel:
    
    try:
        logger.info(f"Registering nodes for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)

        # Check if nodes already exist and update them, or create new ones
        registered_nodes = []
        
        for node_data in body.nodes:
            # Check if node already exists
            existing_node = await RegisteredNode.find_one(
                RegisteredNode.name == node_data.name,
                RegisteredNode.namespace == namespace_name
            )
            
            if existing_node:
                # Update existing node
                await existing_node.update(
                    Set({
                        RegisteredNode.runtime_name: body.runtime_name,
                        RegisteredNode.runtime_namespace: namespace_name,
                        RegisteredNode.inputs_schema: node_data.inputs_schema, # type: ignore
                        RegisteredNode.outputs_schema: node_data.outputs_schema, # type: ignore
                        RegisteredNode.secrets: node_data.secrets, # type: ignore
                        RegisteredNode.timeout_minutes: node_data.timeout_minutes # type: ignore
                }))
                logger.info(f"Updated existing node {node_data.name} in namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
                
            else:
                # Create new node
                new_node = RegisteredNode(
                    name=node_data.name,
                    namespace=namespace_name,
                    runtime_name=body.runtime_name,
                    runtime_namespace=namespace_name,
                    inputs_schema=node_data.inputs_schema,
                    outputs_schema=node_data.outputs_schema,
                    secrets=node_data.secrets,
                    timeout_minutes=node_data.timeout_minutes
                )
                await new_node.insert()
                logger.info(f"Created new node {node_data.name} in namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
            
            registered_nodes.append(
                RegisteredNodeModel(
                    name=node_data.name,
                    inputs_schema=node_data.inputs_schema,
                    outputs_schema=node_data.outputs_schema,
                    secrets=node_data.secrets,
                    timeout_minutes=node_data.timeout_minutes
                )
            )

        response = RegisterNodesResponseModel(
            runtime_name=body.runtime_name,
            registered_nodes=registered_nodes
        )
        
        logger.info(f"Successfully registered {len(registered_nodes)} nodes for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id)
        return response
    
    except Exception as e:
        logger.error(f"Error registering nodes for namespace {namespace_name}", x_exosphere_request_id=x_exosphere_request_id, error=e)
        raise e 