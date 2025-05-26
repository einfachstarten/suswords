import os
import json
import time
from config import DATA_DIR

def ensure_data_dir():
    """Stellt sicher, dass das Daten-Verzeichnis existiert"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def game_exists(game_id):
    """Prüft ob ein Spiel existiert"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"{game_id}.json")
    return os.path.exists(filepath)

def load_game(game_id):
    """Lädt Spieldaten aus JSON-Datei"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"{game_id}.json")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Game {game_id} not found")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in game {game_id}: {e}")
    except Exception as e:
        raise IOError(f"Error reading game {game_id}: {e}")

def save_game(game_id, game_data):
    """Speichert Spieldaten in JSON-Datei"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"{game_id}.json")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(game_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise IOError(f"Error saving game {game_id}: {e}")

def load_game_safe(game_id):
    """Lädt Spieldaten mit Fehlerbehandlung - gibt None zurück bei Fehlern"""
    try:
        return load_game(game_id)
    except Exception as e:
        print(f"Warning: Could not load game {game_id}: {e}")
        return None

def save_game_safe(game_id, game_data):
    """Speichert Spieldaten mit Fehlerbehandlung"""
    try:
        save_game(game_id, game_data)
        return True
    except Exception as e:
        print(f"Error: Could not save game {game_id}: {e}")
        return False

def delete_game(game_id):
    """Löscht eine Spiel-Datei"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"{game_id}.json")

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            print(f"Error deleting game {game_id}: {e}")
            return False
    return False

def list_all_games():
    """Gibt alle Spiel-IDs zurück"""
    ensure_data_dir()
    games = []

    try:
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.json'):
                game_id = filename[:-5]  # Remove .json
                games.append(game_id)
    except Exception as e:
        print(f"Error listing games: {e}")

    return games

def load_all_games():
    """Lädt alle Spiele für Stats/Cleanup"""
    games = []

    for game_id in list_all_games():
        game_data = load_game_safe(game_id)
        if game_data:
            games.append(game_data)

    return games

def get_game_file_age(game_id):
    """Gibt das Alter einer Spiel-Datei in Stunden zurück"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"{game_id}.json")

    if not os.path.exists(filepath):
        return None

    try:
        file_time = os.path.getmtime(filepath)
        current_time = time.time()
        age_hours = (current_time - file_time) / 3600
        return age_hours
    except Exception:
        return None

def get_games_by_age():
    """Kategorisiert Spiele nach Alter"""
    games_by_age = {
        '<1h': [],
        '1-6h': [],
        '6-24h': [],
        '>24h': []
    }

    for game_id in list_all_games():
        age = get_game_file_age(game_id)
        if age is None:
            continue

        if age < 1:
            games_by_age['<1h'].append(game_id)
        elif age < 6:
            games_by_age['1-6h'].append(game_id)
        elif age < 24:
            games_by_age['6-24h'].append(game_id)
        else:
            games_by_age['>24h'].append(game_id)

    return games_by_age

def cleanup_old_games(hours_threshold=24, dry_run=True):
    """Bereinigt alte Spiele"""
    cleaned_games = []

    for game_id in list_all_games():
        age = get_game_file_age(game_id)
        if age is None or age <= hours_threshold:
            continue

        game_data = load_game_safe(game_id)
        if not game_data:
            continue

        # Nur unfertige Spiele bereinigen
        if game_data.get('status') in ['finished', 'abandoned']:
            continue

        if dry_run:
            cleaned_games.append({
                'game_id': game_id,
                'age_hours': age,
                'status': game_data.get('status', 'unknown')
            })
        else:
            # Spiel als abandoned markieren
            game_data['status'] = 'finished'
            game_data['end_reason'] = 'game_abandoned'
            game_data['winner'] = 'abandoned'

            if save_game_safe(game_id, game_data):
                cleaned_games.append({
                    'game_id': game_id,
                    'age_hours': age,
                    'status': 'cleaned'
                })

    return cleaned_games

# Backwards compatibility - alte Funktionen die in app.py verwendet werden
def get_filepath(game_id):
    """Gibt den Dateipfad für eine Game-ID zurück (backwards compatibility)"""
    ensure_data_dir()
    return os.path.join(DATA_DIR, f"{game_id}.json")

if __name__ == "__main__":
    # Test der File Manager Funktionen
    print("🧪 Testing File Manager...")

    # Test data directory
    ensure_data_dir()
    print(f"✅ Data directory: {DATA_DIR}")

    # Test game operations
    test_game_id = "TEST"
    test_data = {
        "id": test_game_id,
        "status": "test",
        "players": {},
        "created_at": time.time()
    }

    # Save test game
    if save_game_safe(test_game_id, test_data):
        print(f"✅ Test game saved: {test_game_id}")

    # Load test game
    loaded_data = load_game_safe(test_game_id)
    if loaded_data and loaded_data['id'] == test_game_id:
        print(f"✅ Test game loaded: {test_game_id}")

    # List games
    all_games = list_all_games()
    print(f"✅ Found {len(all_games)} games")

    # Clean up test
    if delete_game(test_game_id):
        print(f"✅ Test game deleted: {test_game_id}")

    print("🎯 File Manager tests completed!")