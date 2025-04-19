import streamlit as st
import time
import random
from supabase_client import get_supabase_client

supabase = get_supabase_client()

def sync_game_state():
    """
    Synchronize the local game state with the data stored in Supabase.
    Updates room data, player data, and chat messages in the session state.
    """
    if not st.session_state.in_game or not st.session_state.room_id:
        return

    try:
        # Update player's last seen timestamp
        supabase.table("players").update(
            {"last_seen": int(time.time())}
        ).eq("user_id", st.session_state.user_id).eq(
            "room_id", st.session_state.room_id
        ).execute()

        # Fetch room data
        room_data = supabase.table("rooms").select("*").eq("id", st.session_state.room_id).execute()
        if not room_data.data:
            st.error("Room no longer exists!")
            st.session_state.in_game = False
            return

        room = room_data.data[0]

        # Fetch players data
        players_data = supabase.table("players").select("*").eq(
            "room_id", st.session_state.room_id
        ).execute()

        # Update players list, filtering out inactive ones
        st.session_state.players = [
            {
                "id": player["user_id"],
                "name": player["name"],
                "score": player["score"],
                "color": player["color"],
                "avatar": player["avatar"]
            }
            for player in players_data.data
            if time.time() - player["last_seen"] < 60  # Active within 60 seconds
        ]
        st.session_state.players = sorted(st.session_state.players, key=lambda x: x["score"], reverse=True)

        # Update game state
        game_state = room.get("game_state", {})
        st.session_state.game_state = game_state.get("status", "waiting")

        if st.session_state.game_state == "active":
            current_drawer_id = game_state.get("drawing_player_id", "")
            for i, player in enumerate(st.session_state.players):
                if player["id"] == current_drawer_id:
                    st.session_state.drawing_player_index = i
                    break

            st.session_state.current_word = game_state.get("current_word", "")
            st.session_state.hidden_word = "_ " * len(st.session_state.current_word)
            st.session_state.round_number = game_state.get("current_round", 1)
            st.session_state.rounds_played = game_state.get("rounds_played", 0)
            st.session_state.timer_start = game_state.get("timer_start", time.time())

            # Sync drawing data for non-drawers
            is_drawing_player = st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id
            if not is_drawing_player:
                st.session_state.drawing_data = room.get("drawing_data")

        # Sync chat messages
        chat_data = supabase.table("chat_messages").select(
            "message_data"
        ).eq("room_id", st.session_state.room_id).order(
            "created_at"
        ).execute()
        st.session_state.chat_messages = [msg["message_data"] for msg in chat_data.data]

    except Exception as e:
        st.error(f"Error syncing with Supabase: {e}")

def start_game():
    """
    Start the game by setting up the first drawer and word. Only the room owner can start.
    """
    if not st.session_state.is_room_owner:
        return

    try:
        drawer_index = random.randint(0, len(st.session_state.players) - 1)
        drawer_id = st.session_state.players[drawer_index]["id"]
        drawer_name = st.session_state.players[drawer_index]["name"]
        selected_word = random.choice(st.session_state.word_lists[st.session_state.difficulty])

        game_state = {
            "status": "active",
            "current_round": 1,
            "rounds_played": 0,
            "current_word": selected_word,
            "drawing_player_id": drawer_id,
            "timer_start": int(time.time())
        }

        supabase.table("rooms").update(
            {"game_state": game_state, "drawing_data": None}
        ).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Game started! {drawer_name} is drawing first."
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

        st.session_state.game_state = "active"
        st.session_state.drawing_player_index = drawer_index
        st.session_state.current_word = selected_word
        st.session_state.hidden_word = "_ " * len(selected_word)
        st.session_state.timer_start = time.time()

    except Exception as e:
        st.error(f"Error starting game: {e}")

def send_chat_message(content, is_correct=False):
    """
    Send a chat message. If it's a correct guess, update scores and progress the game.
    """
    try:
        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "player",
                "player": st.session_state.username,
                "content": content
            }
        }
        if is_correct:
            new_message["message_data"]["correct"] = True

        supabase.table("chat_messages").insert(new_message).execute()

        if is_correct:
            time_left = st.session_state.round_time - (time.time() - st.session_state.timer_start)
            score_gain = int(time_left * 5)
            player_data = supabase.table("players").select("score").eq(
                "user_id", st.session_state.user_id
            ).eq("room_id", st.session_state.room_id).execute().data[0]
            new_score = player_data["score"] + score_gain

            supabase.table("players").update(
                {"score": new_score}
            ).eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

            word_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"The word was: {st.session_state.current_word.upper()}"
                }
            }
            supabase.table("chat_messages").insert(word_message).execute()

            if st.session_state.rounds_played + 1 >= st.session_state.max_rounds:
                end_game()
            else:
                new_round()

    except Exception as e:
        st.error(f"Error sending message: {e}")

