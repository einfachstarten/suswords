#!/bin/bash
# safe_point.sh - Erstellt sichere Wiederherstellungspunkte

set -e

# Farben für bessere Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔒 SusWords Safe Point Manager${NC}"
echo "=================================="

# Aktueller Status
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_VERSION=$(python3 -c "import json; print(json.load(open('static/version_manifest.json'))['global_version'])" 2>/dev/null || echo "unknown")

echo -e "${YELLOW}📊 Aktueller Status:${NC}"
echo "   Branch: $CURRENT_BRANCH"
echo "   Version: $CURRENT_VERSION"
echo "   Commit: $(git log -1 --oneline)"

# Funktionen
create_safe_point() {
    local tag_name="$1"
    local description="$2"

    echo -e "\n${BLUE}🔒 Erstelle Safe Point: $tag_name${NC}"

    # Alles committen
    echo "📝 Committe aktuelle Änderungen..."
    git add .
    git commit -m "🔒 Safe Point: $tag_name - $description" || echo "Keine neuen Änderungen"

    # Tag erstellen
    echo "🏷️  Erstelle Tag..."
    git tag -a "$tag_name" -m "Safe Point: $description"

    # Zu GitHub pushen
    echo "⬆️  Pushe zu GitHub..."
    git push origin $CURRENT_BRANCH
    git push origin "$tag_name"

    echo -e "${GREEN}✅ Safe Point '$tag_name' erfolgreich erstellt!${NC}"
    echo -e "${YELLOW}📋 Wiederherstellung mit: ./safe_point.sh restore $tag_name${NC}"
}

create_feature_branch() {
    local branch_name="$1"
    local description="$2"

    echo -e "\n${BLUE}🌿 Erstelle Feature Branch: $branch_name${NC}"

    # Aktuellen Stand sichern
    git add .
    git commit -m "💾 Sichere Stand vor Feature: $branch_name" || echo "Keine Änderungen"
    git push origin $CURRENT_BRANCH

    # Neuen Branch erstellen
    echo "🌱 Erstelle neuen Branch..."
    git checkout -b "$branch_name"
    git push -u origin "$branch_name"

    echo -e "${GREEN}✅ Feature Branch '$branch_name' erstellt!${NC}"
    echo -e "${YELLOW}📋 Zurück zu main: git checkout main${NC}"
}

restore_safe_point() {
    local tag_name="$1"

    echo -e "\n${RED}⚠️  WIEDERHERSTELLUNG ZU: $tag_name${NC}"
    echo "Das wird ALLE aktuellen Änderungen überschreiben!"
    read -p "Wirklich fortfahren? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Abgebrochen"
        return 1
    fi

    echo "🔄 Stelle Safe Point wieder her..."

    # Zurück zu main
    git checkout main

    # Hard reset zum Tag
    git reset --hard "$tag_name"

    # Force push (gefährlich, aber nötig)
    git push --force-with-lease origin main

    echo -e "${GREEN}✅ Wiederherstellung zu '$tag_name' abgeschlossen!${NC}"
    echo -e "${YELLOW}⚠️  Version Manifest neu generieren...${NC}"
    python3 cache_busting.py
}

list_safe_points() {
    echo -e "\n${BLUE}📋 Verfügbare Safe Points:${NC}"
    git tag -l -n1 | grep -E "^v[0-9]|stable|working" | head -10

    echo -e "\n${BLUE}🌿 Verfügbare Branches:${NC}"
    git branch -a | grep -v HEAD
}

merge_feature() {
    local feature_branch="$1"

    echo -e "\n${BLUE}🔀 Merge Feature Branch: $feature_branch${NC}"

    # Zu main wechseln
    git checkout main

    # Feature Branch mergen
    echo "🔀 Merge Feature..."
    git merge "$feature_branch" --no-ff -m "🚀 Merge feature: $feature_branch"

    # Pushen
    git push origin main

    # Feature Branch löschen (optional)
    read -p "Feature Branch '$feature_branch' löschen? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git branch -d "$feature_branch"
        git push origin --delete "$feature_branch"
        echo -e "${GREEN}✅ Feature Branch gelöscht${NC}"
    fi

    echo -e "${GREEN}✅ Feature erfolgreich gemerged!${NC}"
}

# Hauptlogik
case "${1:-help}" in
    "create")
        if [ -z "$2" ]; then
            echo "Usage: ./safe_point.sh create <tag_name> [description]"
            echo "Beispiel: ./safe_point.sh create v1.2-stable 'Cache-Busting funktioniert'"
            exit 1
        fi
        create_safe_point "$2" "${3:-Safe Point}"
        ;;

    "feature")
        if [ -z "$2" ]; then
            echo "Usage: ./safe_point.sh feature <branch_name> [description]"
            echo "Beispiel: ./safe_point.sh feature add-statistics 'Spielstatistiken hinzufügen'"
            exit 1
        fi
        create_feature_branch "$2" "${3:-Feature Branch}"
        ;;

    "restore")
        if [ -z "$2" ]; then
            echo "Usage: ./safe_point.sh restore <tag_name>"
            echo "Beispiel: ./safe_point.sh restore v1.2-stable"
            exit 1
        fi
        restore_safe_point "$2"
        ;;

    "list")
        list_safe_points
        ;;

    "merge")
        if [ -z "$2" ]; then
            echo "Usage: ./safe_point.sh merge <feature_branch>"
            echo "Beispiel: ./safe_point.sh merge add-statistics"
            exit 1
        fi
        merge_feature "$2"
        ;;

    "help"|*)
        echo -e "${YELLOW}🔒 Safe Point Manager - Kommandos:${NC}"
        echo ""
        echo "🔒 SAFE POINTS:"
        echo "  create <name> [desc]  - Erstellt sicheren Wiederherstellungspunkt"
        echo "  restore <name>        - Stellt Safe Point wieder her (⚠️ GEFÄHRLICH)"
        echo "  list                  - Zeigt alle Safe Points"
        echo ""
        echo "🌿 FEATURE ENTWICKLUNG:"
        echo "  feature <name> [desc] - Erstellt neuen Feature Branch"
        echo "  merge <branch>        - Merged Feature Branch zurück"
        echo ""
        echo "📋 BEISPIELE:"
        echo "  ./safe_point.sh create v1.2-working 'Cache-Busting funktioniert'"
        echo "  ./safe_point.sh feature add-chat 'Chat-System hinzufügen'"
        echo "  ./safe_point.sh restore v1.2-working"
        echo ""
        ;;
esac