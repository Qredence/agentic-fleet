#!/usr/bin/env python3
"""
Provision Azure Cosmos DB resources for AgenticFleet.

Creates the database and required containers based on the data model
defined in docs/developers/cosmosdb_data_model.md.

Usage:
    # With key-based auth
    export AZURE_COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
    export AZURE_COSMOS_KEY="<your-key>"
    python scripts/provision_cosmos.py

    # With Managed Identity (no key needed)
    export AZURE_COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
    python scripts/provision_cosmos.py
"""

import os
import sys
from typing import cast

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential


def provision_cosmos() -> None:
    """Provision Cosmos DB resources."""
    # 1. Configuration
    endpoint = os.environ.get("AZURE_COSMOS_ENDPOINT")
    key = os.environ.get("AZURE_COSMOS_KEY")
    database_id = os.environ.get("AZURE_COSMOS_DATABASE", "agentic-fleet")

    if not endpoint:
        print("Error: AZURE_COSMOS_ENDPOINT environment variable is not set.")
        print(
            "Please set it to your Cosmos DB account endpoint (e.g., https://<account>.documents.azure.com:443/)"
        )
        sys.exit(1)

    # 2. Connect
    print(f"Connecting to Cosmos DB at {endpoint}...")
    try:
        if key:
            client = CosmosClient(cast(str, endpoint), credential=key)
        else:
            print("No AZURE_COSMOS_KEY found, attempting Managed Identity...")
            credential = DefaultAzureCredential()
            client = CosmosClient(cast(str, endpoint), credential=credential)
    except Exception as e:
        print(f"Failed to create CosmosClient: {e}")
        sys.exit(1)

    # 3. Create Database
    print(f"Creating database '{database_id}' if not exists...")
    try:
        db = client.create_database_if_not_exists(id=database_id)
        print(f"Database '{database_id}' ready.")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to create database: {e}")
        sys.exit(1)

    # 4. Create Containers (matches cosmosdb_data_model.md)
    # See docs/developers/cosmosdb_data_model.md for full schema details
    containers = [
        {
            "id": "workflowRuns",
            "partition_key": "/workflowId",
            "description": "End-to-end workflow runs with embedded events and quality data",
        },
        {
            "id": "conversations",
            "partition_key": "/conversationId",
            "description": "Multi-turn chat sessions with embedded messages for context",
        },
        {
            "id": "agentMemory",
            "partition_key": "/userId",
            "description": "Long-term per-user/agent memory items (vector-friendly)",
        },
        {
            "id": "dspyExamples",
            "partition_key": "/userId",
            "description": "DSPy supervisor training/eval examples",
        },
        {
            "id": "dspyOptimizationRuns",
            "partition_key": "/userId",
            "description": "DSPy optimization/compilation sessions",
        },
        {
            "id": "cache",
            "partition_key": "/cacheKey",
            "description": "Cached workflow/query results with TTL",
            # TTL should be enabled manually in portal or via indexing policy
        },
    ]

    created = []
    for c_config in containers:
        c_id = cast(str, c_config["id"])
        pk_path = cast(str, c_config["partition_key"])
        desc = c_config.get("description", "")
        print(f"Creating container '{c_id}' with PK '{pk_path}'...")
        if desc:
            print(f"  Purpose: {desc}")

        try:
            # Note: For Serverless accounts, offer_throughput must NOT be set.
            # For Provisioned accounts, omitting it uses the default or database throughput.
            db.create_container_if_not_exists(
                id=c_id,
                partition_key=PartitionKey(path=pk_path),
            )
            print(f"  ✓ Container '{c_id}' ready.")
            created.append(c_id)
        except exceptions.CosmosHttpResponseError as e:
            print(f"  ✗ Failed to create container '{c_id}': {e}")

    print("\n" + "=" * 50)
    print("Provisioning complete!")
    print(f"Database: {database_id}")
    print(f"Containers created: {', '.join(created)}")
    print("\nNext steps:")
    print("1. Enable TTL on 'cache' container if needed (portal or CLI)")
    print("2. Configure vector index on 'agentMemory' for semantic search")
    print("3. Set environment variables in your app:")
    print("   AGENTICFLEET_USE_COSMOS=true")
    print(f"   AZURE_COSMOS_ENDPOINT={endpoint}")
    print(f"   AZURE_COSMOS_DATABASE={database_id}")


if __name__ == "__main__":
    provision_cosmos()
