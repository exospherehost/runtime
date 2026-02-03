import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # MongoDB Configuration
    mongo_uri: str = Field(..., description="MongoDB connection URI" )
    mongo_database_name: str = Field(default="exosphere-state-manager", description="MongoDB database name")
    state_manager_secret: str = Field(..., description="Secret key for API authentication")
    secrets_encryption_key: str = Field(..., description="Key for encrypting secrets")
    trigger_workers: int = Field(default=1, description="Number of workers to run the trigger cron")
    node_timeout_minutes: int = Field(default=60, gt=0, description="Timeout in minutes for nodes stuck in QUEUED status")
    trigger_retention_hours: int = Field(default=720, description="Number of hours to retain completed/failed triggers before cleanup")
    
    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mongo_uri=os.getenv("MONGO_URI"), # type: ignore
            mongo_database_name=os.getenv("MONGO_DATABASE_NAME", "exosphere-state-manager"), # type: ignore
            state_manager_secret=os.getenv("STATE_MANAGER_SECRET"), # type: ignore
            secrets_encryption_key=os.getenv("SECRETS_ENCRYPTION_KEY"), # type: ignore
            node_timeout_minutes=int(os.getenv("NODE_TIMEOUT_MINUTES", 60)), # type: ignore
            trigger_workers=int(os.getenv("TRIGGER_WORKERS", 1)), # type: ignore
            trigger_retention_hours=int(os.getenv("TRIGGER_RETENTION_HOURS", 720)) # type: ignore
        )


# Global settings instance - will be updated when get_settings() is called
_settings = None


def get_settings() -> Settings:
    """Get the global settings instance, reloading from environment if needed."""
    global _settings
    _settings = Settings.from_env()
    return _settings


# Initialize settings
settings = get_settings() 