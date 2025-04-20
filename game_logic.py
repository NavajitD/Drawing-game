import streamlit as st
import time
import random
import uuid
import logging
from firebase_client import get_firestore_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = get_firestore_client()

def initialize_game(room_id, is_owner=False, username="Player"):
    """
    Initialize a game room with Firebase Firestore.
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
        room_ref = db.collection("rooms").document(room_id)
        room_doc = room_ref.get()
        logger.info(f"Room check took {time.time() - room_check_start:.2f} seconds")

        if not room_doc.exists and is_owner:
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
                "created_at": time.time()
            }
            room_ref.set(room_data)
            logger.info(f"Room insert took {time.time() - room_insert_start:.2f} seconds")

            # Add player
            player_insert_start = time.time()
            player_id = str(uuid.uuid4())
            player_data = {
                "user_id": st.session_state.user_id,
                "room_id": room_id,
                "name": username,
                "score": 0,
                "color": random.choice(["#FF5722", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5"]),
                "avatar": username[0].upper(),
                "last_seen": int(time.time())
            }
            db.collection("players").document(player_id).set(player_data)
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
                    "created_at": time.time()
                },
                {
                    "room_id": room_id,
                    "message_data": {
                        "type": "system",
                        "content": f"{username} has joined the room."
                    },
                    "created_at": time.time()
                }
            ]
            for msg in system_messages:
                db.collection("chat_messages").document(str(uuid.uuid4())).set(msg)
            logger.info(f"Message insert took {time.time() - message_insert_start:.2f} seconds")

        elif room_doc.exists and not is_owner:
            # Join existing room
            join_start = time.time()
            room = room_doc.to_dict()
            player_id = str(uuid.uuid4())
            player_data = {
                "user_id": st.session_state.user_id,
                "room_id": room_id,
                "name": username,
                "score": 0,
                "color": random.choice(["#FF5722", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5"]),
                "avatar": username[0].upper(),
                "last_seen": int(time.time())
            }
            db.collection("players").document(player_id).set(player_data)

            new_message = {
                "room_id": room_id,
                "message_data": {
                    "type": "system",
                    "content": f"{username} has joined the room."
                },
                "created_at": time.time()
            }
            db.collection("chat_messages").document(str(uuid.uuid4())).set(new_message)

            settings = room.get("settings", {})
            st.session_state.difficulty = settings.get("difficulty", "medium")
            st.session_state.round_time = settings.get("round_time", 60)
            st.session_state.max_rounds = settings.get("max_rounds", 3)
            st.session_state.min_players = settings.get("min_players", 2)
            st.session_state.game_state = room.get("game_state", {}).get("status", "waiting")
            logger.info(f"Join room took {time.time() - join_start:.2f} seconds")

        elif not room_doc.exists and not is_owner:
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
    Synchronize the local game state with Firebase data via polling.
    """
    if not st.session_state.in_game or not st.session_state.room_id:
        return

    current_time = time.time()
    if current_time - st.session_state.last_sync < 5:
        return

    sync_start = time.time()
    try:
        # Update player's last seen
        players = db.collection("players").where("user_id", "==", st.session_state.user_id).where("room_id", "==", st.session_state.room_id).get()
        for player in players:
            player.reference.update({"last_seen": int(time.time())})

        # Fetch room data
        room_doc = db.collection("rooms").document(st.session_state.room_id).get()
        if not room_doc.exists:
            st.error("Room no longer exists!")
            st.session_state.in_game = False
            return

        room = room_doc.to_dict()

        # Fetch players data
        players_data = db.collection("players").where("room_id", "==", st.session_state.room_id).get()
        st.session_state.players = [
            {
                "id": player.to_dict()["user_id"],
                "name": player.to_dict()["name"],
                "score": player.to_dict()["score"],
                "color": player.to_dict()["color"],
                "avatar": player.to_dict()["avatar"]
            }
            for player in players_data
            if time.time() - player.to_dict()["last_seen"] < 60
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
        chat_data = db.collection("chat_messages").where("room_id", "==", st.session_state.room_id).order_by("created_at").get()
        st.session_state.chat_messages = [msg.to_dict()["message_data"] for msg in chat_data]

        st.session_state.last_sync = current_time
        logger.info(f"sync_game_state took {time.time() - sync_start:.2f} seconds")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error syncing with Firebase: {e}")
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

        db.collection("rooms").document(st.session_state.room_id).update({
            "game_state": game_state,
            "drawing_data": None
        })

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Game started! {drawer_name} is drawing first."
            },
            "created_at": time.time()
        }
        db.collection("chat_messages").document(str(uuid.uuid4())).set(new_message)

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
            "created_at": time.time()
        }
        if is_correct:
            new_message["message_data"]["correct"] = True

        db.collection("chat_messages").document(str(uuid.uuid4())).set(new_message)

        if is_correct:
            time_left = st.session_state.round_time - (time.time() - st.session_state.timer_start)
            score_gain = int(time_left * 5)
            players = db.collection("players").where("user_id", "==", st.session_state.user_id).where("room_id", "==", st.session_state.room_id).get()
            for player in players:
                new_score = player.to_dict()["score"] + score_gain
                player.reference.update({"score": new_score})

            word_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"The word was: {st.session_state.current_word.upper()}"
                },
                "created_at": time.time()
            }
            db.collection("chat_messages").document(str(uuid.uuid4())).set(word_message)

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

        room_doc = db.collection("rooms").document(st.session_state.room_id).get()
        game_state = room_doc.to_dict()["game_state"]
        game_state["current_round"] += 1
        game_state["rounds_played"] += 1
        game_state["current_word"] = new_word
        game_state["drawing_player_id"] = next_player_id
        game_state["timer_start"] = int(time.time())

        db.collection("rooms").document(st.session_state.room_id).update({
            "game_state": game_state,
            "drawing_data": None
        })

        new_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Round {game_state['current_round']}! {next_player_name} is drawing now!"
            },
            "created_at": time.time()
        }
        db.collection("chat_messages").document(str(uuid.uuid4())).set(new_message)

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

        room_doc = db.collection("rooms").document(st.session_state.room_id).get()
        game_state = room_doc.to_dict()["game_state"]
        game_state["status"] = "game_over"

        db.collection("rooms").document(st.session_state.room_id).update({"game_state": game_state})

        game_over_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": "Game over! Thanks for playing!"
            },
            "created_at": time.time()
        }
        winner_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Winner: {', '.join(winners)} with {highest_score} points!"
            },
            "created_at": time.time()
        }
        for msg in [game_over_message, winner_message]:
            db.collection("chat_messages").document(str(uuid.uuid4())).set(msg)

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
        players = db.collection("players").where("user_id", "==", st.session_state.user_id).where("room_id", "==", st.session_state.room_id).get()
        for player in players:
            player.reference.delete()

        leave_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"{st.session_state.username} left the room."
            },
            "created_at": time.time()
        }
        db.collection("chat_messages").document(str(uuid.uuid4())).set(leave_message)

        if st.session_state.is_room_owner and len(st.session_state.players) > 1:
            for player in st.session_state.players:
                if player["id"] != st.session_state.user_id:
                    db.collection("rooms").document(st.session_state.room_id).update({"owner_id": player["id"]})
                    owner_message = {
                        "room_id": st.session_state.room_id,
                        "message_data": {
                            "type": "system",
                            "content": f"{player['name']} is now the room owner."
                        },
                        "created_at": time.time()
                    }
                    db.collection("chat_messages").document(str(uuid.uuid4())).set(owner_message)
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
        room_ref = db.collection("rooms").document(st.session_state.room_id)
        room_doc = room_ref.get()
        settings = room_doc.to_dict()["settings"]
        settings["difficulty"] = new_difficulty

        room_ref.update({"settings": settings})

        st.session_state.difficulty = new_difficulty

        difficulty_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Difficulty changed to {new_difficulty.title()}"
            },
            "created_at": time.time()
        }
        db.collection("chat_messages").document(str(uuid.uuid4())).set(difficulty_message)

    except Exception as e:
        st.error(f"Error updating difficulty: {e}")

