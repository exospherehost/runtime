from pydantic import BaseModel, Field, field_validator
from enum import Enum
from croniter import croniter
from typing import Union, Annotated, Literal
from zoneinfo import available_timezones

# Cache available timezones at module level to avoid repeated filesystem queries
_AVAILABLE_TIMEZONES = available_timezones()

class TriggerTypeEnum(str, Enum):
    CRON = "CRON"

class TriggerStatusEnum(str, Enum):
    PENDING = "PENDING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TRIGGERED = "TRIGGERED"
    TRIGGERING = "TRIGGERING"

class CronTrigger(BaseModel):
    type: Literal[TriggerTypeEnum.CRON] = Field(default=TriggerTypeEnum.CRON, description="Type of the trigger")
    expression: str = Field(..., description="Cron expression for the trigger")
    timezone: str = Field(default="UTC", description="Timezone for the cron expression (e.g., 'America/New_York', 'Europe/London', 'UTC')")

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError("Invalid cron expression")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in _AVAILABLE_TIMEZONES:
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone (e.g., 'America/New_York', 'Europe/London', 'UTC')")
        return v

# Union type for all trigger types - add new trigger types here
TriggerValue = Annotated[Union[CronTrigger], Field(discriminator="type")] # type: ignore

class Trigger(BaseModel):
    """
    Extensible trigger model using discriminated unions.
    To add a new trigger type:
    1. Add the enum value to TriggerTypeEnum
    2. Create a new trigger class (e.g., WebhookTrigger) with type field
    3. Add it to the TriggerValue Union

    Note: Access trigger type via trigger.value.type
    """
    value: TriggerValue = Field(..., description="Value of the trigger")