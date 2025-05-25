#!/usr/bin/env python3
"""
Cache-Busting System für SusWords
Erstellt automatisch Versionshashes für statische Assets
"""

import hashlib
import os
import json
import time
from datetime import datetime

def generate_file_hash(filepath):
    """Generiert MD5-Hash einer Datei"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:8]  # Erste 8 Zeichen
    except FileNotFoundError:
        return str(int(time.time()))[:8]  # Fallback: Timestamp

def create_version_manifest():
    """Erstellt version_manifest.json mit allen Asset-Hashes"""

    static_files = {
        # CSS Files
        'css/game.css': 'static/css/game.css',

        # JS Files
        'js/game.js': 'static/js/game.js',

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
    }

    version_manifest = {
        "build_time": datetime.now().isoformat(),
        "build_timestamp": int(time.time()),
        "files": {}
    }

    base_dir = os.path.dirname(os.path.abspath(__file__))

    for asset_key, file_path in static_files.items():
        full_path = os.path.join(base_dir, file_path)
        file_hash = generate_file_hash(full_path)
        version_manifest["files"][asset_key] = {
            "hash": file_hash,
            "versioned_path": f"{asset_key}?v={file_hash}"
        }

    # Global Version für komplettes Cache-Busting
    global_hash = hashlib.md5(
        json.dumps(version_manifest["files"], sort_keys=True).encode()
    ).hexdigest()[:8]

    version_manifest["global_version"] = global_hash

    # Manifest speichern
    manifest_path = os.path.join(base_dir, 'static', 'version_manifest.json')
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

    with open(manifest_path, 'w') as f:
        json.dump(version_manifest, f, indent=2)

    print(f"✅ Version Manifest erstellt: {manifest_path}")
    print(f"🔄 Global Version: {global_hash}")
    print(f"📁 {len(static_files)} Assets versioniert")

    return version_manifest

if __name__ == "__main__":
    create_version_manifest()