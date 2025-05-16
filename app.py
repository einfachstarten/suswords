from flask import Flask, request, jsonify, render_template
import uuid
import os
import json
import random

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "games")
SECRET_WORDS = [
    "Ampel", "Ananas", "Badehose", "Ballon", "Banane", "Banjo", "Besen", "Besenstiel", "Bleistift", "Blitz",
    "Brille", "Brunnen", "Buch", "Drachen", "Eimer", "Einhorn", "Eule", "Fernbedienung", "Feuerzeug", "Flasche",
    "Fuchs", "Geist", "Gießkanne", "Gitarre", "Glühbirne", "Gurke", "Haferflocken", "Heft", "Joystick", "Kaktus",
    "Kamera", "Kartoffel", "Kaugummi", "Keks", "Keksdose", "Ketchup", "Kette", "Kissen", "Klobürste", "Koala",
    "Koffer", "Komet", "Kopfhörer", "Krabbe", "Kronkorken", "Kühlschrank", "Känguru", "Lampe", "Laser", "Laterne",
    "Leiter", "Limo", "Lupe", "Laptop", "Matratze", "Mikrofon", "Mousepad", "Möhre", "Ninja", "Orgel",
    "Pfannkuchen", "Picknick", "Pirat", "Pizza", "Pullover", "Pudding", "Rakete", "Regenschirm", "Roboter", "Roller",
    "Rollschuh", "Rucksack", "Schaufel", "Schnorchel", "Schere", "Schirm", "Schlüssel", "Schmetterling", "Schraube", "Schublade",
    "Segelboot", "Seil", "Socke", "Spaghetti", "Staubsauger", "Tastatur", "Tischtennis", "Tornado", "Trommel", "Trampolin",
    "Vampir", "Vulkan", "Waschbär", "Wolke", "Würfel", "Würstchen", "Zauberer", "Zaun", "Zebra"
]

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@app.route("/")
def landing_page():
    return render_template("index.html")

@app.route("/ui")
def test_ui():
    return render_template("test_ui.html")

@app.route("/create")
def create_game_ui():
    return render_template("create_game.html")

@app.route("/game")
def game():
    game_id = request.args.get("game_id")
    player_id = request.args.get("player_id")
    return render_template("game.html", game_id=game_id, player_id=player_id)

@app.route("/games/<game_id>/join")
def join_page(game_id):
    return render_template("join.html", game_id=game_id)

@app.route("/create_game", methods=["POST"])
def create_game():
    game_id = uuid.uuid4().hex[:4].upper()
    game_data = {
        "id": game_id,
        "status": "lobby",
        "players": {},
        "votes": None,  # Changed to None instead of {} for clearer active vote detection
        "history": [],
        "eliminated_players": []  # Added to track eliminated players
    }
    with open(f"{DATA_DIR}/{game_id}.json", "w") as f:
        json.dump(game_data, f)
    return jsonify({"game_id": game_id})

@app.route("/join_game", methods=["POST"])
def join_game():
    data = request.get_json()
    game_id = data.get("game_id")
    player_name = data.get("name")

    if not game_id or not player_name:
        return jsonify({"error": "game_id and name required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    existing_names = [p["name"] for p in game_data["players"].values()]
    original_name = player_name
    suffix = 2
    while player_name in existing_names:
        player_name = f"{original_name} ({suffix})"
        suffix += 1

    player_id = uuid.uuid4().hex[:8]
    is_first = len(game_data["players"]) == 0

    game_data["players"][player_id] = {
        "name": player_name,
        "role": "pending",
        "vote": None,
        "ready": False,
        "is_master": is_first,
        "eliminated": False  # Added to track player elimination status
    }

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "player_id": player_id,
        "name": player_name,
        "game_id": game_id,
        "is_master": is_first
    })

