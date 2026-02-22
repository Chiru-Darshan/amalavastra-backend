"""
Database Module
Handles Supabase client initialization and connection management
"""
from supabase import create_client, Client
from functools import lru_cache
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", SUPABASE_KEY)


def validate_config():
    """Validate required configuration"""
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL environment variable is required")
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable is required")


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get a cached Supabase client instance.
    Uses LRU cache to maintain a single connection.
    """
    validate_config()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@lru_cache()
def get_supabase_admin_client() -> Client:
    """
    Get a cached Supabase admin client instance.
    Uses service key for elevated permissions.
    """
    validate_config()
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# Default client instance for regular operations
supabase: Client = get_supabase_client()

# Admin client for user management (when needed)
supabase_admin: Client = get_supabase_admin_client()

