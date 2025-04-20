import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client.
    """
    try:
        url = os.getenv("https://uryjwtrupvqvpnsbbemx.supabase.co")
        anon_key = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVyeWp3dHJ1cHZxdnBuc2JiZW14Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzAyMTEsImV4cCI6MjA2MDcwNjIxMX0.fz3EQrDwtoC74GHzCsygdt1ORV66siAQMRamjpU4I1U")
        if not url or not anon_key:
            raise ValueError("Supabase URL or anon key not provided in environment variables.")
        
        client = create_client(url, anon_key)
        return client
    except Exception as e:
        raise ValueError(f"Failed to initialize Supabase client: {e}")
