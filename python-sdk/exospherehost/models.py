from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional, List
from enum import Enum
from zoneinfo import available_timezones

_AVAILABLE_TIMEZONES = available_timezones()

class UnitesStrategyEnum(str, Enum):
    ALL_SUCCESS = "ALL_SUCCESS"
    ALL_DONE = "ALL_DONE"


class UnitesModel(BaseModel):
    identifier: str = Field(..., description="Identifier of the node")
    strategy: UnitesStrategyEnum = Field(default=UnitesStrategyEnum.ALL_SUCCESS, description="Strategy of the unites")


class GraphNodeModel(BaseModel):
    node_name: str = Field(..., description="Name of the node")
    namespace: str = Field(..., description="Namespace of the node")
    identifier: str = Field(..., description="Identifier of the node")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Inputs of the node")
    next_nodes: Optional[List[str]] = Field(default=None, description="Next nodes to execute")
    unites: Optional[UnitesModel] = Field(default=None, description="Unites of the node")

    @field_validator('node_name')
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        trimmed_v = v.strip()
        if trimmed_v == "" or trimmed_v is None:
            raise ValueError("Node name cannot be empty")
        return trimmed_v
    
    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        trimmed_v = v.strip()
        if trimmed_v == "" or trimmed_v is None:
            raise ValueError("Node identifier cannot be empty")
        elif trimmed_v == "store":
            raise ValueError("Node identifier cannot be reserved word 'store'")
        return trimmed_v
    
    @field_validator('next_nodes')
    @classmethod
    def validate_next_nodes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        identifiers = set()
        errors = []
        trimmed_v = []

        if v is not None:
            for next_node_identifier in v:
                trimmed_next_node_identifier = next_node_identifier.strip()
                
                if trimmed_next_node_identifier == "" or trimmed_next_node_identifier is None:
                    errors.append("Next node identifier cannot be empty")
                    continue

                if trimmed_next_node_identifier in identifiers:
                    errors.append(f"Next node identifier {trimmed_next_node_identifier} is not unique")
                    continue

                identifiers.add(trimmed_next_node_identifier)
                trimmed_v.append(trimmed_next_node_identifier)
        if errors:
            raise ValueError("\n".join(errors))
        return trimmed_v
    
    @field_validator('unites')
    @classmethod
    def validate_unites(cls, v: Optional[UnitesModel]) -> Optional[UnitesModel]:
        trimmed_v = v
        if v is not None:
            trimmed_v = UnitesModel(identifier=v.identifier.strip(), strategy=v.strategy)
            if trimmed_v.identifier == "" or trimmed_v.identifier is None:
                raise ValueError("Unites identifier cannot be empty")
        return trimmed_v


class RetryStrategyEnum(str, Enum):
    EXPONENTIAL = "EXPONENTIAL"
    EXPONENTIAL_FULL_JITTER = "EXPONENTIAL_FULL_JITTER"
    EXPONENTIAL_EQUAL_JITTER = "EXPONENTIAL_EQUAL_JITTER"

    LINEAR = "LINEAR"
    LINEAR_FULL_JITTER = "LINEAR_FULL_JITTER"
    LINEAR_EQUAL_JITTER = "LINEAR_EQUAL_JITTER"

    FIXED = "FIXED"
    FIXED_FULL_JITTER = "FIXED_FULL_JITTER"
    FIXED_EQUAL_JITTER = "FIXED_EQUAL_JITTER"


class RetryPolicyModel(BaseModel):
    max_retries: int = Field(default=3, description="The maximum number of retries", ge=0)
    strategy: RetryStrategyEnum = Field(default=RetryStrategyEnum.EXPONENTIAL, description="The method of retry")
    backoff_factor: int = Field(default=2000, description="The backoff factor in milliseconds (default: 2000 = 2 seconds)", gt=0)
    exponent: int = Field(default=2, description="The exponent for the exponential retry strategy", gt=0)
    max_delay: int | None = Field(default=None, description="The maximum delay in milliseconds (no default limit when None)", gt=0)


class StoreConfigModel(BaseModel):
    required_keys: list[str] = Field(default_factory=list, description="Required keys of the store")
    default_values: dict[str, str] = Field(default_factory=dict, description="Default values of the store")

    @field_validator("required_keys")
    @classmethod
    def validate_required_keys(cls, v: list[str]) -> list[str]:
        errors = []
        keys = set()
        trimmed_keys = []
        
        for key in v:
            trimmed_key = key.strip() if key is not None else ""
            
            if trimmed_key == "":
                errors.append("Key cannot be empty or contain only whitespace")
                continue
                
            if '.' in trimmed_key:
                errors.append(f"Key '{trimmed_key}' cannot contain '.' character")
                continue
                
            if trimmed_key in keys:
                errors.append(f"Key '{trimmed_key}' is duplicated")
                continue
                
            keys.add(trimmed_key)
            trimmed_keys.append(trimmed_key)
        
        if len(errors) > 0:
            raise ValueError("\n".join(errors))
        return trimmed_keys

    @field_validator("default_values")
    @classmethod
    def validate_default_values(cls, v: dict[str, str]) -> dict[str, str]:
        errors = []
        keys = set()
        normalized_dict = {}
        
        for key, value in v.items():
            trimmed_key = key.strip() if key is not None else ""
            
            if trimmed_key == "":
                errors.append("Key cannot be empty or contain only whitespace")
                continue
                
            if '.' in trimmed_key:
                errors.append(f"Key '{trimmed_key}' cannot contain '.' character")
                continue
                
            if trimmed_key in keys:
                errors.append(f"Key '{trimmed_key}' is duplicated")
                continue
                
            keys.add(trimmed_key)
            normalized_dict[trimmed_key] = str(value)
        
        if len(errors) > 0:
            raise ValueError("\n".join(errors))
        return normalized_dict
    
class CronTrigger(BaseModel):
    expression: str = Field(..., description="Cron expression for scheduling automatic graph execution. Uses standard 5-field format: minute hour day-of-month month day-of-week. Example: '0 9 * * 1-5' for weekdays at 9 AM.")
    timezone: str = Field(default="UTC", description="Timezone for the cron expression (e.g., 'America/New_York', 'Europe/London', 'UTC'). Defaults to 'UTC'.")

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in _AVAILABLE_TIMEZONES:
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone (e.g., 'America/New_York', 'Europe/London', 'UTC')")
        return v