@app.route("/player_ready", methods=["POST"])
def player_ready():
    data = request.get_json()
    game_id = data.get("game_id")
    player_id = data.get("player_id")

    if not game_id or not player_id:
        return jsonify({"error": "game_id and player_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    if game_data.get("status") != "lobby":
        return jsonify({"error": "game already started"}), 400

    if player_id not in game_data["players"]:
        return jsonify({"error": "player not found"}), 404

    game_data["players"][player_id]["ready"] = True

    all_ready = all(p["ready"] for p in game_data["players"].values())
    if all_ready and len(game_data["players"]) >= 3:
        game_data["status"] = "started"
        secret_word = random.choice(SECRET_WORDS)
        game_data["word"] = secret_word

        player_ids = list(game_data["players"].keys())
        impostor_id = random.choice(player_ids)
        game_data["impostorId"] = impostor_id

        for pid in player_ids:
            role = "impostor" if pid == impostor_id else "normal"
            game_data["players"][pid]["role"] = role

        random.shuffle(player_ids)
        game_data["turn_order"] = player_ids
        game_data["current_turn_index"] = 0

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({"status": "ready registered", "game_started": all_ready})

@app.route("/start_game", methods=["POST"])
def start_game():
    data = request.get_json()
    game_id = data.get("game_id")

    if not game_id:
        return jsonify({"error": "game_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    player_ids = list(game_data["players"].keys())
    if len(player_ids) < 3:
        return jsonify({"error": "at least 3 players required"}), 400

    game_data["status"] = "started"
    secret_word = random.choice(SECRET_WORDS)
    game_data["word"] = secret_word

    impostor_id = random.choice(player_ids)
    game_data["impostorId"] = impostor_id

    for pid in player_ids:
        role = "impostor" if pid == impostor_id else "normal"
        game_data["players"][pid]["role"] = role

    random.shuffle(player_ids)
    game_data["turn_order"] = player_ids
    game_data["current_turn_index"] = 0

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "status": "started",
        "impostorId": impostor_id,
        "word": secret_word
    })

@app.route("/game_state/<game_id>/<player_id>", methods=["GET"])
def game_state(game_id, player_id):
    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    players = game_data.get("players", {})
    if player_id not in players:
        return jsonify({"error": "player not found"}), 404

    # Prüfen, ob das Spiel beendet ist
    if game_data.get("status") == "finished":
        return jsonify({
            "game_status": "finished",
            "winner": game_data.get("winner", "unknown"),
            "end_reason": game_data.get("end_reason", "unknown"),
            "your_role": players[player_id]["role"],
            "word": game_data.get("word"),
            "impostor_id": game_data.get("impostorId")
        })

    # Check if player is eliminated
    if players[player_id].get("eliminated", False) or player_id in game_data.get("eliminated_players", []):
        return jsonify({
            "status": "eliminated",
            "message": "Du wurdest aus dem Spiel eliminiert!"
        })

    player = players[player_id]
    is_impostor = player["role"] == "impostor"

    # Get active players (not eliminated)
    active_players = {pid: p for pid, p in players.items()
                    if not p.get("eliminated", False) and pid not in game_data.get("eliminated_players", [])}

    # Update turn if current player is eliminated
    turn_order = game_data.get("turn_order", [])
    current_index = game_data.get("current_turn_index", 0)

    # Filter turn order to only include active players
    active_turn_order = [pid for pid in turn_order if pid in active_players]

    if not active_turn_order:
        current_player_id = None
        current_player_name = None
    else:
        # Adjust index if needed
        if current_index >= len(active_turn_order):
            current_index = current_index % len(active_turn_order)
            game_data["current_turn_index"] = current_index

            # Save the updated index
            with open(filepath, "w") as f:
                json.dump(game_data, f)

        current_player_id = active_turn_order[current_index % len(active_turn_order)]
        current_player_name = players[current_player_id]["name"] if current_player_id else None

    # Get vote information
    votes = game_data.get("votes")

    active_vote = None
    if votes:
        # Get names for initiator and suspect
        initiator_id = votes.get("initiator")
        suspect_id = votes.get("suspect")

        initiator_name = players.get(initiator_id, {}).get("name") if initiator_id else None
        suspect_name = players.get(suspect_id, {}).get("name") if suspect_id else None

        active_vote = {
            "initiator_id": initiator_id,
            "initiator_name": initiator_name,
            "suspect_id": suspect_id,
            "suspect_name": suspect_name,
            "votes": votes.get("votes", {}),
            "result": votes.get("result")
        }

    return jsonify({
        "player_name": player["name"],
        "your_role": player["role"],
        "your_word": None if is_impostor else game_data.get("word"),
        "game_status": game_data.get("status"),
        "current_player": current_player_name,
        "is_master": player.get("is_master", False),
        "history": game_data.get("history", []),
        "eliminated_players": game_data.get("eliminated_players", []),
        "active_vote": active_vote
    })

@app.route("/submit_word", methods=["POST"])
def submit_word():
    data = request.get_json()
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    word = data.get("word")

    if not game_id or not player_id or not word:
        return jsonify({"error": "game_id, player_id and word required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    if player_id not in game_data["players"]:
        return jsonify({"error": "player not found"}), 404

    # Check if player is eliminated
    if game_data["players"][player_id].get("eliminated", False) or player_id in game_data.get("eliminated_players", []):
        return jsonify({"error": "eliminated players cannot submit words"}), 403

    # Check if player is impostor and guessed the word correctly
    player_role = game_data["players"][player_id]["role"]
    secret_word = game_data.get("word", "")

    if player_role == "impostor" and word.lower() == secret_word.lower():
        # Impostor has guessed the word correctly!
        game_data["status"] = "finished"
        game_data["winner"] = "impostor"
        game_data["end_reason"] = "word_guessed"

        with open(filepath, "w") as f:
            json.dump(game_data, f)

        return jsonify({
            "status": "game_over",
            "winner": "impostor",
            "reason": "word_guessed"
        })

    current_index = game_data.get("current_turn_index", 0)
    turn_order = game_data.get("turn_order", [])

    if not turn_order:
        return jsonify({"error": "turn order missing"}), 400

    # Get active players
    active_turn_order = [pid for pid in turn_order
                        if not game_data["players"].get(pid, {}).get("eliminated", False)
                        and pid not in game_data.get("eliminated_players", [])]

    if not active_turn_order:
        return jsonify({"error": "no active players"}), 400

    # Adjust index if needed
    if current_index >= len(active_turn_order):
        current_index = current_index % len(active_turn_order)
        game_data["current_turn_index"] = current_index

    current_player_id = active_turn_order[current_index % len(active_turn_order)]

    if player_id != current_player_id:
        return jsonify({"error": "not your turn"}), 403

    game_data["history"].append({
        "player_id": player_id,
        "word": word
    })

    game_data["current_turn_index"] = (current_index + 1) % len(active_turn_order)

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({"status": "ok", "next_turn_index": game_data["current_turn_index"]})

@app.route("/players_in_game/<game_id>", methods=["GET"])
def players_in_game(game_id):
    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    players = game_data.get("players", {})
    eliminated = game_data.get("eliminated_players", [])

    simplified = [
        {
            "player_id": pid,
            "name": pdata.get("name", ""),
            "role": pdata.get("role", "pending"),
            "is_master": pdata.get("is_master", False),
            "eliminated": pdata.get("eliminated", False) or pid in eliminated
        }
        for pid, pdata in players.items()
    ]
    return jsonify({"players": simplified})

@app.route("/start_vote", methods=["POST"])
def start_vote():
    data = request.get_json()
    game_id = data.get("game_id")
    initiator_id = data.get("initiator_id")
    suspect_id = data.get("suspect_id")

    if not game_id or not initiator_id or not suspect_id:
        return jsonify({"error": "game_id, initiator_id and suspect_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    players = game_data.get("players", {})
    if initiator_id not in players or suspect_id not in players:
        return jsonify({"error": "player not found"}), 404

    # Check if there's already a vote
    if game_data.get("votes") is not None:
        return jsonify({"error": "vote already in progress"}), 400

    # Get current player
    current_index = game_data.get("current_turn_index", 0)
    turn_order = game_data.get("turn_order", [])

    # Get active players
    active_turn_order = [pid for pid in turn_order
                         if not players.get(pid, {}).get("eliminated", False)
                         and pid not in game_data.get("eliminated_players", [])]

    if not active_turn_order:
        return jsonify({"error": "no active players"}), 400

    # Adjust index if needed
    if current_index >= len(active_turn_order):
        current_index = current_index % len(active_turn_order)

    current_player_id = active_turn_order[current_index % len(active_turn_order)]

    if initiator_id != current_player_id:
        return jsonify({"error": "only current player may start a vote"}), 403

    # Get initiator and suspect names
    initiator_name = players[initiator_id]["name"]
    suspect_name = players[suspect_id]["name"]

    game_data["votes"] = {
        "initiator": initiator_id,
        "initiator_name": initiator_name,
        "suspect": suspect_id,
        "suspect_name": suspect_name,
        "votes": {},
        "result": None
    }

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "status": "vote_started",
        "suspect": suspect_id,
        "suspect_name": suspect_name,
        "initiator_name": initiator_name
    })

@app.route("/cast_vote", methods=["POST"])
def cast_vote():
    data = request.get_json()
    game_id = data.get("game_id")
    voter_id = data.get("voter_id")
    vote = data.get("vote")

    if not game_id or not voter_id or not vote:
        return jsonify({"error": "game_id, voter_id and vote required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    votes_data = game_data.get("votes")
    if not votes_data or "suspect" not in votes_data:
        return jsonify({"error": "no active vote"}), 400

    # Check if voter is suspect
    if voter_id == votes_data["suspect"]:
        return jsonify({"error": "suspect cannot vote"}), 403

    # Check if voter is eliminated
    if game_data["players"][voter_id].get("eliminated", False) or voter_id in game_data.get("eliminated_players", []):
        return jsonify({"error": "eliminated players cannot vote"}), 403

    game_data["votes"]["votes"][voter_id] = vote

    # Check if all active players have voted (except suspect)
    active_players = [pid for pid, p in game_data["players"].items()
                      if not p.get("eliminated", False)
                      and pid not in game_data.get("eliminated_players", [])
                      and pid != votes_data["suspect"]]

    all_voted = all(pid in votes_data["votes"] for pid in active_players)

    # If all have voted, process the result automatically
    if all_voted:
        votes = votes_data["votes"]
        up_votes = list(votes.values()).count("up")
        down_votes = list(votes.values()).count("down")
        suspect_id = votes_data["suspect"]
        impostor_id = game_data.get("impostorId")

        result = None
        # Majority vote to eliminate
        if up_votes > down_votes:
            # Add suspect to eliminated players
            if "eliminated_players" not in game_data:
                game_data["eliminated_players"] = []
            game_data["eliminated_players"].append(suspect_id)
            game_data["players"][suspect_id]["eliminated"] = True

            # Check if suspect was impostor
            if suspect_id == impostor_id:
                game_data["status"] = "finished"
                game_data["winner"] = "players"
                game_data["end_reason"] = "impostor_found"
                result = "impostor_eliminated"
            else:
                # Check if only impostor and one other player remain
                active_players_after_vote = [pid for pid in active_players
                                           if pid != suspect_id and
                                           pid not in game_data.get("eliminated_players", [])]

                if len(active_players_after_vote) == 1 and impostor_id in active_players_after_vote + [suspect_id]:
                    # Impostor wins if only one other player left
                    game_data["status"] = "finished"
                    game_data["winner"] = "impostor"
                    game_data["end_reason"] = "not_enough_players"
                    result = "impostor_wins"
                else:
                    result = "player_eliminated"
        else:
            result = "vote_failed"

        # Store result in vote data
        game_data["votes"]["result"] = result

        # Wait for frontend to process vote result, then clear it in next request
        if result:
            # Update the current player index to skip eliminated player
            current_index = game_data.get("current_turn_index", 0)
            turn_order = game_data.get("turn_order", [])

            # Get active players
            active_turn_order = [pid for pid in turn_order
                               if not game_data["players"].get(pid, {}).get("eliminated", False)
                               and pid not in game_data.get("eliminated_players", [])]

            if active_turn_order:
                # If the current player is not in active turn order, move to next player
                current_player_id = turn_order[current_index % len(turn_order)]
                if current_player_id not in active_turn_order or current_player_id == suspect_id:
                    # Find the next active player
                    next_index = 0
                    for i, pid in enumerate(active_turn_order):
                        if pid != suspect_id:
                            next_index = i
                            break
                    game_data["current_turn_index"] = next_index

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    # Return vote result if all have voted
    if all_voted:
        return jsonify({
            "status": "vote_completed",
            "result": result,
            "up_votes": up_votes,
            "down_votes": down_votes
        })
    else:
        return jsonify({"status": "vote_recorded"})

@app.route("/end_vote", methods=["POST"])
def end_vote():
    data = request.get_json()
    game_id = data.get("game_id")

    if not game_id:
        return jsonify({"error": "game_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    # Check if there is a vote with result
    if not game_data.get("votes") or not game_data["votes"].get("result"):
        return jsonify({"error": "no completed vote to end"}), 400

    # Set a flag to hide the overlay for all players
    game_data["votes"]["overlay_hidden"] = True

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({"status": "vote_ending"})

@app.route("/clear_vote", methods=["POST"])
def clear_vote():
    """Completely clear the vote and remove it from the game data."""
    data = request.get_json()
    game_id = data.get("game_id")

    if not game_id:
        return jsonify({"error": "game_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    # Clear the vote
    game_data["votes"] = None

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({"status": "vote_cleared"})

@app.route("/vote_status/<game_id>/<player_id>", methods=["GET"])
def vote_status(game_id, player_id):
    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    votes = game_data.get("votes")

    if not votes or "suspect" not in votes or not votes.get("suspect"):
        return jsonify({"active": False})

    # Count votes
    vote_counts = {"up": 0, "down": 0}
    for v in votes.get("votes", {}).values():
        if v in vote_counts:
            vote_counts[v] += 1

    return jsonify({
        "active": True,
        "initiator_id": votes.get("initiator"),
        "initiator_name": votes.get("initiator_name", "???"),
        "suspect_id": votes.get("suspect"),
        "suspect_name": votes.get("suspect_name", "???"),
        "already_voted": player_id in votes.get("votes", {}),
        "votes": vote_counts,
        "result": votes.get("result")
    })

@app.route("/reveal_vote", methods=["POST"])
def reveal_vote():
    data = request.get_json()
    game_id = data.get("game_id")

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    votes = game_data.get("votes", {})
    if not votes or "votes" not in votes:
        return jsonify({"error": "no active vote"}), 400

    vote_list = votes.get("votes", {})
    up = list(vote_list.values()).count("up")
    down = list(vote_list.values()).count("down")
    suspect = votes.get("suspect")
    impostor_id = game_data.get("impostorId")

    result = "no_consensus"
    if up > down:
        # Mark player as eliminated
        if suspect not in game_data.get("eliminated_players", []):
            if "eliminated_players" not in game_data:
                game_data["eliminated_players"] = []
            game_data["eliminated_players"].append(suspect)
            game_data["players"][suspect]["eliminated"] = True

        if suspect == impostor_id:
            game_data["status"] = "finished"
            game_data["winner"] = "players"
            game_data["end_reason"] = "impostor_found"
            result = "impostor_eliminated"
        else:
            # Check if only impostor and one other player remain
            active_players = [pid for pid, p in game_data["players"].items()
                             if not p.get("eliminated", False) and
                             pid not in game_data.get("eliminated_players", [])]

            if len(active_players) == 2 and impostor_id in active_players:
                # Impostor wins if only one other player left
                game_data["status"] = "finished"
                game_data["winner"] = "impostor"
                game_data["end_reason"] = "not_enough_players"
                result = "impostor_wins"
            else:
                result = "player_eliminated"

    # Store result
    game_data["votes"]["result"] = result

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "result": result,
        "votes": vote_list,
        "up_votes": up,
        "down_votes": down
    })

@app.route("/end_game", methods=["POST"])
def end_game():
    data = request.get_json()
    game_id = data.get("game_id")
    winner = data.get("winner", "unknown")  # "impostor" oder "players"
    reason = data.get("reason", "unknown")  # "impostor_found", "not_enough_players", etc.

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    game_data["status"] = "finished"
    game_data["winner"] = winner
    game_data["end_reason"] = reason

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "status": "game_ended",
        "winner": winner,
        "reason": reason
    })

@app.route("/restart_game", methods=["POST"])
def restart_game():
    data = request.get_json()
    game_id = data.get("game_id")

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    for pid in game_data["players"]:
        game_data["players"][pid]["role"] = "pending"
        game_data["players"][pid]["vote"] = None
        game_data["players"][pid]["ready"] = False
        game_data["players"][pid]["eliminated"] = False

    game_data["status"] = "lobby"
    game_data["word"] = None
    game_data["votes"] = None
    game_data["history"] = []
    game_data["eliminated_players"] = []

    # Remove game end data
    if "winner" in game_data:
        del game_data["winner"]
    if "end_reason" in game_data:
        del game_data["end_reason"]

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({"status": "restarted"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)