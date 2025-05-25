#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template, send_from_directory
import uuid
import os
import json
import random
import time

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

# ===== CACHE-BUSTING FUNKTIONEN =====

def get_app_version():
    """Gibt die aktuelle App-Version zurück"""
    try:
        with open(os.path.join(BASE_DIR, 'static', 'version_manifest.json'), 'r') as f:
            manifest = json.load(f)
        return manifest.get('global_version', '1')
    except:
        return str(int(time.time()))[:8]

def get_versioned_static_url(asset_path):
    """Gibt versionierte URL für statische Assets zurück"""
    try:
        with open(os.path.join(BASE_DIR, 'static', 'version_manifest.json'), 'r') as f:
            manifest = json.load(f)

        clean_path = asset_path.lstrip('/')
        if clean_path in manifest.get("files", {}):
            return f"/{manifest['files'][clean_path]['versioned_path']}"
        else:
            version = manifest.get("global_version", "1")
            return f"/{asset_path}?v={version}"
    except:
        return f"/{asset_path}?v={get_app_version()}"

def get_build_time():
    """Gibt Build-Zeit zurück"""
    try:
        with open(os.path.join(BASE_DIR, 'static', 'version_manifest.json'), 'r') as f:
            manifest = json.load(f)
        return manifest.get('build_time', 'unknown')
    except:
        return time.strftime('%Y-%m-%dT%H:%M:%S')

# ===== HELPER FUNCTIONS FOR VOTING SYSTEM =====

def check_vote_timeout(game_data):
    """Prüft ob Vote abgelaufen ist und beendet es automatisch"""
    votes = game_data.get("votes")
    if not votes or votes.get("status") != "active":
        return False

    elapsed = time.time() - votes.get("started_at", 0)
    if elapsed >= votes.get("duration", 30):
        # Vote automatisch beenden
        process_vote_result(game_data)
        votes["status"] = "completed"
        return True
    return False

def process_vote_result(game_data):
    """Berechnet das Vote-Ergebnis nach Ablauf der Zeit"""
    votes_data = game_data["votes"]
    vote_counts = {"up": 0, "down": 0}

    for vote in votes_data["votes"].values():
        if vote in vote_counts:
            vote_counts[vote] += 1

    # Ergebnis in votes_data speichern
    votes_data["up_votes"] = vote_counts["up"]
    votes_data["down_votes"] = vote_counts["down"]

    # Ergebnis bestimmen
    if vote_counts["up"] > vote_counts["down"]:
        # Spieler eliminieren
        suspect_id = votes_data["suspect"]
        if suspect_id not in game_data.get("eliminated_players", []):
            if "eliminated_players" not in game_data:
                game_data["eliminated_players"] = []
            game_data["eliminated_players"].append(suspect_id)
            game_data["players"][suspect_id]["eliminated"] = True

        # Spiel-Ende prüfen
        if suspect_id == game_data.get("impostorId"):
            game_data["status"] = "finished"
            game_data["winner"] = "players"
            game_data["end_reason"] = "impostor_found"
            votes_data["result"] = "impostor_eliminated"
        else:
            # Prüfen ob nur noch Impostor + 1 Spieler übrig
            active_players = [pid for pid, p in game_data["players"].items()
                            if not p.get("eliminated", False) and
                            pid not in game_data.get("eliminated_players", [])]

            # Check if impostor is still in game
            impostor_id = game_data.get("impostorId")
            impostor_still_in_game = (impostor_id in active_players)

            if impostor_still_in_game and len(active_players) <= 2:
                game_data["status"] = "finished"
                game_data["winner"] = "impostor"
                game_data["end_reason"] = "not_enough_players"
                votes_data["result"] = "impostor_wins"
            else:
                votes_data["result"] = "player_eliminated"
                # Update turn order if needed
                update_turn_after_elimination(game_data, suspect_id)
    else:
        votes_data["result"] = "vote_failed"

def update_turn_after_elimination(game_data, eliminated_player_id):
    """Aktualisiert die Spielreihenfolge nach einer Elimination"""
    current_index = game_data.get("current_turn_index", 0)
    turn_order = game_data.get("turn_order", [])

    # Get updated active players after elimination
    active_turn_order = [pid for pid in turn_order
                       if not game_data["players"].get(pid, {}).get("eliminated", False)
                       and pid not in game_data.get("eliminated_players", [])]

    if active_turn_order:
        # Get the current player
        if current_index < len(turn_order):
            current_player_id = turn_order[current_index]
        else:
            current_player_id = turn_order[0] if turn_order else None

        # If current player was eliminated or is no longer in active turn order
        if current_player_id not in active_turn_order or current_player_id == eliminated_player_id:
            # Find the index of the current player in the original turn order
            current_idx_in_original = -1
            for i, pid in enumerate(turn_order):
                if pid == current_player_id:
                    current_idx_in_original = i
                    break

            # Find the next active player in the turn order
            next_idx_in_original = (current_idx_in_original + 1) % len(turn_order)
            attempts = 0
            while attempts < len(turn_order):
                next_player_id = turn_order[next_idx_in_original]
                if next_player_id in active_turn_order:
                    game_data["current_turn_index"] = next_idx_in_original
                    break
                next_idx_in_original = (next_idx_in_original + 1) % len(turn_order)
                attempts += 1

