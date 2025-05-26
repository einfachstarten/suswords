# cleanup.py - Game Cleanup System für SusWords

import json
import os
import time
from datetime import datetime, timedelta

def get_file_last_modified(filepath):
    """Gibt das letzte Änderungsdatum einer Datei zurück"""
    try:
        return os.path.getmtime(filepath)
    except:
        return 0

def is_game_abandoned(game_data, filepath, hours_threshold=24):
    """Prüft ob ein Spiel als abandoned gilt"""
    # Nur aktive Spiele prüfen (lobby oder started)
    status = game_data.get('status', 'unknown')
    if status not in ['lobby', 'started']:
        return False

    # Letzte Änderung der Datei prüfen
    last_modified = get_file_last_modified(filepath)
    hours_since_modified = (time.time() - last_modified) / 3600

    return hours_since_modified > hours_threshold

def cleanup_abandoned_games(dry_run=True, hours_threshold=24):
    """
    Bereinigt abandoned Spiele

    Args:
        dry_run: Wenn True, nur anzeigen was passieren würde
        hours_threshold: Stunden ohne Aktivität bevor Spiel als abandoned gilt
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir = os.path.join(base_dir, "games")

    if not os.path.exists(games_dir):
        print(f"❌ Games Verzeichnis nicht gefunden: {games_dir}")
        return

    print(f"🧹 Game Cleanup gestartet (Threshold: {hours_threshold}h)")
    print(f"{'🔍 DRY RUN - ' if dry_run else '🚀 AKTIV - '}Änderungen {'werden NICHT' if dry_run else 'werden'} gespeichert")
    print("=" * 60)

    files = [f for f in os.listdir(games_dir) if f.endswith('.json')]

    total_games = 0
    abandoned_games = 0
    cleaned_games = 0

    for filename in files:
        filepath = os.path.join(games_dir, filename)

        try:
            with open(filepath, 'r') as f:
                game_data = json.load(f)

            total_games += 1
            game_id = game_data.get('id', filename.replace('.json', ''))
            status = game_data.get('status', 'unknown')
            players = len(game_data.get('players', {}))

            last_modified = get_file_last_modified(filepath)
            hours_since = (time.time() - last_modified) / 3600
            last_modified_str = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')

            print(f"📋 {game_id}: Status={status}, Spieler={players}, Letzte Änderung={last_modified_str} ({hours_since:.1f}h)")

            if is_game_abandoned(game_data, filepath, hours_threshold):
                abandoned_games += 1
                print(f"   🗑️  ABANDONED - {hours_since:.1f}h ohne Aktivität")

                if not dry_run:
                    # Spiel als abandoned markieren und beenden
                    game_data['status'] = 'finished'
                    game_data['winner'] = 'abandoned'
                    game_data['end_reason'] = 'game_abandoned'
                    game_data['abandoned_at'] = time.time()
                    game_data['abandoned_after_hours'] = hours_since

                    with open(filepath, 'w') as f:
                        json.dump(game_data, f, indent=2)

                    cleaned_games += 1
                    print(f"   ✅ Spiel als 'finished/abandoned' markiert")
                else:
                    print(f"   💡 Würde als abandoned markiert werden")
            else:
                print(f"   ✅ Aktiv")

        except Exception as e:
            print(f"❌ Fehler bei {filename}: {e}")

    print("=" * 60)
    print(f"📊 ZUSAMMENFASSUNG:")
    print(f"   📁 Spiele gesamt: {total_games}")
    print(f"   🗑️  Abandoned gefunden: {abandoned_games}")
    print(f"   🧹 {'Würden bereinigt werden' if dry_run else 'Bereinigt'}: {cleaned_games}")

    if dry_run and abandoned_games > 0:
        print(f"\n💡 Um die Bereinigung durchzuführen:")
        print(f"   python3 cleanup.py --execute")

def get_cleanup_stats():
    """Gibt Cleanup-Statistiken zurück"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir = os.path.join(base_dir, "games")

    if not os.path.exists(games_dir):
        return {"error": "Games directory not found"}

    files = [f for f in os.listdir(games_dir) if f.endswith('.json')]

    stats = {
        "total_games": 0,
        "active_games": 0,
        "abandoned_candidates": 0,
        "already_abandoned": 0,
        "games_by_age": {"<1h": 0, "1-6h": 0, "6-24h": 0, ">24h": 0}
    }

    for filename in files:
        filepath = os.path.join(games_dir, filename)

        try:
            with open(filepath, 'r') as f:
                game_data = json.load(f)

            stats["total_games"] += 1
            status = game_data.get('status', 'unknown')

            if status in ['lobby', 'started']:
                stats["active_games"] += 1

                last_modified = get_file_last_modified(filepath)
                hours_since = (time.time() - last_modified) / 3600

                if hours_since > 24:
                    stats["abandoned_candidates"] += 1
                    stats["games_by_age"][">24h"] += 1
                elif hours_since > 6:
                    stats["games_by_age"]["6-24h"] += 1
                elif hours_since > 1:
                    stats["games_by_age"]["1-6h"] += 1
                else:
                    stats["games_by_age"]["<1h"] += 1

            elif game_data.get('end_reason') == 'game_abandoned':
                stats["already_abandoned"] += 1

        except Exception as e:
            continue

    return stats

