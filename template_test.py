#!/usr/bin/env python3
"""
Template Funktionstest - Prüft ob versioned_url funktioniert
"""

import os
import glob

def test_templates():
    """Testet Template versioned_url Funktionen"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')

    print("🧪 TEMPLATE FUNKTIONSTEST")
    print("=" * 40)

    html_files = glob.glob(os.path.join(templates_dir, '*.html'))

    for html_file in html_files:
        filename = os.path.basename(html_file)
        print(f"\n📝 {filename}:")

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Suche nach allen Asset-Referenzen
        import re

        # Finde versioned_url Calls
        versioned_calls = re.findall(r'versioned_url\([\'"]([^\'"]+)[\'"]\)', content)

        # Finde alte /static/ URLs
        old_static = re.findall(r'[\'"]\/static\/[^\'"]+[\'"]', content)

        # Finde game.js spezifisch
        js_refs = re.findall(r'[\'"][^\'"]*/js/game\.js[^\'"]*[\'"]', content)

        if versioned_calls:
            print(f"  ✅ versioned_url Calls gefunden:")
            for call in versioned_calls:
                print(f"     - {call}")

        if old_static:
            print(f"  ⚠️  Alte /static/ URLs gefunden:")
            for url in old_static:
                print(f"     - {url}")

        if js_refs:
            print(f"  🔧 JavaScript Referenzen:")
            for ref in js_refs:
                print(f"     - {ref}")

        # Prüfe spezifische Probleme
        if 'game.js' in content and filename == 'game.html':
            if 'versioned_url' not in content:
                print(f"  ❌ game.html lädt game.js OHNE versioned_url!")
            else:
                print(f"  ✅ game.html verwendet versioned_url")

def fix_remaining_static_urls():
    """Repariert verbleibende /static/ URLs"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')

    html_files = glob.glob(os.path.join(templates_dir, '*.html'))

    print(f"\n🛠️  REPARIERE VERBLEIBENDE URLS")
    print("=" * 40)

    for html_file in html_files:
        filename = os.path.basename(html_file)

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Spezifische Fixes für häufige Patterns
        fixes = [
            # CSS
            (r'href="/static/([^"]+\.css)"', r'href="{{ versioned_url("static/\1") }}"'),
            # JS
            (r'src="/static/([^"]+\.js)"', r'src="{{ versioned_url("static/\1") }}"'),
            # Images
            (r'src="/static/([^"]+\.(png|jpg|jpeg|gif|svg|ico))"', r'src="{{ versioned_url("static/\1") }}"'),
            # Audio
            (r'src="/static/([^"]+\.(mp3|wav|ogg))"', r'src="{{ versioned_url("static/\1") }}"'),
            # Generic href
            (r'href="/static/([^"]+)"', r'href="{{ versioned_url("static/\1") }}"'),
        ]

        changes = 0
        import re
        for pattern, replacement in fixes:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                changes += len(matches)

        if content != original_content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ {filename}: {changes} URLs repariert")
        else:
            print(f"  ℹ️  {filename}: Keine Reparaturen nötig")

if __name__ == "__main__":
    test_templates()

    print(f"\n" + "=" * 50)
    choice = input("Verbleibende URLs reparieren? (y/N): ").strip().lower()
    if choice == 'y':
        fix_remaining_static_urls()
        print(f"\n🚀 Nach Reparatur: PythonAnywhere Reload klicken!")