import streamlit as st
import time
import random
import uuid
import logging
from supabase import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_game(supabase: Client, room_id, is_owner=False, username="Player"):
    """
    Initialize a game room with Supabase.
    """
    if not supabase:
        st.error("Database connection not available")
        st.session_state.in_game = False
        return

    start_time = time.time()
    logger.info(f"Starting initialize_game for room {room_id}")

    st.session_state.room_id = room_id
    st.session_state.is_room_owner = is_owner
    st.session_state.username = username
    st.session_state.in_game = True
    st.session_state.last_sync = 0
    st.session_state.drawing_data = None
    st.session_state.drawing_player_index = None
    st.session_state.hidden_word = ""
    st.session_state.chat_messages = []
    st.session_state.word_options = []
    st.session_state.current_word = ""

    try:
        room_check_start = time.time()
        room = supabase.table("rooms").select("*").eq("id", room_id).execute()
        logger.info(f"Room check took {time.time() - room_check_start:.2f} seconds")

        if not room.data and is_owner:
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
                    "timer_start": 0,
                    "word_options": []
                },
                "drawing_data": None
            }
            supabase.table("rooms").insert(room_data).execute()
            logger.info(f"Room insert took {time.time() - room_insert_start:.2f} seconds")

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

            message_insert_start = time.time()
            system_messages = [
                {
                    "room_id": room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"Room {room_id} created! Waiting for at least {st.session_state.min_players} players to join."
                    }
                },
                {
                    "room_id": room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"{username} has joined the room."
                    }
                }
            ]
            supabase.table("chat_messages").insert(system_messages).execute()
            logger.info(f"Message insert took {time.time() - message_insert_start:.2f} seconds")

        elif room.data and not is_owner:
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
                }
            }
            supabase.table("chat_messages").insert(new_message).execute()

            settings = room.get("settings", {})
            st.session_state.difficulty = settings.get("difficulty", "medium")
            st.session_state.round_time = settings.get("round_time", 60)
            st.session_state.max_rounds = settings.get("max_rounds", 3)
            st.session_state.min_players = settings.get("min_players", 2)
            st.session_state.game_state = room.get("game_state", {}).get("status", "waiting")
            st.session_state.drawing_data = room.get("drawing_data", None)
            st.session_state.drawing_player_index = None
            st.session_state.hidden_word = ""
            st.session_state.word_options = []
            st.session_state.current_word = ""
            logger.info(f"Join room took {time.time() - join_start:.2f} seconds")

        elif not room.data and not is_owner:
            st.error(f"Room {room_id} does not exist!")
            st.session_state.in_game = False
            return

        st.session_state.game_initialized = True
        sync_game_state(supabase)
        logger.info(f"Total initialize_game took {time.time() - start_time:.2f} seconds")

    except Exception as e:
        st.error(f"Error initializing game: {e}")
        st.session_state.in_game = False
        logger.error(f"Error in initialize_game: {e}")

def sync_game_state(supabase: Client):
    """
    Synchronize local game state with Supabase.
    """
    if not st.session_state.in_game or not st.session_state.room_id or not supabase:
        return

    current_time = time.time()
    if current_time - st.session_state.last_sync < 2:  # Faster sync for chat
        return

    sync_start = time.time()
    try:
        supabase.table("players").update({"last_seen": int(current_time)}).eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

        room = supabase.table("rooms").select("*").eq("id", st.session_state.room_id).execute()
        if not room.data:
            st.error("Room no longer exists!")
            st.session_state.in_game = False
            return

        room = room.data[0]
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
            if current_time - player["last_seen"] < 60
        ]
        st.session_state.players = sorted(st.session_state.players, key=lambda x: x["score"], reverse=True)

        game_state = room.get("game_state", {})
        st.session_state.game_state = game_state.get("status", "waiting")

        if st.session_state.game_state == "active":
            current_drawer_id = game_state.get("drawing_player_id", "")
            st.session_state.drawing_player_index = None
            for i, player in enumerate(st.session_state.players):
                if player["id"] == current_drawer_id:
                    st.session_state.drawing_player_index = i
                    break

            if st.session_state.drawing_player_index is not None:
                st.session_state.current_word = game_state.get("current_word", "")
                st.session_state.hidden_word = "_ " * len(st.session_state.current_word)
                st.session_state.round_number = game_state.get("current_round", 1)
                st.session_state.rounds_played = game_state.get("rounds_played", 0)
                st.session_state.timer_start = game_state.get("timer_start", current_time)
                st.session_state.word_options = game_state.get("word_options", [])

                is_drawing_player = st.session_state.players[st.session_state.drawing_player_index]["id"] == st.session_state.user_id
                if not is_drawing_player:
                    st.session_state.drawing_data = room.get("drawing_data", None)
                else:
                    st.session_state.drawing_data = None
            else:
                st.session_state.word_options = []
                st.session_state.current_word = ""
                st.session_state.hidden_word = ""
        else:
            st.session_state.drawing_player_index = None
            st.session_state.drawing_data = None
            st.session_state.current_word = ""
            st.session_state.hidden_word = ""
            st.session_state.round_number = 1
            st.session_state.rounds_played = 0
            st.session_state.timer_start = 0
            st.session_state.word_options = []

        chat_data = supabase.table("chat_messages").select("message_data").eq("room_id", st.session_state.room_id).order("created_at").limit(50).execute()
        st.session_state.chat_messages = [msg["message_data"] for msg in chat_data.data]
        logger.info(f"Chat messages synced: {len(st.session_state.chat_messages)}")

        st.session_state.last_sync = current_time
        logger.info(f"sync_game_state took {time.time() - sync_start:.2f} seconds")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error syncing with Supabase: {e}")
        logger.error(f"Error in sync_game_state: {e}")

