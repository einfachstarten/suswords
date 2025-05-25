# 🕵️ SusWords

**Finde den Impostor! Ein spannendes Multiplayer-Wortspiel für 3+ Spieler.**

[![Live Demo](https://img.shields.io/badge/🎮_Live_Demo-SusWords-00f0ff?style=for-the-badge)](https://suswords.pythonanywhere.com)
[![GitHub](https://img.shields.io/badge/GitHub-einfachstarten/suswords-181717?style=for-the-badge&logo=github)](https://github.com/einfachstarten/suswords)

---

## 🎯 Was ist SusWords?

SusWords ist ein browserbasiertes Multiplayer-Wortspiel im "Impostor"-Stil. Jeder Spieler erhält ein geheimes Wort – **außer einer**: Der Impostor kennt das Wort nicht und muss bluffen!

### 🎮 Spielablauf

1. **🔑 Hinweise geben** - Jeder Spieler gibt ein Hinweiswort zum gesuchten Begriff
2. **🕵️ Bluffen** - Der Impostor muss ein glaubwürdiges Wort erfinden
3. **🧠 Diskutieren** - Wer wirkt verdächtig? Wer kennt das Wort nicht?
4. **🗳️ Abstimmen** - Gemeinsam entscheiden, wer der Impostor ist
5. **🏆 Gewinnen** - Wird der Impostor enttarnt? Oder blufft er sich durch?

---

## 🚀 Schnellstart

### Spiel starten
1. Besuche [suswords.pythonanywhere.com](https://suswords.pythonanywhere.com)
2. Klicke **"🎮 Spiel starten"**
3. Gib deinen Namen ein
4. Teile den **QR-Code** oder **Game Code** mit Freunden
5. Warte bis mindestens 3 Spieler beigetreten sind
6. Starte das Spiel!

### Spiel beitreten
1. **Mit Link**: Öffne den geteilten Link direkt
2. **Mit Code**: Klicke **"🔢 Ich habe einen Code"** und gib den 4-stelligen Code ein
3. Gib deinen Namen ein und warte auf den Spielstart

---

## ✨ Features

- 🌐 **Browserbasiert** - Keine App-Installation nötig
- 📱 **Mobile-First** - Optimiert für Smartphones
- 🔗 **Einfaches Teilen** - QR-Code oder Game Code
- ⚡ **Echtzeitspiel** - Sofortige Updates für alle Spieler
- 🎨 **Moderne UI** - Dunkles Design mit Sci-Fi Atmosphäre
- 🔊 **Lobby-Musik** - Atmosphärische Hintergrundmusik
- 📱 **PWA-Support** - Installierbar als App
- 🎯 **Voting-System** - Spannende Abstimmungsrunden

---

## 🛠️ Technologie

### Backend
- **Flask** (Python) - Leichtgewichtiges Web-Framework
- **JSON-Files** - Einfache Datenspeicherung
- **REST API** - Saubere Client-Server Kommunikation

### Frontend
- **Vanilla JavaScript** - Keine schweren Frameworks
- **CSS Custom Properties** - Konsistentes Design-System
- **Responsive Design** - Funktioniert auf allen Geräten
- **Progressive Web App** - Moderne Web-Standards

### Hosting
- **PythonAnywhere** - Zuverlässiges Python-Hosting
- **GitHub** - Versionskontrolle und CI/CD
- **Cache-Busting** - Automatische Asset-Versionierung

---

## 📁 Projektstruktur

```
suswords/
├── app.py                 # Flask Backend & API
├── templates/             # HTML Templates
│   ├── index.html        # Startseite
│   ├── create_game.html  # Spiel erstellen
│   ├── join.html         # Spiel beitreten
│   ├── game.html         # Hauptspiel
│   └── game_ended.html   # Spielende
├── static/               # Assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript
│   ├── *.png            # Bilder & Icons
│   └── *.mp3            # Sounds
├── games/               # Spielzustände (JSON)
├── cache_busting.py     # Asset-Versionierung
└── deploy.sh           # Deployment-Script
```

---

## 🎯 Spielregeln

### Für normale Spieler
- **Ziel**: Den Impostor finden und eliminieren
- **Hinweise geben**: Beschreibe das geheime Wort ohne es zu nennen
- **Abstimmen**: Entscheide weise, wer verdächtig wirkt
- **Gewinnen**: Wenn der Impostor eliminiert wird

### Für den Impostor
- **Ziel**: Unentdeckt bleiben oder das Wort erraten
- **Bluffen**: Gib glaubwürdige "Hinweise" ohne das Wort zu kennen
- **Beobachten**: Versuche aus den Hinweisen das Wort zu erraten
- **Gewinnen**: Wenn du nicht eliminiert wirst oder das Wort erratst

---

## 🔧 Entwicklung

### Lokale Installation
```bash
# Repository klonen
git clone https://github.com/einfachstarten/suswords.git
cd suswords

# Abhängigkeiten installieren
pip install -r requirements.txt

# Cache-Busting generieren
python3 cache_busting.py

# Server starten
python3 app.py
```

Die App läuft dann auf `http://localhost:5000`

### Development Workflow
```bash
# Feature-Branch erstellen
./safe_point.sh feature mein-feature "Beschreibung"

# Entwickeln...

# Safe Point erstellen
./safe_point.sh create v1.x-working "Feature fertig"

# Feature mergen
./safe_point.sh merge mein-feature

# Deployen
./deploy.sh
```

---

## 🌟 Roadmap

- [ ] **🎵 Sound-Effekte** - Feedback für Aktionen
- [ ] **📊 Statistiken** - Spieler-Erfolgsraten
- [ ] **🎨 Themes** - Verschiedene Design-Varianten
- [ ] **🔄 Reconnect** - Automatische Wiederverbindung
- [ ] **👥 Spectator Mode** - Zuschauer-Modus
- [ ] **🌍 Internationalisierung** - Mehrsprachigkeit
- [ ] **🎪 Custom Words** - Eigene Wortlisten

---

## 🤝 Beitragen

Beiträge sind willkommen! 

1. **Fork** das Repository
2. **Feature-Branch** erstellen (`git checkout -b feature/amazing-feature`)
3. **Änderungen committen** (`git commit -m 'Add amazing feature'`)
4. **Branch pushen** (`git push origin feature/amazing-feature`)
5. **Pull Request** öffnen

---

## 📜 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.

---

## 🎉 Credits

**Entwickelt mit ❤️ von [Einfach Starten](https://github.com/einfachstarten)**

- 🎨 **Design**: Moderne Sci-Fi Ästhetik
- 🎵 **Musik**: Atmosphärische Lobby-Sounds  
- 🎮 **Gameplay**: Inspiriert von Social Deduction Games
- 💻 **Code**: Vanilla Web-Technologien für maximale Performance

---

## 📞 Support

Probleme oder Fragen? 

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/einfachstarten/suswords/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/einfachstarten/suswords/discussions)
- 📧 **Kontakt**: Über GitHub Profil

---

**🎮 Viel Spaß beim Spielen! Wer ist der Impostor? 🕵️**
