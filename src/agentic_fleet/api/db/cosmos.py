import logging

from azure.cosmos.aio import CosmosClient

from agentic_fleet.api.settings import settings

logger = logging.getLogger(__name__)


class CosmosDBConnection:
    def __init__(self):
        self.client = None
        self.database = None

    async def connect(self):
        if not settings.AZURE_COSMOS_ENDPOINT or not settings.AZURE_COSMOS_KEY:
            logger.warning("Cosmos DB credentials missing")
            return

        self.client = CosmosClient(
            settings.AZURE_COSMOS_ENDPOINT, credential=settings.AZURE_COSMOS_KEY
        )
        self.database = self.client.get_database_client(settings.AZURE_COSMOS_DATABASE)

    async def get_container(self, container_name: str):
        if not self.database:
            await self.connect()
        if not self.database:
            raise RuntimeError("Failed to connect to Cosmos DB")
        return self.database.get_container_client(container_name)

    async def close(self):
        if self.client:
            await self.client.close()


cosmos_db = CosmosDBConnection()
