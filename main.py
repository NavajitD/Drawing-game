import streamlit as st
import os
import uuid
import string
import random
from supabase_client import get_supabase_client
from game_logic import initialize_game, sync_game_state, start_game, send_chat_message, leave_game, update_difficulty, update_min_players
from ui_components import render_game_ui

# Disable pages watcher
os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "false"

# Set page config
st.set_page_config(
    page_title="That Drawing Game",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply Skribbl.io-style CSS
st.markdown("""
    <style>
    body { background-color: #F0F0F0; color: #333333; font-family: 'Arial', sans-serif; }
    h1, h2, h3 { font-family: 'Comic Sans MS', cursive; color: #00AEEF; }
    .stButton>button { background-color: #00AEEF; color: white; border-radius: 10px; padding: 10px 20px; font-size: 16px; font-weight: bold; transition: all 0.3s; }
    .stButton>button:hover { background-color: #FFD700; color: #333333; }
    .stContainer { border-radius: 10px; padding: 10px; background-color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    @media (max-width: 768px) { .stColumn { width: 100% !important; } }
    </style>
""", unsafe_allow_html=True)

# Generate unique room code
def generate_room_code(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

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
        "easy": ["cat", "dog", "tree", "sun", "book"],
        "medium": ["house", "car", "boat", "chair", "lamp"],
        "hard": ["airplane", "mountain", "castle", "volcano", "bridge"]
    }
if "drawing_data" not in st.session_state:
    st.session_state.drawing_data = None
if "drawing_player_index" not in st.session_state:
    st.session_state.drawing_player_index = None
if "hidden_word" not in st.session_state:
    st.session_state.hidden_word = ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "word_options" not in st.session_state:
    st.session_state.word_options = []
if "current_word" not in st.session_state:
    st.session_state.current_word = ""

# Debug environment variables
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
        action = st.radio("Choose an action", ["Join Room", "Create New Room"])
        room_id = st.text_input("Enter room ID", disabled=action == "Create New Room")
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=["easy", "medium", "hard"].index(st.session_state.difficulty))
        min_players = st.number_input("Minimum players", min_value=2, max_value=10, value=st.session_state.min_players)
        submit = st.form_submit_button("Submit")
        
        if submit:
            if username:
                if action == "Create New Room":
                    room_id = generate_room_code()
                    while supabase.table("rooms").select("id").eq("id", room_id).execute().data:
                        room_id = generate_room_code()
                    is_owner = True
                else:
                    if not room_id:
                        st.error("Please enter a room ID")
                        st.stop()
                    is_owner = False
                
                st.session_state.difficulty = difficulty
                st.session_state.min_players = min_players
                initialize_game(supabase, room_id, is_owner, username)
            else:
                st.error("Please enter a username")
else:
    sync_game_state(supabase)
    st.write("Rendering game UI, in_game:", st.session_state.in_game, "game_state:", st.session_state.game_state)
    render_game_ui(supabase)
    
    # Game controls
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.is_room_owner and st.session_state.game_state == "waiting":
            if len(st.session_state.players) >= st.session_state.min_players:
                if st.button("Start Game"):
                    start_game(supabase)
            else:
                st.write(f"Need at least {st.session_state.min_players} players to start!")
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
