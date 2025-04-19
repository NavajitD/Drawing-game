import streamlit as st
import random
import time
from supabase_client import get_supabase_client
from game_logic import (sync_game_state, initialize_game, start_game, send_chat_message, 
                       new_round, end_game, leave_game, update_difficulty, update_min_players, cleanup_inactive_players)
from ui_components import render_join_create_screen, render_game_interface
from utils import get_val_or_default

# Set page config
st.set_page_config(
    page_title="That Drawing Game",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with enhancements
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Paytone+One&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Comfortaa:wght@300;400;500;600;700&display=swap');
    
    :root {
        --background-color: #f2f2f2;
        --text-color: #333;
        --card-bg: white;
        --primary-color: #ff7b3b;
        --secondary-color: #4b6fff;
        --chat-bg: white;
        --timer-bg: #ddd;
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --background-color: #121212;
            --text-color: #e6e6e6;
            --card-bg: #1e1e1e;
            --primary-color: #ff9d5c;
            --secondary-color: #7c89ff;
            --chat-bg: #1e1e1e;
            --timer-bg: #333;
        }
    }
    
    .logo {
        font-family: 'Paytone One', sans-serif;
        font-size: 42px;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .timer-bar {
        height: 100%;
        background: linear-gradient(to right, #4CAF50, #FFC107, #FF5722);
        transition: width 1s linear;
    }
    
    .chat-container {
        height: 350px;
        overflow-y: auto;
        background-color: var(--chat-bg);
        border-radius: 12px;
        padding: 15px;
    }
    
    .leaderboard {
        animation: fadeIn 0.5s ease;
        background-color: var(--card-bg);
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 123, 59, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 123, 59, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 123, 59, 0); }
    }
</style>
""", unsafe_allow_html=True)

# Initialize Supabase
supabase = get_supabase_client()

# Session state initialization
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.word_lists = {
        "easy": ["dog", "cat", "sun"],
        "medium": ["airplane", "birthday", "computer"],
        "hard": ["skyscraper", "electricity", "photosynthesis"]
    }
    st.session_state.user_id = str(random.randint(1000, 9999))  # Simplified for demo
    st.session_state.username = None
    st.session_state.room_id = None
    st.session_state.is_room_owner = False
    st.session_state.in_game = False
    st.session_state.difficulty = "medium"
    st.session_state.round_time = 60
    st.session_state.max_rounds = 3
    st.session_state.min_players = 2
    st.session_state.game_state = "waiting"
    st.session_state.players = []
    st.session_state.chat_messages = []
    st.session_state.drawing_player_index = 0
    st.session_state.current_word = ""
    st.session_state.timer_start = time.time()

# Periodic sync and cleanup
def periodic_tasks():
    if st.session_state.in_game:
        sync_game_state()
        if st.session_state.is_room_owner:
            cleanup_inactive_players()
    time.sleep(1)  # Simplified; in practice, use Streamlit's rerun
    st.experimental_rerun()

# Main app logic
if not st.session_state.in_game:
    render_join_create_screen()
else:
    periodic_tasks()
    render_game_interface()

# Footer
st.markdown("""
<div class="footer">
    <p>🎮 That Drawing Game | A Streamlit Multiplayer Game</p>
</div>
""", unsafe_allow_html=True)
