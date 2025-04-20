import streamlit as st
import os
import uuid
from supabase_client import get_supabase_client
from game_logic import initialize_game, sync_game_state

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="That Drawing Game",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "in_game" not in st.session_state:
    st.session_state.in_game = False
if "difficulty" not in st.session_state:
    st.session_state.difficulty = "medium"
if "round_time" not in st.session_state:
    st.session_state.round_time = 60
if "max_rounds" not in st.session_state:
    st.session_state.max_rounds = 3
if "min_players" not in st.session_state:
    st.session_state.min_players = 2
if "word_lists" not in st.session_state:
    st.session_state.word_lists = {
        "easy": ["cat", "dog", "tree"],
        "medium": ["house", "car", "boat"],
        "hard": ["airplane", "mountain", "castle"]
    }

# Initialize Supabase client
supabase = None
try:
    supabase = get_supabase_client()
except ValueError as e:
    st.error(f"Failed to connect to database: {e}")

# Main app logic
st.title("That Drawing Game")

if not st.session_state.in_game:
    username = st.text_input("Enter your username", value="Player")
    room_id = st.text_input("Enter room ID or create a new one")
    is_owner = st.checkbox("Create new room")
    
    if st.button("Join/Create Room"):
        if username and room_id:
            initialize_game(room_id, is_owner, username)
        else:
            st.error("Please enter a username and room ID")
else:
    sync_game_state()
    st.write(f"In room: {st.session_state.room_id}")
    if st.button("Leave Game"):
        from game_logic import leave_game
        leave_game()

# Debug: List files
if os.getenv("STREAMLIT_ENV") == "development":
    st.write("Files in directory:", os.listdir('.'))
