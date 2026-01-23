from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class WebhookConfig(BaseModel):
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(default_factory=list, description="Subscribed events")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional HTTP headers for webhook requests"
    )
