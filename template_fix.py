#!/usr/bin/env python3
"""
Debug Script für Cache-Busting Probleme
"""

import os
import json
import glob

def debug_cache_busting():
    """Diagnostiziert Cache-Busting Probleme"""

    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("🔍 CACHE-BUSTING DIAGNOSE")
    print("=" * 40)

    # 1. Version Manifest prüfen
    print("\n📦 Version Manifest:")
    manifest_path = os.path.join(base_dir, 'static', 'version_manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"  ✅ Global Version: {manifest.get('global_version')}")
        print(f"  📅 Build Time: {manifest.get('build_time')}")
        print(f"  📁 Assets: {len(manifest.get('files', {}))}")

        # Top 3 Assets zeigen
        for i, (asset, info) in enumerate(list(manifest.get('files', {}).items())[:3]):
            print(f"     - {asset}: v{info.get('hash')}")
    else:
        print("  ❌ Version Manifest fehlt!")

    # 2. JavaScript Dateien prüfen
    print("\n🔧 JavaScript Dateien:")
    js_files = glob.glob(os.path.join(base_dir, 'static', 'js', '*.js'))
    for js_file in js_files:
        filename = os.path.basename(js_file)
        size = os.path.getsize(js_file)
        print(f"  📄 {filename}: {size:,} bytes")

        # Prüfe ob Datei vollständig ist (endet mit } oder ;)
        with open(js_file, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                if content.strip().endswith(('}', ';', ')')):
                    print(f"     ✅ Datei scheint vollständig")
                else:
                    print(f"     ⚠️  Datei endet mit: '{content.strip()[-10:]}'")
                    print(f"     ❌ Möglicherweise truncated!")
            except Exception as e:
                print(f"     ❌ Lesefehler: {e}")

    # 3. Templates prüfen
    print("\n🎨 Template Versioned URLs:")
    templates_dir = os.path.join(base_dir, 'templates')
    html_files = glob.glob(os.path.join(templates_dir, '*.html'))

    for html_file in html_files[:2]:  # Nur erste 2
        filename = os.path.basename(html_file)
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Suche nach versioned_url Aufrufen
        import re
        versioned_calls = re.findall(r'versioned_url\([\'"]([^\'"]+)[\'"]\)', content)
        if versioned_calls:
            print(f"  📝 {filename}:")
            for call in versioned_calls[:3]:  # Max 3 zeigen
                print(f"     - {call}")
        else:
            # Suche nach alten /static/ URLs
            static_urls = re.findall(r'[\'"]\/static\/[^\'"]+[\'"]', content)
            if static_urls:
                print(f"  ⚠️  {filename} hat noch alte URLs:")
                for url in static_urls[:2]:
                    print(f"     - {url}")

    # 4. App.py Cache Route prüfen
    print("\n🔧 Flask App Konfiguration:")
    app_py_path = os.path.join(base_dir, 'app.py')
    if os.path.exists(app_py_path):
        with open(app_py_path, 'r', encoding='utf-8') as f:
            app_content = f.read()

        if 'versioned_static' in app_content:
            print("  ✅ versioned_static Route gefunden")
        else:
            print("  ❌ versioned_static Route fehlt!")

        if 'context_processor' in app_content:
            print("  ✅ context_processor gefunden")
        else:
            print("  ❌ context_processor fehlt!")

    print("\n🚀 EMPFOHLENE AKTIONEN:")

    # JavaScript Probleme
    if any(os.path.getsize(js) < 1000 for js in js_files):
        print("  1. ❌ JavaScript-Dateien sind zu klein - eventuell beschädigt")
        print("     → Git status prüfen und ggf. restore")

    # Template Probleme
    any_old_urls = False
    for html_file in html_files:
        with open(html_file, 'r') as f:
            if '/static/' in f.read() and 'versioned_url' not in f.read():
                any_old_urls = True
                break

    if any_old_urls:
        print("  2. ⚠️  Templates haben noch alte /static/ URLs")
        print("     → Template Update Script nochmal laufen lassen")

    print("  3. 🔄 PythonAnywhere Reload klicken")
    print("  4. 🧪 Incognito-Fenster testen")

if __name__ == "__main__":
    debug_cache_busting()