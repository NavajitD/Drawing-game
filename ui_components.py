import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import Client
import time

def render_game_ui(supabase: Client):
    """
    Render the enhanced game UI with drawing canvas, chat, and player list.
    """
    # Header with room ID and game status
    st.markdown(f"### Room: {st.session_state.room_id} - {st.session_state.game_state.title()}")
    
    # Main layout: Player list | Canvas | Chat
    col1, col2, col3 = st.columns([2, 6, 2])
    
    with col1:
        st.subheader("Players")
        for player in st.session_state.players:
            is_drawer = st.session_state.game_state == "active" and st.session_state.drawing_player_index is not None and player["id"] == st.session_state.players[st.session_state.drawing_player_index]["id"]
            avatar = player["avatar"] if not is_drawer else "✏️ " + player["avatar"]
            st.write(f"{avatar} {player['name']} ({player['score']} points)")
    
    with col2:
        # Drawing canvas
        if st.session_state.game_state == "active" and st.session_state.drawing_player_index is not None and st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id:
            # Drawer view
            st.write(f"**Draw: {st.session_state.current_word.upper()}**")
            col_color, col_brush = st.columns(2)
            with col_color:
                stroke_color = st.color_picker("Stroke color", "#000000")
            with col_brush:
                stroke_width = st.slider("Brush size", 1, 25, 2)
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_color="#ffffff",
                height=450,
                width=600,
                drawing_mode="freedraw",
                key=f"canvas_{st.session_state.room_id}"
            )
            if canvas_result.json_data:
                supabase.table("rooms").update({"drawing_data": canvas_result.json_data}).eq("id", st.session_state.room_id).execute()
        elif st.session_state.game_state == "active":
            # Guesser view
            st.write(f"**Guess the word: {st.session_state.hidden_word or 'Waiting...'}**")
            canvas_kwargs = {
                "fill_color": "rgba(255, 165, 0, 0.3)",
                "stroke_width": 2,
                "stroke_color": "#000000",
                "background_color": "#ffffff",
                "height": 450,
                "width": 600,
                "drawing_mode": "view",
                "key": f"canvas_{st.session_state.room_id}_view"
            }
            if st.session_state.drawing_data:
                canvas_kwargs["initial_drawing"] = st.session_state.drawing_data
            st_canvas(**canvas_kwargs)
        else:
            st.write("**Waiting for the game to start...**")
    
    with col3:
        st.subheader("Chat")
        chat_container = st.empty()
        with chat_container.container():
            for msg in st.session_state.chat_messages:
                if msg["type"] == "system":
                    st.markdown(f"<span style='color: #FFD700; font-weight: bold;'>[System]: {msg['content']}</span>", unsafe_allow_html=True)
                else:
                    color = "#00AEEF" if "correct" in msg and msg["correct"] else "#333333"
                    st.markdown(f"<span style='color: {color};'>{msg['player']}: {msg['content']}</span>", unsafe_allow_html=True)
        
        chat_input = st.text_input("Send a message", key=f"chat_{st.session_state.room_id}")
        if st.button("Send"):
            if chat_input:
                from game_logic import send_chat_message
                is_correct = chat_input.lower() == st.session_state.current_word.lower() if st.session_state.game_state == "active" else False
                send_chat_message(supabase, chat_input, is_correct)

    # Footer with instructions
    st.markdown("---")
    st.write("🎨 Draw or guess the word! Type your guesses in the chat. Good luck!")
