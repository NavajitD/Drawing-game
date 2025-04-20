import streamlit as st
import time
import random
import uuid
import logging
from supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

supabase = get_supabase_client()

def initialize_game(room_id, is_owner=False, username="Player"):
    """
    Initialize a game room with Supabase.
    """
    start_time = time.time()
    logger.info(f"Starting initialize_game for room {room_id}")

    st.session_state.room_id = room_id
    st.session_state.is_room_owner = is_owner
    st.session_state.username = username
    st.session_state.in_game = True
    st.session_state.last_sync = 0

    try:
        # Check if room exists
        room_check_start = time.time()
        room = supabase.table("rooms").select("*").eq("id", room_id).execute()
        logger.info(f"Room check took {time.time() - room_check_start:.2f} seconds")

        if not room.data and is_owner:
            # Create new room
            room_insert_start = time.time()
            room_data = {
                "id": room_id,
                "owner_id": st.session_state.user_id,
                "settings": {
                    "difficulty": st.session_state.difficulty,
                    "round_time": st.session_state.round_time,
                    "max_rounds": st.session_state.max_rounds,
                    "min_players": st.session_state.min_players
                },
                "game_state": {
                    "status": "waiting",
                    "current_round": 1,
                    "rounds_played": 0,
                    "current_word": "",
                    "drawing_player_id": "",
                    "timer_start": 0
                },
                "drawing_data": None,
                "created_at": int(time.time())
            }
            supabase.table("rooms").insert(room_data).execute()
            logger.info(f"Room insert took {time.time() - room_insert_start:.2f} seconds")

            # Add player
            player_insert_start = time.time()
            player_id = str(uuid.uuid4())
            player_data = {
                "id": player_id,
                "user_id": st.session_state.user_id,
                "room_id": room_id,
                "name": username,
                "score": 0,
                "color": random.choice(["#FF5722", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5"]),
                "avatar": username[0].upper(),
                "last_seen": int(time.time())
            }
            supabase.table("players").insert(player_data).execute()
            logger.info(f"Player insert took {time.time() - player_insert_start:.2f} seconds")

            # Add system messages
            message_insert_start = time.time()
            system_messages = [
                {
                    "room_id": room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"Room created! Waiting for at least {st.session_state.min_players} players to join."
                    },
                    "created_at": int(time.time())
                },
                {
                    "room_id": room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"{username} has joined the room."
                    },
                    "created_at": int(time.time())
                }
            ]
            for msg in system_messages:
                supabase.table("chat_messages").insert(msg).execute()
            logger.info(f"Message insert took {time.time() - message_insert_start:.2f} seconds")

        elif room.data and not is_owner:
            # Join existing room
            join_start = time.time()
            room = room.data[0]
            player_id = str(uuid.uuid4())
            player_data = {
                "id": player_id,
                "user_id": st.session_state.user_id,
                "room_id": room_id,
                "name": username,
                "score": 0,
                "color": random.choice(["#FF5722", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5"]),
                "avatar": username[0].upper(),
                "last_seen": int(time.time())
            }
            supabase.table("players").insert(player_data).execute()

            new_message = {
                "room_id": room_id,
                "message_data": {
                    "type": "system",
                    "content": f"{username} has joined the room."
                },
                "created_at": int(time.time())
            }
            supabase.table("chat_messages").insert(new_message).execute()

            settings = room.get("settings", {})
            st.session_state.difficulty = settings.get("difficulty", "medium")
            st.session_state.round_time = settings.get("round_time", 60)
            st.session_state.max_rounds = settings.get("max_rounds", 3)
            st.session_state.min_players = settings.get("min_players", 2)
            st.session_state.game_state = room.get("game_state", {}).get("status", "waiting")
            logger.info(f"Join room took {time.time() - join_start:.2f} seconds")

        elif not room.data and not is_owner:
            st.error(f"Room {room_id} does not exist!")
            st.session_state.in_game = False
            return

        st.session_state.game_initialized = True
        sync_game_state()
        logger.info(f"Total initialize_game took {time.time() - start_time:.2f} seconds")

    except Exception as e:
        st.error(f"Error initializing game: {e}")
        st.session_state.in_game = False
        logger.error(f"Error in initialize_game: {e}")

def sync_game_state():
    """
    Synchronize the local game state with Supabase data via polling.
    """
    if not st.session_state.in_game or not st.session_state.room_id:
        return

    current_time = time.time()
    if current_time - st.session_state.last_sync < 5:
        return

    sync_start = time.time()
    try:
        # Update player's last seen
        supabase.table("players").update({"last_seen": int(time.time())}).eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

        # Fetch room data
        room = supabase.table("rooms").select("*").eq("id", st.session_state.room_id).execute()
        if not room.data:
            st.error("Room no longer exists!")
            st.session_state.in_game = False
            return

        room = room.data[0]

        # Fetch players data
        players_data = supabase.table("players").select("*").eq("room_id", st.session_state.room_id).execute()
        st.session_state.players = [
            {
                "id": player["user_id"],
                "name": player["name"],
                "score": player["score"],
                "color": player["color"],
                "avatar": player["avatar"]
            }
            for player in players_data.data
            if time.time() - player["last_seen"] < 60
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

            is_drawing_player = st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id
            if not is_drawing_player:
                st.session_state.drawing_data = room.get("drawing_data")

        # Sync chat messages
        chat_data = supabase.table("chat_messages").select("message_data").eq("room_id", st.session_state.room_id).order("created_at").execute()
        st.session_state.chat_messages = [msg["message_data"] for msg in chat_data.data]

        st.session_state.last_sync = current_time
        logger.info(f"sync_game_state took {time.time() - sync_start:.2f} seconds")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error syncing with Supabase: {e}")
        logger.error(f"Error in sync_game_state: {e}")

def start_game():
    """
    Start the game by selecting the first drawer and word.
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

        supabase.table("rooms").update({
            "game_state": game_state,
            "drawing_data": None
        }).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Game started! {drawer_name} is drawing first."
            },
            "created_at": int(time.time())
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
    Send a chat message, handling correct guesses and score updates.
    """
    try:
        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "player",
                "player": st.session_state.username,
                "content": content
            },
            "created_at": int(time.time())
        }
        if is_correct:
            new_message["message_data"]["correct"] = True

        supabase.table("chat_messages").insert(new_message).execute()

        if is_correct:
            time_left = st.session_state.round_time - (time.time() - st.session_state.timer_start)
            score_gain = int(time_left * 5)
            supabase.table("players").update({"score": supabase.table("players").select("score").eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute().data[0]["score"] + score_gain}).eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

            word_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"The word was: {st.session_state.current_word.upper()}"
                },
                "created_at": int(time.time())
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
    Start a new round with the next drawer and word.
    """
    if not st.session_state.is_room_owner:
        return

    try:
        next_index = (st.session_state.drawing_player_index + 1) % len(st.session_state.players)
        next_player_id = st.session_state.players[next_index]["id"]
        next_player_name = st.session_state.players[next_index]["name"]
        new_word = random.choice(st.session_state.word_lists[st.session_state.difficulty])

        room = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room["game_state"]
        game_state["current_round"] += 1
        game_state["rounds_played"] += 1
        game_state["current_word"] = new_word
        game_state["drawing_player_id"] = next_player_id
        game_state["timer_start"] = int(time.time())

        supabase.table("rooms").update({
            "game_state": game_state,
            "drawing_data": None
        }).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Round {game_state['current_round']}! {next_player_name} is drawing now!"
            },
            "created_at": int(time.time())
        }
        supabase.table("chat_messages").insert(new_message).execute()

    except Exception as e:
        st.error(f"Error starting new round: {e}")

def end_game():
    """
    End the game and announce the winner.
    """
    if not st.session_state.is_room_owner:
        return

    try:
        highest_score = max(player["score"] for player in st.session_state.players)
        winners = [player["name"] for player in st.session_state.players if player["score"] == highest_score]

        room = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room["game_state"]
        game_state["status"] = "game_over"

        supabase.table("rooms").update({"game_state": game_state}).eq("id", st.session_state.room_id).execute()

        game_over_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": "Game over! Thanks for playing!"
            },
            "created_at": int(time.time())
        }
        winner_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Winner: {', '.join(winners)} with {highest_score} points!"
            },
            "created_at": int(time.time())
        }
        for msg in [game_over_message, winner_message]:
            supabase.table("chat_messages").insert(msg).execute()

        st.session_state.game_state = "game_over"

    except Exception as e:
        st.error(f"Error ending game: {e}")

def leave_game():
    """
    Allow a player to leave the game, updating ownership if necessary.
    """
    if not st.session_state.in_game or not st.session_state.room_id:
        return

    try:
        supabase.table("players").delete().eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

        leave_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"{st.session_state.username} left the room."
            },
            "created_at": int(time.time())
        }
        supabase.table("chat_messages").insert(leave_message).execute()

        if st.session_state.is_room_owner and len(st.session_state.players) > 1:
            for player in st.session_state.players:
                if player["id"] != st.session_state.user_id:
                    supabase.table("rooms").update({"owner_id": player["id"]}).eq("id", st.session_state.room_id).execute()
                    owner_message = {
                        "room_id": st.session_state.room_id,
                        "message_data": {
                            "type": "system",
                            "content": f"{player['name']} is now the room owner."
                        },
                        "created_at": int(time.time())
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
    Update the game difficulty.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game:
        return

    try:
        room = supabase.table("rooms").select("settings").eq("id", st.session_state.room_id).execute().data[0]
        settings = room["settings"]
        settings["difficulty"] = new_difficulty

        supabase.table("rooms").update({"settings": settings}).eq("id", st.session_state.room_id).execute()

        st.session_state.difficulty = new_difficulty

        difficulty_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Difficulty changed to {new_difficulty.title()}"
            },
            "created_at": int(time.time())
        }
        supabase.table("chat_messages").insert(difficulty_message).execute()

    except Exception as e:
        st.error(f"Error updating difficulty: {e}")

def update_min_players(new_min_players):
    """
    Update the minimum number of players.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game:
        return

    try:
        room = supabase.table("rooms").select("settings").eq("id", st.session_state.room_id).execute().data[0]
        settings = room["settings"]
        settings["min_players"] = new_min_players

        supabase.table("rooms").update({"settings": settings}).eq("id", st.session_state.room_id).execute()

        st.session_state.min_players = new_min_players

        min_players_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Minimum players changed to {new_min_players}"
            },
            "created_at": int(time.time())
        }
        supabase.table("chat_messages").insert(min_players_message).execute()

    except Exception as e:
        st.error(f"Error updating minimum players: {e}")

def cleanup_inactive_players():
    """
    Remove players inactive for over 60 seconds.
    """
    try:
        current_time = int(time.time())
        inactive_players = supabase.table("players").select("name").eq("room_id", st.session_state.room_id).lt("last_seen", current_time - 60).execute()
        supabase.table("players").delete().eq("room_id", st.session_state.room_id).lt("last_seen", current_time - 60).execute()

        for player in inactive_players.data:
            leave_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"{player['name']} was removed due to inactivity."
                },
                "created_at": int(time.time())
            }
            supabase.table("chat_messages").insert(leave_message).execute()

    except Exception as e:
        st.error(f"Error cleaning up inactive players: {e}")
