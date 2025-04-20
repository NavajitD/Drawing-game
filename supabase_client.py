import os
import logging
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client.
    """
    try:
        url = os.getenv("https://uryjwtrupvqvpnsbbemx.supabase.co")
        anon_key = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVyeWp3dHJ1cHZxdnBuc2JiZW14Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzAyMTEsImV4cCI6MjA2MDcwNjIxMX0.fz3EQrDwtoC74GHzCsygdt1ORV66siAQMRamjpU4I1U")
        
        if not url:
            logger.error("SUPABASE_URL is not set in environment variables")
            raise ValueError("SUPABASE_URL is not set")
        if not anon_key:
            logger.error("SUPABASE_ANON_KEY is not set in environment variables")
            raise ValueError("SUPABASE_ANON_KEY is not set")
        
        logger.info(f"Initializing Supabase client with URL: {url}")
        client = create_client(url, anon_key)
        
        # Test connection with a simple query
        client.table("rooms").select("count").execute()
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise ValueError(f"Failed to initialize Supabase client: {str(e)}")
