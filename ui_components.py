import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import Client
import time
from game_logic import set_chosen_word

def render_game_ui(supabase: Client):
    """
    Render the Skribbl.io-style game UI with word selection, canvas, chat, and player list.
    """
    st.markdown(f"### Room: {st.session_state.room_id} - {st.session_state.game_state.title()}")
    
    col1, col2, col3 = st.columns([2, 6, 2])
    
    with col1:
        st.subheader("Players")
        for player in st.session_state.players:
            is_drawer = st.session_state.game_state == "active" and st.session_state.drawing_player_index is not None and player["id"] == st.session_state.players[st.session_state.drawing_player_index]["id"]
            avatar = player["avatar"] if not is_drawer else "✏️ " + player["avatar"]
            st.write(f"{avatar} {player['name']} ({player['score']} points)")
    
    with col2:
        if st.session_state.game_state == "active" and st.session_state.drawing_player_index is not None:
            if st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id:
                if st.session_state.word_options:
                    st.write("**Choose a word to draw:**")
                    cols = st.columns(3)
                    for i, word in enumerate(st.session_state.word_options):
                        with cols[i]:
                            if st.button(word.upper(), key=f"word_{i}"):
                                set_chosen_word(supabase, word)
                elif st.session_state.current_word:
                    st.write(f"**Draw: {st.session_state.current_word.upper()} ({len(st.session_state.current_word)} letters)**")
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
            else:
                word_length = len(st.session_state.current_word) if st.session_state.current_word else 0
                st.write(f"**Guess the word: {st.session_state.hidden_word or 'Waiting...'} ({word_length} letters)**")
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
        chat_container = st.container()
        with chat_container:
            if st.session_state.chat_messages:
                for msg in st.session_state.chat_messages:
                    if msg["type"] == "system":
                        st.markdown(f"<span style='color: #FFD700; font-weight: bold;'>[System]: {msg['content']}</span>", unsafe_allow_html=True)
                    else:
                        color = "#00AEEF" if msg.get("correct", False) else "#333333"
                        st.markdown(f"<span style='color: {color};'>{msg['player']}: {msg['content']}</span>", unsafe_allow_html=True)
            else:
                st.write("No messages yet.")
        
        chat_input = st.text_input("Send a message", key=f"chat_{st.session_state.room_id}")
        if st.button("Send"):
            if chat_input:
                from game_logic import send_chat_message
                is_correct = chat_input.lower() == st.session_state.current_word.lower() if st.session_state.game_state == "active" and st.session_state.current_word else False
                send_chat_message(supabase, chat_input, is_correct)

    st.markdown("---")
    st.write("🎨 Draw or guess the word! Type your guesses in the chat. Good luck!")
