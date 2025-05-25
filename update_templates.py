#!/usr/bin/env python3
"""
Template Updater für Cache-Busting
Ersetzt automatisch alle Asset-URLs in HTML-Templates
"""

import os
import re
import glob

def update_templates():
    """Aktualisiert alle HTML-Templates für Cache-Busting"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')

    if not os.path.exists(templates_dir):
        print("❌ Templates-Ordner nicht gefunden!")
        return

    # Asset-Ersetzungen definieren
    replacements = [
        # CSS Files
        (r'href="/static/css/([^"]+)"', r'href="{{ versioned_url(\'static/css/\1\') }}"'),

        # JS Files
        (r'src="/static/js/([^"]+)"', r'src="{{ versioned_url(\'static/js/\1\') }}"'),

        # Images
        (r'src="/static/([^"]*\.(?:png|jpg|jpeg|gif|svg|ico))"', r'src="{{ versioned_url(\'static/\1\') }}"'),

        # Audio Files
        (r'src="/static/([^"]*\.(?:mp3|wav|ogg))"', r'src="{{ versioned_url(\'static/\1\') }}"'),

        # Generic /static/ references
        (r'href="/static/([^"]+)"', r'href="{{ versioned_url(\'static/\1\') }}"'),

        # Service Worker mit Version
        (r"navigator\.serviceWorker\.register\('/sw\.js'\)",
         r"navigator.serviceWorker.register(`/sw.js?v={{ app_version }}`)"),

        # SW.js Route ohne Version Parameter (falls vorhanden)
        (r"navigator\.serviceWorker\.register\('/sw\.js\?v=.*?'\)",
         r"navigator.serviceWorker.register(`/sw.js?v={{ app_version }}`)"),
    ]

    # Alle HTML-Dateien finden
    html_files = glob.glob(os.path.join(templates_dir, '*.html'))

    if not html_files:
        print("❌ Keine HTML-Templates gefunden!")
        return

    print(f"🔍 Gefunden: {len(html_files)} HTML-Templates")

    updated_files = []

    for html_file in html_files:
        filename = os.path.basename(html_file)
        print(f"\n📝 Bearbeite: {filename}")

        try:
            # Datei lesen
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = 0

            # Alle Ersetzungen anwenden
            for pattern, replacement in replacements:
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    changes_made += len(matches)
                    print(f"  ✓ {len(matches)} Asset-URLs aktualisiert")

            # Meta-Tags für Cache-Busting hinzufügen (falls noch nicht vorhanden)
            if '<meta name="app-version"' not in content and '<head>' in content:
                meta_tags = '''  <meta name="app-version" content="{{ app_version }}">
  <meta name="build-time" content="{{ build_time }}">
'''
                content = content.replace('<head>', f'<head>\n{meta_tags}')
                changes_made += 1
                print(f"  ✓ Meta-Tags für Versionierung hinzugefügt")

            # Datei nur schreiben wenn Änderungen gemacht wurden
            if content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_files.append(filename)
                print(f"  💾 {changes_made} Änderungen gespeichert")
            else:
                print(f"  ℹ️  Keine Änderungen nötig")

        except Exception as e:
            print(f"  ❌ Fehler bei {filename}: {e}")

    # Zusammenfassung
    print(f"\n✅ UPDATE ABGESCHLOSSEN!")
    print(f"📁 {len(updated_files)} von {len(html_files)} Templates aktualisiert")

    if updated_files:
        print(f"🔄 Aktualisierte Dateien:")
        for filename in updated_files:
            print(f"   - {filename}")

        print(f"\n🚀 Nächste Schritte:")
        print(f"   1. Templates überprüfen")
        print(f"   2. ./deploy.sh ausführen")
        print(f"   3. PythonAnywhere aktualisieren")
    else:
        print(f"ℹ️  Alle Templates bereits aktuell!")

def preview_changes():
    """Zeigt Vorschau der Änderungen ohne zu speichern"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')

    replacements = [
        (r'href="/static/css/([^"]+)"', r'href="{{ versioned_url(\'static/css/\1\') }}"'),
        (r'src="/static/js/([^"]+)"', r'src="{{ versioned_url(\'static/js/\1\') }}"'),
        (r'src="/static/([^"]*\.(?:png|jpg|jpeg|gif|svg|ico))"', r'src="{{ versioned_url(\'static/\1\') }}"'),
        (r'src="/static/([^"]*\.(?:mp3|wav|ogg))"', r'src="{{ versioned_url(\'static/\1\') }}"'),
        (r'href="/static/([^"]+)"', r'href="{{ versioned_url(\'static/\1\') }}"'),
    ]

    html_files = glob.glob(os.path.join(templates_dir, '*.html'))

    print("🔍 VORSCHAU DER ÄNDERUNGEN:")
    print("=" * 50)

    for html_file in html_files:
        filename = os.path.basename(html_file)

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        found_assets = []
        for pattern, replacement in replacements:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    found_assets.append(f"/static/{match[0] if len(match) > 0 else match}")
                else:
                    found_assets.append(f"/static/{match}")

        if found_assets:
            print(f"\n📝 {filename}:")
            for asset in set(found_assets):  # Duplikate entfernen
                print(f"   {asset}")

    print(f"\n💡 Führe 'python3 update_templates.py' aus um zu aktualisieren")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview_changes()
    else:
        print("🔧 SusWords Template Updater")
        print("=" * 40)

        choice = input("Templates aktualisieren? (y/N): ").strip().lower()
        if choice == 'y':
            update_templates()
        else:
            print("ℹ️  Vorschau mit: python3 update_templates.py preview")
            preview_changes()