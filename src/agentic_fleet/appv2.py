import os

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data.storage_clients import (
    SupabaseStorageClient,  # Import Supabase storage client
)
from dotenv import load_dotenv
from sqlalchemy.supabase_client import get_supabase_client  # Adjusted import path

# Load environment variables from .env file
load_dotenv()

# Initialize the Supabase storage client
storage_client = SupabaseStorageClient(bucket_name="chainlit")  # Replace with your actual bucket name

@cl.data_layer
def get_data_layer():
    # Get the Supabase client
    supabase = get_supabase_client()

    # Configure the SQLAlchemy Data Layer
    return SQLAlchemyDataLayer(
        conninfo=f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
        storage_provider=storage_client  # Use Supabase storage client
    )
