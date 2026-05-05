from pydantic import BaseModel, Field
from typing import Any, List, Optional


class RegisteredNodeModel(BaseModel):
    name: str = Field(..., description="Name of the registered node")
    inputs_schema: dict[str, Any] = Field(..., description="Inputs for the registered node")
    outputs_schema: dict[str, Any] = Field(..., description="Outputs for the registered node")
    secrets: List[str] = Field(..., description="List of secrets that the node uses")
    timeout_minutes: Optional[int] = Field(None, gt=0, description="Timeout in minutes for this node. Falls back to global setting if not provided")


class RegisterNodesResponseModel(BaseModel):
    runtime_name: str = Field(..., description="Name of the runtime that registered the nodes")
    registered_nodes: List[RegisteredNodeModel] = Field(..., description="List of successfully registered nodes")