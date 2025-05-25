#!/bin/bash
# deploy.sh - Professionelles Deployment Script mit Cache-Busting

set -e  # Exit bei Fehlern

echo "🚀 SusWords Deployment gestartet..."

# 1. Version Manifest erstellen
echo "📦 Erstelle Version Manifest..."
python3 cache_busting.py

# 2. Git Status prüfen
echo "📋 Prüfe Git Status..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Uncommitted changes gefunden!"
    git status --short
    read -p "Trotzdem fortfahren? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment abgebrochen"
        exit 1
    fi
fi

# 3. Aktuelle Version lesen
if [ -f "static/version_manifest.json" ]; then
    VERSION=$(python3 -c "import json; print(json.load(open('static/version_manifest.json'))['global_version'])")
    echo "🔖 Deployment Version: $VERSION"
else
    VERSION="unknown"
    echo "⚠️  Keine Version gefunden"
fi

# 4. Git Commit mit Version
echo "📝 Committe Änderungen..."
git add .
git commit -m "🚀 Deploy v$VERSION - $(date '+%Y-%m-%d %H:%M:%S')" || echo "ℹ️  Keine neuen Änderungen"

# 5. Push zu GitHub
echo "⬆️  Pushe zu GitHub..."
git push -f origin master:main

# 6. PythonAnywhere Sync (falls verfügbar)
echo "🔄 Synchronisiere mit PythonAnywhere..."

# Option A: Über PythonAnywhere API (falls konfiguriert)
if command -v pythonanywhere &> /dev/null; then
    pythonanywhere files upload --file static/version_manifest.json
    echo "✅ Version Manifest zu PythonAnywhere hochgeladen"
fi

# Option B: Git Pull auf Server auslösen (falls webhook verfügbar)
# curl -X POST "https://your-webhook-url.com/deploy" || echo "ℹ️  Webhook nicht verfügbar"

# 7. Deployment bestätigen
echo ""
echo "✅ DEPLOYMENT ABGESCHLOSSEN!"
echo "🔖 Version: $VERSION"
echo "⏰ Zeit: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "📋 Nächste Schritte:"
echo "   1. GitHub prüfen: https://github.com/einfachstarten/suswords"
echo "   2. PythonAnywhere Web-Tab öffnen"
echo "   3. 'Pull latest code from repo' klicken"
echo "   4. App testen: https://suswords.pythonanywhere.com"
echo ""
echo "🔧 Cache-Busting aktiv - Browser laden neue Version automatisch!"