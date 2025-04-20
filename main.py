import streamlit as st
import random
import time
import os
from supabase_client import get_supabase_client
from game_logic import (
    sync_game_state, initialize_game, start_game, send_chat_message,
    new_round, end_game, leave_game, update_difficulty, update_min_players,
    cleanup_inactive_players
)
from ui_components import render_join_create_screen, render_game_interface
from utils import get_val_or_default
from streamlit.components.v1 import html
import streamlit_javascript as st_js

if st.session_state.get("in_game", False):
    html(open("supabase_realtime.html").read(), height=0)
    st_js.run_js(f'''
        window.parent.postMessage({{
            type: "subscribe",
            roomId: "{st.session_state.room_id}",
            url: "{os.getenv("SUPABASE_URL")}",
            key: "{os.getenv("SUPABASE_ANON_KEY")}"
        }}, "*")
    ''')
    updates = st_js.get_from_js("window.receivedMessages")
    if updates:
        for update in updates:
            if update["type"] == "room_update":
                st.session_state.game_state = update["data"]["game_state"]["status"]
            elif update["type"] == "players_update":
                st.session_state.players = sorted(
                    [{"id": p["user_id"], "name": p["name"], "score": p["score"], "color": p["color"], "avatar": p["avatar"]} for p in update["data"] if time.time() - p["last_seen"] < 60],
                    key=lambda x: x["score"],
                    reverse=True
                )
            elif update["type"] == "messages_update":
                st.session_state.chat_messages = update["data"]
        st.experimental_rerun()

# Debug: Print directory contents
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir('.'))

# Set page config
st.set_page_config(
    page_title="That Drawing Game",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (simplified for brevity)
st.markdown("""
<style>
    .logo { font-family: 'Arial', sans-serif; font-size: 42px; color: #ff7b3b; }
    .chat-container { height: 350px; overflow-y: auto; background: white; border-radius: 12px; padding: 15px; }
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
    st.session_state.user_id = str(random.randint(1000, 9999))
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
    # Note: Streamlit doesn't support sleep in production; rely on rerun
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
