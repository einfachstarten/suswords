# config.py - SusWords Configuration
"""
Zentrale Konfiguration für SusWords
Alle Konstanten und Einstellungen an einem Ort
"""

import os

# ===== SPIEL-KONSTANTEN =====

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

# ===== SPIEL-EINSTELLUNGEN =====

GAME_SETTINGS = {
    # Spieler-Limits
    'min_players': 3,
    'max_players': 20,

    # Voting-System
    'vote_duration_seconds': 30,
    'processing_duration_seconds': 1.5,
    'results_duration_seconds': 8,

    # Timeouts & Cleanup
    'game_timeout_hours': 24,
    'cleanup_threshold_hours': 48,
    'polling_interval_seconds': 3,

    # UI Timeouts
    'redirect_countdown_seconds': 5,
    'loading_delay_ms': 100,
    'toast_duration_ms': 4000,
}

# ===== PFAD-KONFIGURATION =====

# Basis-Verzeichnis des Projekts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Daten-Verzeichnisse
DATA_DIR = os.path.join(BASE_DIR, "games")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Dateipfade
VERSION_MANIFEST_PATH = os.path.join(STATIC_DIR, 'version_manifest.json')
CLEANUP_LOG_PATH = os.path.join(BASE_DIR, 'cleanup.log')

# ===== FLASK-KONFIGURATION =====

FLASK_CONFIG = {
    'DEBUG': True,
    'HOST': "0.0.0.0",
    'PORT': 5000,
    'SECRET_KEY': 'suswords-dev-key-change-in-production'
}

# ===== CACHE-BUSTING EINSTELLUNGEN =====

CACHE_SETTINGS = {
    # Asset-Dateien für Cache-Busting
    'static_files': {
        # CSS Files
        'css/game.css': 'static/css/game.css',
        'css/create_game.css': 'static/css/create_game.css',
        'css/join.css': 'static/css/join.css',

        # JS Files
        'js/game.js': 'static/js/game.js',
        'js/create_game.js': 'static/js/create_game.js',
        'js/join.js': 'static/js/join.js',

        # Images
        'suswords.png': 'static/suswords.png',
        'suswords_splash.png': 'static/suswords_splash.png',
        'suswords_icon192.png': 'static/suswords_icon192.png',
        'favicon.ico': 'static/favicon.ico',

        # Audio
        'suswords.mp3': 'static/suswords.mp3',

        # PWA Files
        'manifest.json': 'static/manifest.json',
        'sw.js': 'sw.js'
    },

    # Cache-Headers
    'versioned_max_age': 31536000,  # 1 Jahr für versionierte Assets
    'unversioned_max_age': 300,     # 5 Minuten für unverlierte Assets
}

# ===== STATISTIK-EINSTELLUNGEN =====

STATS_SETTINGS = {
    'track_game_duration': True,
    'track_player_actions': True,
    'track_vote_outcomes': True,
    'cleanup_after_days': 30,

    # Aggregation-Intervalle
    'daily_stats': True,
    'weekly_stats': True,
    'monthly_stats': False,
}

# ===== ENTWICKLUNGS-EINSTELLUNGEN =====

DEV_SETTINGS = {
    'auto_create_version_manifest': True,
    'enable_debug_routes': True,
    'enable_admin_interface': True,
    'log_game_actions': True,
    'auto_cleanup_old_games': True,
}

# ===== HILFSFUNKTIONEN =====

def ensure_directories():
    """Stellt sicher, dass alle nötigen Verzeichnisse existieren"""
    import os
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

def get_setting(category, key, default=None):
    """Hilfsfunktion zum sicheren Abrufen von Einstellungen"""
    settings_map = {
        'game': GAME_SETTINGS,
        'flask': FLASK_CONFIG,
        'cache': CACHE_SETTINGS,
        'stats': STATS_SETTINGS,
        'dev': DEV_SETTINGS,
    }

    return settings_map.get(category, {}).get(key, default)

if __name__ == "__main__":
    print("🔧 SusWords Configuration")
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"📁 Data Directory: {DATA_DIR}")
    print(f"🎮 Secret Words: {len(SECRET_WORDS)} verfügbar")
    print(f"⚙️ Min Players: {GAME_SETTINGS['min_players']}")
    print(f"⏱️ Vote Duration: {GAME_SETTINGS['vote_duration_seconds']}s")