def new_round():
    """
    Start a new round with the next drawer and a new word. Only the room owner can initiate.
    """
    if not st.session_state.is_room_owner:
        return

    try:
        next_index = (st.session_state.drawing_player_index + 1) % len(st.session_state.players)
        next_player_id = st.session_state.players[next_index]["id"]
        next_player_name = st.session_state.players[next_index]["name"]
        new_word = random.choice(st.session_state.word_lists[st.session_state.difficulty])

        room_data = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room_data["game_state"]
        game_state["current_round"] += 1
        game_state["rounds_played"] += 1
        game_state["current_word"] = new_word
        game_state["drawing_player_id"] = next_player_id
        game_state["timer_start"] = int(time.time())

        supabase.table("rooms").update(
            {"game_state": game_state, "drawing_data": None}
        ).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Round {game_state['current_round']}! {next_player_name} is drawing now!"
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

    except Exception as e:
        st.error(f"Error starting new round: {e}")

def end_game():
    """
    End the game and announce winners. Only the room owner can end it.
    """
    if not st.session_state.is_room_owner:
        return

    try:
        highest_score = max(player["score"] for player in st.session_state.players)
        winners = [player["name"] for player in st.session_state.players if player["score"] == highest_score]

        room_data = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room_data["game_state"]
        game_state["status"] = "game_over"

        supabase.table("rooms").update(
            {"game_state": game_state}
        ).eq("id", st.session_state.room_id).execute()

        game_over_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": "Game over! Thanks for playing!"
            }
        }
        winner_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Winner: {', '.join(winners)} with {highest_score} points!"
            }
        }
        supabase.table("chat_messages").insert([game_over_message, winner_message]).execute()

        st.session_state.game_state = "game_over"

    except Exception as e:
        st.error(f"Error ending game: {e}")

def leave_game():
    """
    Allow a player to leave the game, updating the room state and ownership if necessary.
    """
    if not st.session_state.in_game or not st.session_state.room_id:
        return

    try:
        supabase.table("players").delete().eq(
            "user_id", st.session_state.user_id
        ).eq("room_id", st.session_state.room_id).execute()

        leave_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"{st.session_state.username} left the room."
            }
        }
        supabase.table("chat_messages").insert(leave_message).execute()

        if st.session_state.is_room_owner and len(st.session_state.players) > 1:
            for player in st.session_state.players:
                if player["id"] != st.session_state.user_id:
                    supabase.table("rooms").update(
                        {"owner_id": player["id"]}
                    ).eq("id", st.session_state.room_id).execute()
                    owner_message = {
                        "room_id": st.session_state.room_id,
                        "message_data": {
                            "type": "system",
                            "content": f"{player['name']} is now the room owner."
                        }
                    }
                    supabase.table("chat_messages").insert(owner_message).execute()
                    break

        st.session_state.in_game = False
        st.session_state.game_initialized = False

    except Exception as e:
        st.error(f"Error leaving game: {e}")
        st.session_state.in_game = False
        st.session_state.game_initialized = False

def update_difficulty(new_difficulty):
    """
    Update the game difficulty setting. Only the room owner can change it.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game:
        return

    try:
        room_data = supabase.table("rooms").select("settings").eq("id", st.session_state.room_id).execute().data[0]
        settings = room_data["settings"]
        settings["difficulty"] = new_difficulty

        supabase.table("rooms").update(
            {"settings": settings}
        ).eq("id", st.session_state.room_id).execute()

        st.session_state.difficulty = new_difficulty

        difficulty_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Difficulty changed to {new_difficulty.title()}"
            }
        }
        supabase.table("chat_messages").insert(difficulty_message).execute()

    except Exception as e:
        st.error(f"Error updating difficulty: {e}")

def update_min_players(new_min_players):
    """
    Update the minimum number of players required. Only the room owner can change it.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game:
        return

    try:
        room_data = supabase.table("rooms").select("settings").eq("id", st.session_state.room_id).execute().data[0]
        settings = room_data["settings"]
        settings["min_players"] = new_min_players

        supabase.table("rooms").update(
            {"settings": settings}
        ).eq("id", st.session_state.room_id).execute()

        st.session_state.min_players = new_min_players

        min_players_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Minimum players changed to {new_min_players}"
            }
        }
        supabase.table("chat_messages").insert(min_players_message).execute()

    except Exception as e:
        st.error(f"Error updating minimum players: {e}")

def cleanup_inactive_players():
    """
    Remove players inactive for over 60 seconds from the game.
    """
    try:
        current_time = int(time.time())
        inactive_players = supabase.table("players").select("*").eq(
            "room_id", st.session_state.room_id
        ).lt("last_seen", current_time - 60).execute().data

        for player in inactive_players:
            supabase.table("players").delete().eq("id", player["id"]).execute()
            leave_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"{player['name']} was removed due to inactivity."
                }
            }
            supabase.table("chat_messages").insert(leave_message).execute()

    except Exception as e:
        st.error(f"Error cleaning up inactive players: {e}")
