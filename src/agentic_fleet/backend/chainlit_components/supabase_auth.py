"""Supabase authentication handler for Chainlit."""

import os
from typing import Dict, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from .user import User

load_dotenv()

class SupabaseAuth:
    """Supabase authentication handler."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
            )

        self.client: Client = create_client(supabase_url, supabase_key)

    async def handle_callback(
        self,
        token: str,
        raw_user_data: Dict[str, str],
        default_user: User,
    ) -> User:
        """Handle Supabase authentication callback.

        Args:
            token: Authentication token
            raw_user_data: Raw user data from Supabase
            default_user: Default user object

        Returns:
            Updated user object
        """
        try:
            # Extract user information from Supabase data
            user_id = str(raw_user_data.get("id", ""))
            email = raw_user_data.get("email", "")
            name = raw_user_data.get("user_metadata", {}).get("full_name", "")
            provider = raw_user_data.get("app_metadata", {}).get("provider", "")

            # Create user object with Supabase data
            return User(
                identifier=user_id,
                display_name=name or email,
                metadata={
                    "email": email,
                    "provider": provider,
                    "name": name,
                },
            )

        except Exception as e:
            print(f"Error in Supabase callback: {str(e)}")
            return default_user

    def get_user_session(self) -> Optional[Dict]:
        """Get current user session from Supabase.

        Returns:
            User session data if authenticated, None otherwise
        """
        try:
            return self.client.auth.get_session()
        except Exception:
            return None
