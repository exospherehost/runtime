from pydantic import BaseModel, Field


class CancelTriggerResponse(BaseModel):
    namespace: str = Field(..., description="Namespace of the cancelled triggers")
    graph_name: str = Field(..., description="Name of the graph")
    cancelled_count: int = Field(..., description="Number of triggers that were cancelled")
    message: str = Field(..., description="Human-readable message describing the result")