# ===== STATIC ROUTES =====

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/static/<path:filename>')
def versioned_static(filename):
    """Serviert statische Dateien mit Cache-Headers"""
    try:
        response = send_from_directory('static', filename)

        # Aggressive Caching für versionierte Assets
        if request.args.get('v'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 Jahr
            response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        else:
            # Kurzes Caching für unverlierte Assets
            response.headers['Cache-Control'] = 'public, max-age=300'  # 5 Minuten

        return response
    except Exception as e:
        print(f"Static file error: {e}")
        return "File not found", 404

@app.route('/version')
def version_info():
    """API Endpoint für Version-Informationen"""
    try:
        with open(os.path.join(BASE_DIR, 'static', 'version_manifest.json'), 'r') as f:
            manifest = json.load(f)
        return jsonify({
            "version": manifest.get("global_version"),
            "build_time": manifest.get("build_time"),
            "build_timestamp": manifest.get("build_timestamp")
        })
    except:
        return jsonify({
            "version": get_app_version(),
            "build_time": get_build_time(),
            "build_timestamp": int(time.time())
        })

# ===== TEMPLATE ROUTES =====

@app.route("/")
def landing_page():
    return render_template("index.html",
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/ui")
def test_ui():
    return render_template("test_ui.html",
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/create")
def create_game_ui():
    return render_template("create_game.html",
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/game")
def game():
    game_id = request.args.get("game_id")
    player_id = request.args.get("player_id")
    return render_template("game.html",
                         game_id=game_id,
                         player_id=player_id,
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/game_ended")
def game_ended():
    game_id = request.args.get("game_id")
    player_id = request.args.get("player_id")
    result = request.args.get("result")
    winner = request.args.get("winner")
    word = request.args.get("word")
    is_impostor = request.args.get("is_impostor")
    return render_template("game_ended.html",
                         game_id=game_id,
                         player_id=player_id,
                         result=result,
                         winner=winner,
                         word=word,
                         is_impostor=is_impostor,
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/games/<game_id>/join")
def join_page(game_id):
    return render_template("join.html",
                         game_id=game_id,
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

@app.route("/join")
def join_page_general():
    return render_template("join.html",
                         game_id=None,  # Kein Game-ID
                         app_version=get_app_version(),
                         versioned_url=get_versioned_static_url,
                         build_time=get_build_time())

# ===== DEBUG ROUTES =====

@app.route("/debug")
def debug_versioning():
    """Debug Route um versioned_url zu testen"""
    test_results = {}

    try:
        test_results["versioned_url_function"] = get_versioned_static_url("static/css/game.css")
        test_results["app_version"] = get_app_version()
        test_results["manifest_exists"] = os.path.exists(os.path.join(BASE_DIR, 'static', 'version_manifest.json'))

        # Test alle Assets
        test_results["all_assets"] = {}
        for asset in ["static/css/game.css", "static/js/game.js", "static/suswords.png"]:
            test_results["all_assets"][asset] = get_versioned_static_url(asset)

        test_results["status"] = "success"

    except Exception as e:
        test_results["error"] = str(e)
        test_results["status"] = "error"

    return jsonify(test_results)

@app.route("/debug_template")
def debug_template():
    """Debug Template mit direkter Variable-Übergabe"""
    app_version = get_app_version()

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug versioned_url</title>
        <meta name="app-version" content="{app_version}">
        <link rel="stylesheet" href="{get_versioned_static_url('static/css/game.css')}">
    </head>
    <body>
        <h1>Debug versioned_url</h1>
        <p>App Version: {app_version}</p>
        <p>CSS URL: {get_versioned_static_url('static/css/game.css')}</p>
        <p>JS URL: {get_versioned_static_url('static/js/game.js')}</p>
        <p>Image URL: {get_versioned_static_url('static/suswords.png')}</p>

        <script>
            console.log('Meta app-version:', document.querySelector('meta[name="app-version"]')?.content);
            console.log('CSS URL from link:', document.querySelector('link[rel="stylesheet"]')?.href);
        </script>
    </body>
    </html>
    '''

# ===== GAME API ROUTES =====

@app.route("/create_game", methods=["POST"])
def create_game():
    game_id = uuid.uuid4().hex[:4].upper()
    game_data = {
        "id": game_id,
        "status": "lobby",
        "players": {},
        "votes": None,
        "history": [],
        "eliminated_players": []
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
        "eliminated": False
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

    # Check for vote timeout before processing
    vote_timeout_occurred = check_vote_timeout(game_data)
    if vote_timeout_occurred:
        with open(filepath, "w") as f:
            json.dump(game_data, f)

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
            "impostor_id": game_data.get("impostorId"),
            "history": game_data.get("history", []),
            "eliminated_players": game_data.get("eliminated_players", [])
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
            "result": votes.get("result"),
            "status": votes.get("status", "active"),
            "started_at": votes.get("started_at"),
            "duration": votes.get("duration", 30),
            "up_votes": votes.get("up_votes", 0),
            "down_votes": votes.get("down_votes", 0)
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

# ===== VOTING SYSTEM ROUTES =====

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

    # Check if suspect is already eliminated
    if players.get(suspect_id, {}).get("eliminated", False) or suspect_id in game_data.get("eliminated_players", []):
        return jsonify({"error": "player already eliminated"}), 400

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

    # Create NEW vote structure with timing
    game_data["votes"] = {
        "initiator": initiator_id,
        "initiator_name": initiator_name,
        "suspect": suspect_id,
        "suspect_name": suspect_name,
        "votes": {},
        "result": None,
        "started_at": time.time(),  # Unix timestamp for timing
        "duration": 30,  # 30 seconds voting time
        "status": "active",  # active, completed, revealed
        "up_votes": 0,
        "down_votes": 0
    }

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "status": "vote_started",
        "suspect": suspect_id,
        "suspect_name": suspect_name,
        "initiator_name": initiator_name,
        "duration": 30
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

    # Check for timeout first
    vote_timeout_occurred = check_vote_timeout(game_data)
    if vote_timeout_occurred:
        with open(filepath, "w") as f:
            json.dump(game_data, f)
        return jsonify({"error": "vote has timed out"}), 400

    votes_data = game_data.get("votes")
    if not votes_data or votes_data.get("status") != "active":
        return jsonify({"error": "no active vote"}), 400

    # Check if voter is suspect
    if voter_id == votes_data["suspect"]:
        return jsonify({"error": "suspect cannot vote"}), 403

    # Check if voter is eliminated
    if game_data["players"][voter_id].get("eliminated", False) or voter_id in game_data.get("eliminated_players", []):
        return jsonify({"error": "eliminated players cannot vote"}), 403

    # Check if already voted
    if voter_id in votes_data["votes"]:
        return jsonify({"error": "player has already voted"}), 403

    # Record the vote (but don't process result until timeout)
    game_data["votes"]["votes"][voter_id] = vote

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    # Return simple confirmation - no live results
    return jsonify({
        "status": "vote_recorded",
        "message": "Vote recorded successfully"
    })

@app.route("/vote_time_remaining/<game_id>", methods=["GET"])
def vote_time_remaining(game_id):
    """Gibt verbleibende Voting-Zeit zurück"""
    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    votes = game_data.get("votes")
    if not votes or votes.get("status") != "active":
        return jsonify({"active": False})

    elapsed = time.time() - votes.get("started_at", 0)
    remaining = max(0, votes.get("duration", 30) - elapsed)

    # Auto-beenden wenn Zeit abgelaufen
    if remaining <= 0:
        vote_timeout_occurred = check_vote_timeout(game_data)
        if vote_timeout_occurred:
            with open(filepath, "w") as f:
                json.dump(game_data, f)

    return jsonify({
        "active": remaining > 0,
        "remaining_seconds": int(remaining),
        "total_duration": votes.get("duration", 30),
        "votes_cast": len(votes.get("votes", {})),
        "status": votes.get("status", "active")
    })

@app.route("/vote_status/<game_id>/<player_id>", methods=["GET"])
def vote_status(game_id, player_id):
    """Enhanced API endpoint for checking vote status - now includes completed results"""
    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    # Check for timeout
    vote_timeout_occurred = check_vote_timeout(game_data)
    if vote_timeout_occurred:
        with open(filepath, "w") as f:
            json.dump(game_data, f)

    votes = game_data.get("votes")

    if not votes or "suspect" not in votes or not votes.get("suspect"):
        return jsonify({"active": False})

    # Count active players who can vote
    active_players = [pid for pid, p in game_data["players"].items()
                      if not p.get("eliminated", False)
                      and pid not in game_data.get("eliminated_players", [])
                      and pid != votes.get("suspect")]
    votes_needed = len(active_players)
    votes_cast = len(votes.get("votes", {}))

    # Check if the requesting player can vote
    can_vote = (
        player_id in active_players and
        player_id not in votes.get("votes", {}) and
        player_id != votes.get("suspect") and
        votes.get("status") == "active"
    )

    # Also return player names for all voters for better UI display
    voter_names = {}
    for voter_id, vote_value in votes.get("votes", {}).items():
        voter_name = game_data["players"].get(voter_id, {}).get("name", "Unknown")
        voter_names[voter_id] = {
            "name": voter_name,
            "vote": vote_value
        }

    # Calculate remaining time
    elapsed = time.time() - votes.get("started_at", 0)
    remaining = max(0, votes.get("duration", 30) - elapsed)

    # Additional data for game status display
    response_data = {
        "active": votes.get("status") in ["active", "completed"],
        "initiator_id": votes.get("initiator"),
        "initiator_name": votes.get("initiator_name", "???"),
        "suspect_id": votes.get("suspect"),
        "suspect_name": votes.get("suspect_name", "???"),
        "already_voted": player_id in votes.get("votes", {}),
        "can_vote": can_vote,
        "votes_cast": votes_cast,
        "votes_needed": votes_needed,
        "voters": voter_names,
        "result": votes.get("result"),
        "status": votes.get("status", "active"),
        "remaining_seconds": int(remaining),
        "up_votes": votes.get("up_votes", 0),
        "down_votes": votes.get("down_votes", 0)
    }

    # Include extra game status info for better end screens if a result is available
    if votes.get("result") and votes.get("status") == "completed":
        suspect_id = votes.get("suspect")
        impostor_id = game_data.get("impostorId")

        # Add additional info based on result type
        if votes.get("result") == "impostor_eliminated":
            response_data["game_status"] = "finished"
            response_data["winner"] = "players"
            response_data["end_reason"] = "impostor_found"
            response_data["secret_word"] = game_data.get("word")
            response_data["eliminated_player"] = {
                "id": suspect_id,
                "name": game_data["players"][suspect_id]["name"],
                "was_impostor": True
            }
        elif votes.get("result") == "impostor_wins":
            response_data["game_status"] = "finished"
            response_data["winner"] = "impostor"
            response_data["end_reason"] = "not_enough_players"
            response_data["secret_word"] = game_data.get("word")
        elif votes.get("result") == "player_eliminated":
            response_data["eliminated_player"] = {
                "id": suspect_id,
                "name": game_data["players"][suspect_id]["name"],
                "was_impostor": False
            }
            # Check if player is impostor to show correct message
            response_data["is_player_impostor"] = (player_id == impostor_id)

    return jsonify(response_data)

@app.route("/clear_vote", methods=["POST"])
def clear_vote():
    """Completely clear the vote and remove it from the game data"""
    data = request.get_json()
    game_id = data.get("game_id")

    if not game_id:
        return jsonify({"error": "game_id required"}), 400

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    try:
        with open(filepath, "r") as f:
            game_data = json.load(f)

        # Clear the vote
        game_data["votes"] = None

        with open(filepath, "w") as f:
            json.dump(game_data, f)

        return jsonify({"status": "vote_cleared"})
    except Exception as e:
        return jsonify({"error": f"Failed to clear vote: {str(e)}"}), 500

# ===== LEGACY VOTING ROUTES (for backwards compatibility) =====

@app.route("/end_vote", methods=["POST"])
def end_vote():
    """Legacy endpoint - now just clears the vote"""
    return clear_vote()

@app.route("/reveal_vote", methods=["POST"])
def reveal_vote():
    """Legacy endpoint - forces vote completion"""
    data = request.get_json()
    game_id = data.get("game_id")

    filepath = f"{DATA_DIR}/{game_id}.json"
    if not os.path.exists(filepath):
        return jsonify({"error": "game not found"}), 404

    with open(filepath, "r") as f:
        game_data = json.load(f)

    votes = game_data.get("votes")
    if not votes or "votes" not in votes:
        return jsonify({"error": "no active vote"}), 400

    # Force process the result
    process_vote_result(game_data)
    game_data["votes"]["status"] = "completed"

    with open(filepath, "w") as f:
        json.dump(game_data, f)

    return jsonify({
        "result": votes.get("result", "no_consensus"),
        "votes": votes.get("votes", {}),
        "up_votes": votes.get("up_votes", 0),
        "down_votes": votes.get("down_votes", 0)
    })

# ===== GAME MANAGEMENT ROUTES =====

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
    # Version Manifest bei Entwicklung automatisch erstellen
    if not os.path.exists(os.path.join(BASE_DIR, 'static', 'version_manifest.json')):
        print("🔄 Erstelle Version Manifest...")
        try:
            from cache_busting import create_version_manifest
            create_version_manifest()
        except ImportError:
            print("⚠️  cache_busting.py nicht gefunden, aber Cache-Busting funktioniert trotzdem")

    app.run(debug=True, host="0.0.0.0", port=5000)