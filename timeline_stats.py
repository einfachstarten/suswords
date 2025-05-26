# timeline_stats.py - Timeline Statistics für SusWords

import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter

def get_file_creation_date(filepath):
    """Gibt das Erstellungsdatum einer Datei zurück"""
    try:
        # Verwende das frühere Datum zwischen creation und modification
        created = os.path.getctime(filepath)
        modified = os.path.getmtime(filepath)
        return min(created, modified)
    except:
        return time.time()

def calculate_timeline_stats(games_data, days=30):
    """Berechnet Timeline-Statistiken für die letzten X Tage"""

    # Basis-Daten vorbereiten
    now = datetime.now()
    date_counts = defaultdict(lambda: {"total": 0, "finished": 0, "started": 0, "abandoned": 0})

    # Letzte X Tage initialisieren
    for i in range(days):
        date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        date_counts[date] = {"total": 0, "finished": 0, "started": 0, "abandoned": 0}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir = os.path.join(base_dir, "games")

    if not os.path.exists(games_dir):
        return prepare_timeline_response(date_counts, days)

    files = [f for f in os.listdir(games_dir) if f.endswith('.json')]

    for filename in files:
        filepath = os.path.join(games_dir, filename)

        try:
            with open(filepath, 'r') as f:
                game_data = json.load(f)

            # Datum des Spiels bestimmen
            game_date = get_file_creation_date(filepath)
            game_date_str = datetime.fromtimestamp(game_date).strftime('%Y-%m-%d')

            # Nur Spiele der letzten X Tage berücksichtigen
            game_datetime = datetime.fromtimestamp(game_date)
            days_ago = (now - game_datetime).days

            if days_ago <= days:
                status = game_data.get('status', 'unknown')
                end_reason = game_data.get('end_reason', '')

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

    return prepare_timeline_response(date_counts, days)

def prepare_timeline_response(date_counts, days):
    """Bereitet die Timeline-Response für Frontend vor"""
    now = datetime.now()

    # Sortierte Liste der letzten X Tage (älteste zuerst)
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
            "abandoned_games": stats["abandoned"],
            "is_today": date.date() == now.date(),
            "is_weekend": date.weekday() >= 5  # Samstag=5, Sonntag=6
        })

    # Zusätzliche Statistiken
    total_games = sum(day["total_games"] for day in timeline_data)
    max_games = max(day["total_games"] for day in timeline_data) if timeline_data else 1
    avg_games = total_games / days if days > 0 else 0

    # Trends berechnen
    if len(timeline_data) >= 7:
        recent_week = sum(day["total_games"] for day in timeline_data[-7:])
        previous_week = sum(day["total_games"] for day in timeline_data[-14:-7]) if len(timeline_data) >= 14 else recent_week

        if previous_week > 0:
            trend_percent = ((recent_week - previous_week) / previous_week) * 100
        else:
            trend_percent = 0 if recent_week == 0 else 100
    else:
        trend_percent = 0

    # Wochentag-Statistiken
    weekday_stats = defaultdict(int)
    for day in timeline_data:
        weekday_stats[day["weekday"]] += day["total_games"]

    return {
        "timeline_data": timeline_data,
        "summary": {
            "total_games": total_games,
            "max_games_per_day": max_games,
            "avg_games_per_day": round(avg_games, 1),
            "days_analyzed": days,
            "trend_percent": round(trend_percent, 1),
            "trend_direction": "up" if trend_percent > 5 else "down" if trend_percent < -5 else "stable"
        },
        "weekday_stats": dict(weekday_stats),
        "peak_day": max(timeline_data, key=lambda x: x["total_games"], default={"display_date": "N/A", "total_games": 0})
    }

# Integration in stats.py
def update_stats_with_timeline():
    """Aktualisiert die Stats-Funktionen um Timeline-Features"""

    def calculate_timeline_stats_updated(finished_games):
        """Erweiterte Timeline-Statistiken"""
        return calculate_timeline_stats(finished_games, days=30)

    return calculate_timeline_stats_updated

# Flask Route für Timeline API
def add_timeline_routes_to_app(app):
    """Fügt Timeline-Routes zur Flask-App hinzu"""

    @app.route("/api/timeline")
    def timeline_api():
        """Timeline API für die letzten 30 Tage"""
        try:
            days = int(request.args.get('days', 30))
            days = min(max(days, 7), 90)  # Zwischen 7 und 90 Tagen

            timeline_stats = calculate_timeline_stats([], days)
            return jsonify(timeline_stats)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/timeline/<int:days>")
    def timeline_api_days(days):
        """Timeline API für spezifische Anzahl Tage"""
        try:
            days = min(max(days, 7), 90)  # Zwischen 7 und 90 Tagen
            timeline_stats = calculate_timeline_stats([], days)
            return jsonify(timeline_stats)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Test der Timeline-Funktionen
    print("📈 SusWords Timeline Statistics Test")
    print("=" * 50)

    stats = calculate_timeline_stats([], 30)
    print(f"📊 Letzten 30 Tage:")
    print(f"   Spiele gesamt: {stats['summary']['total_games']}")
    print(f"   Max. pro Tag: {stats['summary']['max_games_per_day']}")
    print(f"   Durchschnitt: {stats['summary']['avg_games_per_day']}")
    print(f"   Trend: {stats['summary']['trend_direction']} ({stats['summary']['trend_percent']:+.1f}%)")

    print(f"\n📅 Letzte 7 Tage:")
    for day in stats['timeline_data'][-7:]:
        print(f"   {day['display_date']} ({day['weekday']}): {day['total_games']} Spiele")

    print(f"\n🏆 Peak Tag: {stats['peak_day']['display_date']} mit {stats['peak_day']['total_games']} Spielen")