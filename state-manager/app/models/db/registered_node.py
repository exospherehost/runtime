from .base import BaseDatabaseModel
from pydantic import Field
from typing import Any, Optional
from pymongo import IndexModel
from ..node_template_model import NodeTemplate


class RegisteredNode(BaseDatabaseModel):
    name: str = Field(..., description="Unique name of the registered node")
    namespace: str = Field(..., description="Namespace of the registered node")
    runtime_name: str = Field(..., description="Name of the runtime that registered this node")
    runtime_namespace: str = Field(..., description="Namespace of the runtime that registered this node")
    inputs_schema: dict[str, Any] = Field(..., description="JSON schema for node inputs")
    outputs_schema: dict[str, Any] = Field(..., description="JSON schema for node outputs") 
    secrets: list[str] = Field(default_factory=list, description="List of secrets that the node uses")
    timeout_minutes: Optional[int] = Field(None, gt=0, description="Timeout in minutes for this node. Falls back to global setting if not provided")

    class Settings:
        indexes = [
            IndexModel(
                keys=[("name", 1), ("namespace", 1)],
                unique=True,
                name="unique_name_namespace"
            ),
        ]

    @staticmethod
    async def get_by_name_and_namespace(name: str, namespace: str) -> "RegisteredNode | None":
        return await RegisteredNode.find_one(
            RegisteredNode.name == name,
            RegisteredNode.namespace == namespace
        )
    
    @staticmethod
    async def list_nodes_by_templates(templates: list[NodeTemplate]) -> list["RegisteredNode"]:
        if len(templates) == 0:
            return []
        
        query = {
            "$or": [
                {"name": node.node_name, "namespace": node.namespace}
                for node in templates
            ]
        }
        return await RegisteredNode.find(query).to_list()