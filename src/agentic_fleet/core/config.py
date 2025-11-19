from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AgenticFleet API"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./agentic_fleet.db"

    # Azure Cosmos DB
    AGENTICFLEET_USE_COSMOS: bool = False
    AZURE_COSMOS_ENDPOINT: str | None = None
    AZURE_COSMOS_KEY: str | None = None
    AZURE_COSMOS_DATABASE: str = "agentic-fleet"
    AZURE_COSMOS_ITEMS_CONTAINER: str = "items"

    # Security
    API_KEY: str = Field(default="dev_key", validation_alias="API_KEY")

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
