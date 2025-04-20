import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import Client

def render_game_ui(supabase: Client):
    """
    Render the game UI with drawing canvas, chat, and player list.
    """
    st.subheader(f"Room: {st.session_state.room_id}")
    
    # Drawing canvas
    if st.session_state.game_state == "active" and st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id:
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#ffffff",
            height=400,
            width=600,
            drawing_mode="freedraw",
            key=f"canvas_{st.session_state.room_id}"
        )
        if canvas_result.json_data:
            supabase.table("rooms").update({"drawing_data": canvas_result.json_data}).eq("id", st.session_state.room_id).execute()
    else:
        canvas_kwargs = {
            "fill_color": "rgba(255, 165, 0, 0.3)",
            "stroke_width": 2,
            "stroke_color": "#000000",
            "background_color": "#ffffff",
            "height": 400,
            "width": 600,
            "drawing_mode": "view",
            "key": f"canvas_{st.session_state.room_id}_view"
        }
        if st.session_state.drawing_data:
            canvas_kwargs["initial_drawing"] = st.session_state.drawing_data
        st_canvas(**canvas_kwargs)
    
    # Player list
    st.subheader("Players")
    for player in st.session_state.players:
        st.write(f"{player['avatar']} {player['name']} ({player['score']} points)")
    
    # Chat
    st.subheader("Chat")
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["type"] == "system":
                st.write(f"[System]: {msg['content']}")
            else:
                st.write(f"{msg['player']}: {msg['content']}")
    
    chat_input = st.text_input("Send a message", key=f"chat_{st.session_state.room_id}")
    if st.button("Send"):
        if chat_input:
            from game_logic import send_chat_message
            is_correct = chat_input.lower() == st.session_state.current_word.lower()
            send_chat_message(supabase, chat_input, is_correct)
