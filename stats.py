# stats.py - Erweitert um Timeline und Cleanup Integration

import json
import os
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import time

def load_all_games():
    """Lädt alle Spiel-JSONs aus dem /games Verzeichnis"""
    # FIX: Absoluter Pfad basierend auf dem app.py Verzeichnis
    base_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir = os.path.join(base_dir, "games")

    print(f"[DEBUG] Looking for games in: {games_dir}")  # Debug-Info

    all_games = []

    if not os.path.exists(games_dir):
        print(f"[DEBUG] Games directory does not exist: {games_dir}")
        return []

    files = [f for f in os.listdir(games_dir) if f.endswith('.json')]
    print(f"[DEBUG] Found {len(files)} JSON files")  # Debug-Info

    for filename in files:
        try:
            filepath = os.path.join(games_dir, filename)
            with open(filepath, 'r') as f:
                game_data = json.load(f)
                game_data['filename'] = filename
                game_data['filepath'] = filepath  # Für Timeline-Analyse
                all_games.append(game_data)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

    print(f"[DEBUG] Loaded {len(all_games)} games successfully")  # Debug-Info
    return all_games

def get_file_creation_date(filepath):
    """Gibt das Erstellungsdatum einer Datei zurück"""
    try:
        # Verwende das frühere Datum zwischen creation und modification
        created = os.path.getctime(filepath)
        modified = os.path.getmtime(filepath)
        return min(created, modified)
    except:
        return time.time()

def calculate_timeline_stats(all_games, days=30):
    """Berechnet Timeline-Statistiken für die letzten X Tage"""

    # Basis-Daten vorbereiten
    now = datetime.now()
    date_counts = defaultdict(lambda: {"total": 0, "finished": 0, "started": 0, "abandoned": 0})

    # Letzte X Tage initialisieren
    for i in range(days):
        date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        date_counts[date] = {"total": 0, "finished": 0, "started": 0, "abandoned": 0}

    for game in all_games:
        try:
            # Datum des Spiels bestimmen
            filepath = game.get('filepath')
            if filepath:
                game_date = get_file_creation_date(filepath)
            else:
                game_date = time.time()  # Fallback

            game_date_str = datetime.fromtimestamp(game_date).strftime('%Y-%m-%d')

            # Nur Spiele der letzten X Tage berücksichtigen
            game_datetime = datetime.fromtimestamp(game_date)
            days_ago = (now - game_datetime).days

            if days_ago <= days:
                status = game.get('status', 'unknown')
                end_reason = game.get('end_reason', '')

                date_counts[game_date_str]["total"] += 1

                if status == 'finished':
                    if end_reason == 'game_abandoned':
                        date_counts[game_date_str]["abandoned"] += 1
                    else:
                        date_counts[game_date_str]["finished"] += 1
                elif status in ['lobby', 'started']:
                    date_counts[game_date_str]["started"] += 1

        except Exception as e:
            continue

    # Timeline-Daten vorbereiten
    timeline_data = []

    for i in range(days - 1, -1, -1):  # Rückwärts für chronologische Reihenfolge
        date = now - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        weekday = date.strftime('%a')  # Mo, Di, Mi, etc.
        display_date = date.strftime('%d.%m')  # 15.05

        stats = date_counts.get(date_str, {"total": 0, "finished": 0, "started": 0, "abandoned": 0})

        timeline_data.append({
            "date": date_str,
            "display_date": display_date,
            "weekday": weekday,
            "total_games": stats["total"],
            "finished_games": stats["finished"],
            "active_games": stats["started"],
            "abandoned_