import os
import logging
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_supabase_client(url: str, anon_key: str) -> Client:
    """
    Initialize and return a Supabase client with provided credentials.
    """
    try:
        logger.info(f"SUPABASE_URL: {url}")
        logger.info(f"SUPABASE_ANON_KEY: {anon_key[:10]}...")
        
        if not url:
            logger.error("SUPABASE_URL is empty")
            raise ValueError("SUPABASE_URL is empty")
        if not anon_key:
            logger.error("SUPABASE_ANON_KEY is empty")
            raise ValueError("SUPABASE_ANON_KEY is empty")
        
        logger.info(f"Initializing Supabase client with URL: {url}")
        client = create_client(url, anon_key)
        
        # Test connection
        response = client.table("rooms").select("count").execute()
        logger.info(f"Connection test response: {response}")
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise ValueError(f"Failed to initialize Supabase client: {str(e)}")