def update_min_players(new_min_players):
    """
    Update the minimum number of players.
    """
    if not st.session_state.is_room_owner or not st.session_state.in_game:
        return

    try:
        room_ref = db.collection("rooms").document(st.session_state.room_id)
        room_doc = room_ref.get()
        settings = room_doc.to_dict()["settings"]
        settings["min_players"] = new_min_players

        room_ref.update({"settings": settings})

        st.session_state.min_players = new_min_players

        min_players_message = {
            "room_id": st.session_state.room_id,
            "message_data": {
                "type": "system",
                "content": f"Minimum players changed to {new_min_players}"
            },
            "created_at": time.time()
        }
        db.collection("chat_messages").document(str(uuid.uuid4())).set(min_players_message)

    except Exception as e:
        st.error(f"Error updating minimum players: {e}")

def cleanup_inactive_players():
    """
    Remove players inactive for over 60 seconds.
    """
    try:
        current_time = int(time.time())
        players = db.collection("players").where("room_id", "==", st.session_state.room_id).where("last_seen", "<", current_time - 60).get()
        for player in players:
            player.reference.delete()
            leave_message = {
                "room_id": st.session_state.room_id,
                "message_data": {
                    "type": "system",
                    "content": f"{player.to_dict()['name']} was removed due to inactivity."
                },
                "created_at": time.time()
            }
            db.collection("chat_messages").document(str(uuid.uuid4())).set(leave_message)

    except Exception as e:
        st.error(f"Error cleaning up inactive players: {e}")
