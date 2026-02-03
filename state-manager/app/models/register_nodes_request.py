from pydantic import BaseModel, Field
from typing import Any, List, Optional


class NodeRegistrationModel(BaseModel):
    name: str = Field(..., description="Unique name of the node")
    inputs_schema: dict[str, Any] = Field(..., description="JSON schema for node inputs")
    outputs_schema: dict[str, Any] = Field(..., description="JSON schema for node outputs")
    secrets: List[str] = Field(..., description="List of secrets that the node uses")
    timeout_minutes: Optional[int] = Field(None, gt=0, description="Timeout in minutes for this node. Falls back to global setting if not provided")


class RegisterNodesRequestModel(BaseModel):
    runtime_name: str = Field(..., description="Name of the runtime registering the nodes")
    nodes: List[NodeRegistrationModel] = Field(..., description="List of nodes to register")