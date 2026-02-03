from pydantic import Field
from beanie import Document
from typing import Optional

from pymongo import IndexModel
from ..trigger_models import TriggerTypeEnum, TriggerStatusEnum
from datetime import datetime

class DatabaseTriggers(Document):
    type: TriggerTypeEnum = Field(..., description="Type of the trigger")
    expression: Optional[str] = Field(default=None, description="Expression of the trigger")
    timezone: Optional[str] = Field(default="UTC", description="Timezone for the trigger")
    graph_name: str = Field(..., description="Name of the graph")
    namespace: str = Field(..., description="Namespace of the graph")
    trigger_time: datetime = Field(..., description="Trigger time of the trigger")
    trigger_status: TriggerStatusEnum = Field(..., description="Status of the trigger")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time for automatic cleanup of completed triggers")

    class Settings:
        indexes = [
            IndexModel(
                [
                    ("trigger_time", -1),
                ],
                name="idx_trigger_time"
            ),
            IndexModel(
                [
                    ("type", 1),
                    ("expression", 1),
                    ("graph_name", 1),
                    ("namespace", 1),
                    ("trigger_time", 1),
                ],
                name="uniq_graph_type_expr_time",
                unique=True
            ),
            IndexModel(
                [
                    ("expires_at", 1),
                ],
                name="ttl_expires_at",
                expireAfterSeconds=0,  # Delete immediately when expires_at is reached
                partialFilterExpression={
                    "trigger_status": {
                        "$in": [
                            TriggerStatusEnum.TRIGGERED,
                            TriggerStatusEnum.FAILED
                        ]
                    }
                }
            )
        ]
