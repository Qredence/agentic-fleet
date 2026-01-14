"""ChromaDB driver for semantic memory storage."""

import logging
import os

import chromadb
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ChromaDriver:
    """Driver for managing ChromaDB semantic memory collections."""

    def __init__(self, config_path=".fleet/context/.chroma/config.yaml"):
        self.config = self._load_config(config_path)
        self.client = self._connect_to_cloud()
        self.collections = {}
        self._initialize_collections()
        self.config = self._load_config(config_path)
        self.client = self._connect_to_cloud()
        self.collections = {}
        self._initialize_collections()

    def _load_config(self, path):
        """Load configuration from YAML file."""
        if not os.path.exists(path):
            # Fallback for when config doesn't exist yet (e.g. during init)
            logger.warning(
                f"Config file not found at {path}. using environment variables or defaults."
            )
            return {}

        with open(path) as f:
            return yaml.safe_load(f)

    def _connect_to_cloud(self):
        """Connect to Chroma Cloud using config.yaml values."""
        cloud_config = self.config.get("cloud", {})

        api_key = cloud_config.get("api_key")
        tenant = cloud_config.get("tenant")
        database = cloud_config.get("database")

        if not api_key:
            logger.warning(
                "No Chroma API key found in config.yaml. Operating in offline/local-only mode."
            )
            return None

        try:
            client = chromadb.CloudClient(tenant=tenant, database=database, api_key=api_key)
            logger.info(f"Connected to Chroma Cloud (Tenant: {tenant}, DB: {database})")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Chroma Cloud: {e}")
            return None

    def _initialize_collections(self):
        """Initialize the three standard collections."""
        if not self.client:
            return

        collection_names = self.config.get(
            "collections",
            {
                "semantic": "agentic-fleet-semantic",
                "procedural": "agentic-fleet-procedural",
                "episodic": "agentic-fleet-episodic",
            },
        )

        for key, name in collection_names.items():
            try:
                self.collections[key] = self.client.get_or_create_collection(name=name)
                logger.info(f"Initialized collection: {name} ({key})")
            except Exception as e:
                logger.error(f"Error initializing collection {name}: {e}")

    def add_memory(self, collection_type, documents, metadatas, ids):
        """Add items to a specific collection."""
        if not self.client:
            logger.warning("Chroma client not initialized. Skipping add_memory.")
            return

        if collection_type not in self.collections:
            logger.error(f"Unknown collection type: {collection_type}")
            return

        try:
            collection = self.collections[collection_type]
            collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Upserted {len(ids)} items into {collection_type} collection.")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")

    def query_memory(self, collection_type, query_texts, n_results=5):
        """Query a specific collection."""
        if not self.client:
            logger.warning("Chroma client not initialized. Skipping query.")
            return []

        if collection_type not in self.collections:
            logger.error(f"Unknown collection type: {collection_type}")
            return []

        try:
            collection = self.collections[collection_type]
            results = collection.query(query_texts=query_texts, n_results=n_results)
            return results
        except Exception as e:
            logger.error(f"Failed to query memory: {e}")
            return []

    def query_all(self, query_texts, n_results=3):
        """Query all collections and aggregate results."""
        if not self.client:
            return {}

        results = {}
        for key in self.collections:
            results[key] = self.query_memory(key, query_texts, n_results)
        return results
