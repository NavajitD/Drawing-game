import json
import os
from firebase_admin import initialize_app, firestore
from firebase_admin.credentials import Certificate

def get_firestore_client():
    """
    Initialize and return a Firebase Firestore client.
    """
    try:
        # Load credentials from Streamlit secrets
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
        if not firebase_credentials:
            raise ValueError("Firebase credentials not provided in environment variables.")

        # Parse JSON credentials
        cred_dict = json.loads(firebase_credentials)
        cred = Certificate(cred_dict)
        
        # Initialize Firebase app
        app = initialize_app(cred)
        client = firestore.client(app)
        return client
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase client: {e}")