def start_game(supabase: Client):
    """
    Start the game with word options for the first drawer.
    """
    if not st.session_state.is_room_owner or not supabase or len(st.session_state.players) < st.session_state.min_players:
        st.error("Cannot start game: Insufficient players or not owner")
        return

    try:
        drawer_index = random.randint(0, len(st.session_state.players) - 1)
        drawer_id = st.session_state.players[drawer_index]["id"]
        drawer_name = st.session_state.players[drawer_index]["name"]
        word_options = random.sample(st.session_state.word_lists[st.session_state.difficulty], 3)

        game_state = {
            "status": "active",
            "current_round": 1,
            "rounds_played": 0,
            "current_word": "",  # Set after drawer chooses
            "drawing_player_id": drawer_id,
            "timer_start": int(time.time()),
            "word_options": word_options
        }

        supabase.table("rooms").update({
            "game_state": game_state,
            "drawing_data": None
        }).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Game started! {drawer_name} is choosing a word."
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

        st.session_state.game_state = "active"
        st.session_state.drawing_player_index = drawer_index
        st.session_state.word_options = word_options
        st.session_state.current_word = ""
        st.session_state.hidden_word = ""
        st.session_state.timer_start = time.time()
        st.session_state.drawing_data = None
        logger.info("Game started successfully")
        st.experimental_rerun()

    except Exception as e:
        st.error(f"Error starting game: {e}")
        logger.error(f"Error starting game: {e}")

def set_chosen_word(supabase: Client, chosen_word: str):
    """
    Drawer selects a word from options.
    """
    if not supabase or st.session_state.players[st.session_state.drawing_player_index]["id"] != st.session_state.user_id:
        return

    try:
        room = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room["game_state"]
        game_state["current_word"] = chosen_word
        game_state["word_options"] = []
        game_state["timer_start"] = int(time.time())

        supabase.table("rooms").update({
            "game_state": game_state,
            "drawing_data": None
        }).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"{st.session_state.username} is drawing!"
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

        st.session_state.current_word = chosen_word
        st.session_state.hidden_word = "_ " * len(chosen_word)
        st.session_state.word_options = []
        st.experimental_rerun()

    except Exception as e:
        st.error(f"Error choosing word: {e}")
        logger.error(f"Error choosing word: {e}")

def send_chat_message(supabase: Client, content, is_correct=False):
    """
    Send chat message with Skribbl.io scoring for correct guesses.
    """
    if not supabase:
        return

    try:
        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "player",
                "player": st.session_state.username,
                "content": content,
                "correct": is_correct
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

        if is_correct and st.session_state.game_state == "active":
            time_left = st.session_state.round_time - (time.time() - st.session_state.timer_start)
            if time_left > 0:
                guesser_score = int(100 * (time_left / st.session_state.round_time)) + 20  # Bonus for first guess
                drawer_score = int(100 * (time_left / st.session_state.round_time))
                
                # Update guesser score
                player = supabase.table("players").select("score").eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute().data[0]
                supabase.table("players").update({"score": player["score"] + guesser_score}).eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

                # Update drawer score
                drawer_id = st.session_state.players[st.session_state.drawing_player_index]["id"]
                drawer = supabase.table("players").select("score").eq("user_id", drawer_id).eq("room_id", st.session_state.room_id).execute().data[0]
                supabase.table("players").update({"score": drawer["score"] + drawer_score}).eq("user_id", drawer_id).eq("room_id", st.session_state.room_id).execute()

                word_message = {
                    "room_id": st.session_state.room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"{st.session_state.username} guessed correctly! The word was: {st.session_state.current_word.upper()}"
                    }
                }
                supabase.table("chat_messages").insert(word_message).execute()

                if st.session_state.rounds_played + 1 >= st.session_state.max_rounds:
                    end_game(supabase)
                else:
                    new_round(supabase)

    except Exception as e:
        st.error(f"Error sending message: {e}")
        logger.error(f"Error sending message: {e}")

