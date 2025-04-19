import streamlit as st
import random

def render_join_create_screen():
    """
    Render the screen for joining or creating a game with input fields and settings.
    """
    st.markdown('<div class="logo">That Drawing Game</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<h2 class="subheader">Join a Game</h2>', unsafe_allow_html=True)
        join_username = st.text_input("Your Nickname", key="join_username", placeholder="Enter your nickname")
        join_room = st.text_input("Room Code", key="join_room", placeholder="Enter room code (e.g., A12B3C)")

        if st.button("Join Game", key="join_btn"):
            if join_username and join_room:
                join_room = join_room.upper()
                initialize_game(join_room, is_owner=False, username=join_username)
                st.experimental_rerun()
            else:
                st.error("Please enter a nickname and room code.")

    with col2:
        st.markdown('<h2 class="subheader">Create a New Game</h2>', unsafe_allow_html=True)
        create_username = st.text_input("Your Nickname", key="create_username", placeholder="Enter your nickname")

        st.markdown('<h3 class="subheader" style="font-size: 18px; margin-top: 20px;">Game Settings</h3>', unsafe_allow_html=True)
        st.markdown("##### Difficulty Level")
        col_easy, col_med, col_hard = st.columns(3)

        with col_easy:
            if st.button("Easy", key="easy_btn"):
                st.session_state.difficulty = "easy"
        with col_med:
            if st.button("Medium", key="medium_btn"):
                st.session_state.difficulty = "medium"
        with col_hard:
            if st.button("Hard", key="hard_btn"):
                st.session_state.difficulty = "hard"

        st.markdown(f"Selected: **{st.session_state.difficulty.title()}**")

        col_time, col_rounds = st.columns(2)
        with col_time:
            round_time = st.slider("Round Time (seconds)", min_value=30, max_value=120, value=60, step=10)
            st.session_state.round_time = round_time
        with col_rounds:
            max_rounds = st.slider("Number of Rounds", min_value=2, max_value=10, value=3, step=1)
            st.session_state.max_rounds = max_rounds

        min_players = st.slider("Minimum Players", min_value=2, max_value=8, value=2, step=1)
        st.session_state.min_players = min_players

        if st.button("Create Game", key="create_btn"):
            if create_username:
                room_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
                initialize_game(room_code, is_owner=True, username=create_username)
                st.experimental_rerun()
            else:
                st.error("Please enter a nickname.")

def render_game_interface():
    """
    Render the main game interface with room info, player list (leaderboard), and enhanced chat.
    """
    col_logo, col_room = st.columns([2, 1])
    with col_logo:
        st.markdown('<div class="logo">That Drawing Game</div>', unsafe_allow_html=True)
    with col_room:
        game_state_text = st.session_state.game_state.replace("_", " ").title()
        st.markdown(f"""
        <div class="room-info">
            <strong>Room:</strong> {st.session_state.room_id} | 
            <strong>Difficulty:</strong> {st.session_state.difficulty.title()} 
            <span class="game-state {st.session_state.game_state}">{game_state_text}</span>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col2:
        st.markdown('<h3 class="subheader">Players</h3>', unsafe_allow_html=True)
        for player in st.session_state.players:
            is_drawing = player["id"] == st.session_state.players[st.session_state.drawing_player_index]["id"] if st.session_state.game_state == "active" else False
            st.markdown(f"""
            <div class="player-card {'drawing' if is_drawing else ''}">
                <div class="avatar" style="background-color: {player['color']};">{player['avatar']}</div>
                <div>{player['name']} {' (Drawing)' if is_drawing else ''}</div>
                <div>{player['score']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<h3 class="subheader">Chat</h3>', unsafe_allow_html=True)
        for message in st.session_state.chat_messages:
            if message["type"] == "system":
                st.markdown(f'<div class="message system-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                player_color = next((p["color"] for p in st.session_state.players if p["name"] == message["player"]), "#333")
                st.markdown(f'<div class="message player-message"><span style="color: {player_color};">{message["player"]}:</span> {message["content"]}</div>', unsafe_allow_html=True)

        chat_input = st.text_input("Type your guess here", key="chat_input")
        if st.button("Send", key="send_button"):
            if chat_input.strip():
                from game_logic import send_chat_message
                send_chat_message(chat_input)
                st.session_state.chat_input = ""
                st.experimental_rerun()

    with col1:
        if st.session_state.game_state == "active":
            is_drawing_player = st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id
            if is_drawing_player:
                st.markdown("<h3>Draw the word!</h3>", unsafe_allow_html=True)
                # Placeholder for drawing canvas (e.g., st_canvas)
            else:
                st.markdown(f"<h3>{st.session_state.players[st.session_state.drawing_player_index]['name']} is drawing...</h3>", unsafe_allow_html=True)
                # Placeholder for displaying drawing
