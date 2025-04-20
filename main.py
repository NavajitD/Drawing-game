import streamlit as st
import os
import uuid
from supabase_client import get_supabase_client
from game_logic import initialize_game, sync_game_state, start_game, send_chat_message, leave_game, update_difficulty, update_min_players
from ui_components import render_game_ui  # Handles canvas, chat, players

# Set page config first
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

# Debug environment variables (temporary)
st.write("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
st.write("SUPABASE_ANON_KEY:", os.getenv("SUPABASE_ANON_KEY")[:10] + "..." if os.getenv("SUPABASE_ANON_KEY") else None)

# Initialize Supabase client
supabase = None
try:
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY is not set")
    supabase = get_supabase_client(url, anon_key)
except ValueError as e:
    st.error(f"Failed to connect to database: {e}")

# Main app logic
st.title("That Drawing Game")

if not st.session_state.in_game:
    with st.form("join_form"):
        username = st.text_input("Enter your username", value="Player")
        room_id = st.text_input("Enter room ID or create a new one")
        is_owner = st.checkbox("Create new room")
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=["easy", "medium", "hard"].index(st.session_state.difficulty))
        min_players = st.number_input("Minimum players", min_value=2, max_value=10, value=st.session_state.min_players)
        submit = st.form_submit_button("Join/Create Room")
        
        if submit:
            if username and room_id:
                st.session_state.difficulty = difficulty
                st.session_state.min_players = min_players
                initialize_game(supabase, room_id, is_owner, username)
            else:
                st.error("Please enter a username and room ID")
else:
    sync_game_state(supabase)
    render_game_ui()  # Render full UI (canvas, chat, players)
    
    # Game controls
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.is_room_owner and st.session_state.game_state == "waiting":
            if st.button("Start Game"):
                start_game(supabase)
    with col2:
        if st.button("Leave Game"):
            leave_game(supabase)
    
    # Owner settings
    if st.session_state.is_room_owner:
        with st.expander("Game Settings"):
            new_difficulty = st.selectbox("Change Difficulty", ["easy", "medium", "hard"], index=["easy", "medium", "hard"].index(st.session_state.difficulty))
            new_min_players = st.number_input("Change Minimum Players", min_value=2, max_value=10, value=st.session_state.min_players)
            if st.button("Update Settings"):
                if new_difficulty != st.session_state.difficulty:
                    update_difficulty(supabase, new_difficulty)
                if new_min_players != st.session_state.min_players:
                    update_min_players(supabase, new_min_players)

# Debug: List files
if os.getenv("STREAMLIT_ENV") == "development":
    st.write("Files in directory:", os.listdir('.'))