# Flask Route für Cleanup-Interface
def add_cleanup_routes_to_app(app):
    """Fügt Cleanup-Routes zur Flask-App hinzu"""

    @app.route("/admin/cleanup")
    def cleanup_interface():
        """Admin Interface für Game Cleanup"""
        stats = get_cleanup_stats()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SusWords Game Cleanup</title>
            <style>
                body {{ font-family: monospace; margin: 20px; background: #1d1b3a; color: #fff; }}
                h1, h2 {{ color: #00f0ff; }}
                .card {{ background: #2c294d; padding: 20px; border-radius: 8px; margin: 15px 0; }}
                .btn {{ background: #00f0ff; color: #000; padding: 10px 20px; border: none; border-radius: 4px; margin: 5px; cursor: pointer; text-decoration: none; display: inline-block; }}
                .btn.danger {{ background: #ff3260; color: #fff; }}
                .btn.warning {{ background: #ffcc00; color: #000; }}
                .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .stat {{ background: #1b1a2e; padding: 15px; border-radius: 6px; text-align: center; }}
                .big-number {{ font-size: 2em; font-weight: bold; color: #00f0ff; }}
                pre {{ background: #1b1a2e; padding: 15px; border-radius: 6px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>🧹 SusWords Game Cleanup</h1>

            <div class="card">
                <h2>📊 Cleanup Statistics</h2>
                <div class="stat-grid">
                    <div class="stat">
                        <div class="big-number">{stats['total_games']}</div>
                        <div>Spiele Gesamt</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['active_games']}</div>
                        <div>Aktive Spiele</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['abandoned_candidates']}</div>
                        <div>Abandoned Kandidaten</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['already_abandoned']}</div>
                        <div>Bereits bereinigt</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>⏰ Spiele nach Alter</h2>
                <div class="stat-grid">
                    <div class="stat">
                        <div class="big-number">{stats['games_by_age']['<1h']}</div>
                        <div>&lt; 1 Stunde</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['games_by_age']['1-6h']}</div>
                        <div>1-6 Stunden</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['games_by_age']['6-24h']}</div>
                        <div>6-24 Stunden</div>
                    </div>
                    <div class="stat">
                        <div class="big-number">{stats['games_by_age']['>24h']}</div>
                        <div>&gt; 24 Stunden</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🛠️ Cleanup Aktionen</h2>
                <p>⚠️ <strong>Vorsicht:</strong> Cleanup markiert abandoned Spiele als "finished" mit Grund "game_abandoned"</p>

                <a href="/admin/cleanup/dry-run" class="btn">🔍 Dry Run (24h Threshold)</a>
                <a href="/admin/cleanup/dry-run?hours=12" class="btn warning">🔍 Dry Run (12h Threshold)</a>
                <a href="/admin/cleanup/execute" class="btn danger" onclick="return confirm('Wirklich abandoned Games bereinigen?')">🧹 Cleanup Ausführen (24h)</a>

                <p><a href="/debug/stats">📊 Zurück zu Stats</a> | <a href="/">🏠 Home</a></p>
            </div>
        </body>
        </html>
        """

        return html

    @app.route("/admin/cleanup/dry-run")
    def cleanup_dry_run():
        """Dry Run des Cleanups"""
        hours = int(request.args.get('hours', 24))

        # Capture output
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            cleanup_abandoned_games(dry_run=True, hours_threshold=hours)
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()

        return f"""
        <html>
        <head><title>Cleanup Dry Run</title>
        <style>body{{font-family:monospace;background:#1d1b3a;color:#fff;margin:20px;}}
        pre{{background:#2c294d;padding:15px;border-radius:8px;}}
        .btn{{background:#00f0ff;color:#000;padding:10px 20px;text-decoration:none;border-radius:4px;margin:10px 0;display:inline-block;}}
        </style></head>
        <body>
        <h1>🔍 Cleanup Dry Run ({hours}h Threshold)</h1>
        <pre>{output}</pre>
        <a href="/admin/cleanup" class="btn">🔙 Zurück</a>
        </body>
        </html>
        """

    @app.route("/admin/cleanup/execute")
    def cleanup_execute():
        """Führt Cleanup tatsächlich aus"""
        # Sicherheitscheck
        confirm = request.args.get('confirm')
        if confirm != 'yes':
            return """
            <html><body style="font-family:monospace;background:#1d1b3a;color:#fff;margin:20px;">
            <h1>⚠️ Bestätigung erforderlich</h1>
            <p>Um den Cleanup auszuführen, klicke:</p>
            <a href="/admin/cleanup/execute?confirm=yes" style="background:#ff3260;color:#fff;padding:15px 30px;text-decoration:none;border-radius:4px;">✅ Cleanup ausführen</a>
            <a href="/admin/cleanup" style="background:#666;color:#fff;padding:15px 30px;text-decoration:none;border-radius:4px;margin-left:10px;">❌ Abbrechen</a>
            </body></html>
            """

        # Cleanup ausführen
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            cleanup_abandoned_games(dry_run=False, hours_threshold=24)
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()

        return f"""
        <html>
        <head><title>Cleanup Ausgeführt</title>
        <style>body{{font-family:monospace;background:#1d1b3a;color:#fff;margin:20px;}}
        pre{{background:#2c294d;padding:15px;border-radius:8px;}}
        .btn{{background:#00f0ff;color:#000;padding:10px 20px;text-decoration:none;border-radius:4px;margin:10px 0;display:inline-block;}}
        </style></head>
        <body>
        <h1>✅ Cleanup Ausgeführt</h1>
        <pre>{output}</pre>
        <a href="/admin/cleanup" class="btn">🔙 Zurück zum Cleanup</a>
        <a href="/debug/stats" class="btn">📊 Stats anzeigen</a>
        </body>
        </html>
        """

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # Cleanup ausführen
        cleanup_abandoned_games(dry_run=False)
    else:
        # Dry run
        cleanup_abandoned_games(dry_run=True)