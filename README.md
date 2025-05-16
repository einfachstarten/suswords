# SusWords – A Social Deduction Word Game

SusWords is a browser-based party game inspired by social deduction mechanics, where players try to identify the hidden "impostor" among them through word clues and voting. Designed for quick rounds, it is optimized for minimal setup, seamless UI, and intuitive gameplay.

---

## 🎯 Game Concept

Each round, one player is secretly assigned the role of the **impostor**, while the rest receive a **secret word**. Players take turns submitting a word related to the secret word — except the impostor, who has to improvise based on what others say.

At any time during a round, a player can **suspect** someone by initiating a vote. All players (except the suspect) can vote. If the majority votes "👍", the suspected player is eliminated. If they were the impostor, the game ends with a win for the others. Otherwise, the game continues — unless the impostor manages to outlive the rest...

---

## 🧩 Features

- 🧠 **Word clue submission** with input validation and turn-based logic
- 🕵️ **Vote mechanic** with real-time overlays and dramatic reveal
- 🔀 **Random role assignment** at game start
- 🔒 **Impostor restrictions** (no access to secret word, can't vote on themselves)
- ⚖️ **Voting outcome logic** (including automatic game end and round transitions)
- ☠️ **Player elimination tracking** with strike-through history
- 🏁 **Game end screen** with role-based win/lose messages and restart option
- 🔁 **Backend game state management** using JSON files
- 📡 **Live polling** for UI updates every 3 seconds
- ✅ **Compatible with mobile and desktop browsers**
- 🌐 **No account or login required**

---

## 💻 Tech Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Python 3 (Flask)
- **Hosting**: PythonAnywhere (or any standard Flask hosting environment)
- **Data Storage**: JSON files per game session (no database needed)
