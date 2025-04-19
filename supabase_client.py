from supabase import create_client, Client

from supabase import create_client, Client

def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client with real-time support.
    Replace 'your_supabase_url' and 'your_supabase_key' with actual credentials.
    """
    SUPABASE_URL = "https://nmiblwofhcxyhkunhpxo.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5taWJsd29maGN4eWhrdW5ocHhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUwNjM3OTQsImV4cCI6MjA2MDYzOTc5NH0.-Gpcmn_k0-oNCSDcervRSbzsWWdyROTgbm2dz3OSuNM"  # Replace with your Supabase key

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be provided.")

    # Initialize client with real-time support
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return client