def new_round(supabase: Client):
    """
    Start a new round with the next drawer and word options.
    """
    if not st.session_state.is_room_owner or not supabase:
        return

    try:
        next_index = (st.session_state.drawing_player_index + 1) % len(st.session_state.players)
        next_player_id = st.session_state.players[next_index]["id"]
        next_player_name = st.session_state.players[next_index]["name"]
        word_options = random.sample(st.session_state.word_lists[st.session_state.difficulty], 3)

        room = supabase.table("rooms").select("game_state").eq("id", st.session_state.room_id).execute().data[0]
        game_state = room["game_state"]
        game_state["current_round"] += 1
        game_state["rounds_played"] += 1
        game_state["current_word"] = ""
        game_state["drawing_player_id"] = next_player_id
        game_state["timer_start"] = int(time.time())
        game_state["word_options"] = word_options

        supabase.table("rooms").update({
            "game_state": game_state,
            "drawing_data": None
        }).eq("id", st.session_state.room_id).execute()

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Round {game_state['current_round']}! {next_player_name} is choosing a word."
            }
        }
        supabase.table("chat_messages").insert(new_message).execute()

        st.session_state.drawing_data = None
        st.session_state.drawing_player_index = next_index
        st.session_state.current_word = ""
        st.session_state.hidden_word = ""
        st.session_state.word_options = word_options
        st.experimental_rerun()

    except Exception as e:
        st.error(f"Error starting new round: {e}")
        logger.error(f"Error starting new round: {e}")

def end_game(supabase: Client):
    """
    End the game and announce the winner.
    """
    if not st.session_state.is_room_owner or not supabase:
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
        st.session_state.drawing_data = None
        st.session_state.drawing_player_index = None
        st.session_state.hidden_word = ""
        st.session_state.current_word = ""
        st.session_state.word_options = []
        st.experimental_rerun()

    except Exception as e:
        st.error(f"Error ending game: {e}")
        logger.error(f"Error ending game: {e}")

def leave_game(supabase: Client):
    """
    Allow a player to leave the game, updating ownership if necessary.
    """
    if not st.session_state.in_game or not st.session_state.room_id or not supabase:
        return

    try:
        supabase.table("players").delete().eq("user_id", st.session_state.user_id).eq("room_id", st.session_state.room_id).execute()

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
                    supabase.table("rooms").update({"owner_id": player["id"]}).eq("id", st.session_state.room_id).execute()
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
        st.session_state.drawing_data = None
        st.session_state.drawing_player_index = None
        st.session_state.hidden_word = ""
        st.session_state.current_word = ""
        st.session_state.word_options = []
        st.session_state.chat_messages = []
        logger.info("Player left game successfully")
        st.experimental_rerun()

    except Exception as e:
        st.error(f"Error leaving game: {e}")
        logger.error(f"Error leaving game: {e}")
        st.session_state.in_game = False
        st.session_state.game_initialized = False

def update_difficulty(supabase: Client, new_difficulty):
    """
    Update the game difficulty.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game or not supabase:
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
            }
        }
        supabase.table("chat_messages").insert(difficulty_message).execute()

    except Exception as e:
        st.error(f"Error updating difficulty: {e}")
        logger.error(f"Error updating difficulty: {e}")

def update_min_players(supabase: Client, new_min_players):
    """
    Update the minimum number of players.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game or not supabase:
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
            }
        }
        supabase.table("chat_messages").insert(min_players_message).execute()

    except Exception as e:
        st.error(f"Error updating minimum players: {e}")
        logger.error(f"Error updating minimum players: {e}")

def cleanup_inactive_players(supabase: Client):
    """
    Remove players inactive for over 60 seconds.
    """
    if not supabase:
        return

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
                }
            }
            supabase.table("chat_messages").insert(leave_message).execute()

    except Exception as e:
        st.error(f"Error cleaning up inactive players: {e}")
        logger.error(f"Error cleaning up inactive players: {e}")
