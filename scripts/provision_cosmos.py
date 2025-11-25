#!/usr/bin/env python3
"""
Provision Azure Cosmos DB resources for AgenticFleet.

Creates the database and required containers based on the data model.
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

    # 4. Create Containers
    containers = [
        {
            "id": "Conversations",
            "partition_key": "/conversationId",
        },
        {
            "id": "Workflows",
            "partition_key": "/workflowId",
        },
    ]

    for c_config in containers:
        c_id = cast(str, c_config["id"])
        pk_path = cast(str, c_config["partition_key"])
        print(f"Creating container '{c_id}' with PK '{pk_path}'...")

        try:
            # Note: For Serverless accounts, offer_throughput must NOT be set.
            # For Provisioned accounts, omitting it uses the default or database throughput.
            db.create_container_if_not_exists(
                id=c_id,
                partition_key=PartitionKey(path=pk_path),
            )
            print(f"Container '{c_id}' ready.")
        except exceptions.CosmosHttpResponseError as e:
            print(f"Failed to create container '{c_id}': {e}")

    print("\nProvisioning complete!")
    print(f"Database: {database_id}")
    print("Containers: Conversations, Workflows")


if __name__ == "__main__":
    provision_cosmos()
