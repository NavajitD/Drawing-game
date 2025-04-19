from supabase import create_client, create_async_client, Client, AsyncClient

def get_supabase_client() -> Client:
    """
    Initialize and return a synchronous Supabase client for database and auth operations.
    Replace 'your_supabase_url' and 'your_supabase_key' with actual credentials.
    """
    SUPABASE_URL = "https://nmiblwofhcxyhkunhpxo.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5taWJsd29maGN4eWhrdW5ocHhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUwNjM3OTQsImV4cCI6MjA2MDYzOTc5NH0.-Gpcmn_k0-oNCSDcervRSbzsWWdyROTgbm2dz3OSuNM"  

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be provided.")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client

def get_supabase_async_client() -> AsyncClient:
    """
    Initialize and return an asynchronous Supabase client for real-time subscriptions.
    Replace 'your_supabase_url' and 'your_supabase_key' with actual credentials.
    """
    SUPABASE_URL = "https://nmiblwofhcxyhkunhpxo.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5taWJsd29maGN4eWhrdW5ocHhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUwNjM3OTQsImV4cCI6MjA2MDYzOTc5NH0.-Gpcmn_k0-oNCSDcervRSbzsWWdyROTgbm2dz3OSuNM"  # Replace with your Supabase key

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be provided.")

    async_client = create_async_client(SUPABASE_URL, SUPABASE_KEY)
    return async_client
