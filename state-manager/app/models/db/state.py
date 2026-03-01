from pymongo import IndexModel
from .base import BaseDatabaseModel
from ..state_status_enum import StateStatusEnum
from pydantic import Field
from beanie import Insert, PydanticObjectId, Replace, Save, before_event
from pymongo.results import InsertManyResult
from typing import Any, Optional
import hashlib
import json
import time
import uuid

class State(BaseDatabaseModel):
    node_name: str = Field(..., description="Name of the node of the state")
    namespace_name: str = Field(..., description="Name of the namespace of the state")
    identifier: str = Field(..., description="Identifier of the node for which state is created")
    graph_name: str = Field(..., description="Name of the graph template for this state")
    run_id: str = Field(..., description="Unique run ID for grouping states from the same graph execution")
    status: StateStatusEnum = Field(..., description="Status of the state")
    inputs: dict[str, Any] = Field(..., description="Inputs of the state")
    outputs: dict[str, Any] = Field(..., description="Outputs of the state")
    data: dict[str, Any] = Field(default_factory=dict, description="Data of the state (could be used to save pruned meta data)")
    error: Optional[str] = Field(None, description="Error message")
    parents: dict[str, PydanticObjectId] = Field(default_factory=dict, description="Parents of the state")
    does_unites: bool = Field(default=False, description="Whether this state unites other states")
    state_fingerprint: str = Field(default="", description="Fingerprint of the state")
    enqueue_after: int = Field(default_factory=lambda: int(time.time() * 1000), gt=0, description="Unix time in milliseconds after which the state should be enqueued")
    retry_count: int = Field(default=0, description="Number of times the state has been retried")
    fanout_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Fanout ID of the state")
    manual_retry_fanout_id: str = Field(default="", description="Fanout ID from a manual retry request, ensuring unique retries for unite nodes.")
    queued_at: Optional[int] = Field(default=None, description="Unix time in milliseconds when state was queued")
    timeout_at: Optional[int] = Field(default=None, description="Unix time in milliseconds when state times out")
    timeout_minutes: Optional[int] = Field(default=None, gt=0, description="Timeout in minutes for this specific state, taken from node registration")

    @before_event([Insert, Replace, Save])
    def _generate_fingerprint(self):
        if not self.does_unites:
            self.state_fingerprint = ""
            return
        
        data = {
            "node_name": self.node_name,
            "namespace_name": self.namespace_name,
            "identifier": self.identifier,
            "graph_name": self.graph_name,
            "run_id": self.run_id,
            "retry_count": self.retry_count,
            "parents": {k: str(v) for k, v in self.parents.items()},
            "manual_retry_fanout_id": self.manual_retry_fanout_id,
        }
        payload = json.dumps(
            data,
            sort_keys=True,            # canonical key ordering at all levels
            separators=(",", ":"),     # no whitespace variance
            ensure_ascii=True,         # normalized non-ASCII escapes
        ).encode("utf-8")
        self.state_fingerprint = hashlib.sha256(payload).hexdigest()    
    
    @classmethod
    async def insert_many(cls, documents: list["State"]) -> InsertManyResult:
        """Override insert_many to ensure fingerprints are generated before insertion."""
        # Generate fingerprints for states that need them
        for state in documents:
            state._generate_fingerprint()
        
        return await super().insert_many(documents) # type: ignore
        
    class Settings:
        indexes = [
            IndexModel(
                [
                    ("state_fingerprint", 1)
                ],
                unique=True,
                name="uniq_state_fingerprint_unites",
                partialFilterExpression={
                    "does_unites": True
                }
            ),
            IndexModel(
                [
                    ("enqueue_after", 1),
                    ("status", 1),
                    ("namespace_name", 1),
                    ("node_name", 1),
                ],
                name="enqueue_query"
            ),
            IndexModel(
                [
                    ("node_name", 1),
                    ("namespace_name", 1),
                    ("graph_name", 1),
                    ("identifier", 1),
                    ("run_id", 1),
                    ("retry_count", 1),
                    ("fanout_id", 1),
                ],
                unique=True,
                name="uniq_fanout_retry"
            ),
            IndexModel(
                [
                    ("run_id", 1),
                    ("status", 1),
                ],
                name="run_id_status_index"
            ),
            IndexModel(
                [
                    ("status", 1),
                    ("timeout_at", 1),
                ],
                name="timeout_query_index"
            )
        ]