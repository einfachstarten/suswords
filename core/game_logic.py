#!/usr/bin/env python3
"""
game_logic.py - Kernspiellogik für SusWords
Enthält alle Spiel-spezifischen Funktionen und Geschäftslogik
"""

import uuid
import random
import time
from typing import Dict, List, Optional, Tuple, Any

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

class GameLogic:
    """Zentrale Klasse für die Spiellogik"""

    def __init__(self, file_manager):
        self.file_manager = file_manager

    def create_new_game(self) -> str:
        """Erstellt ein neues Spiel und gibt die Game-ID zurück"""
        game_id = uuid.uuid4().hex[:4].upper()
        game_data = {
            "id": game_id,
            "status": "lobby",
            "players": {},
            "votes": None,
            "history": [],
            "eliminated_players": [],
            "created_at": time.time()
        }

        self.file_manager.save_game(game_id, game_data)
        return game_id

    def add_player_to_game(self, game_id: str, player_name: str) -> Dict[str, Any]:
        """Fügt einen Spieler zum Spiel hinzu"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        # Name-Kollisionsprüfung
        existing_names = [p["name"] for p in game_data["players"].values()]
        original_name = player_name
        suffix = 2
        while player_name in existing_names:
            player_name = f"{original_name} ({suffix})"
            suffix += 1

        player_id = uuid.uuid4().hex[:8]
        is_first = len(game_data["players"]) == 0

        game_data["players"][player_id] = {
            "name": player_name,
            "role": "pending",
            "vote": None,
            "ready": False,
            "is_master": is_first,
            "eliminated": False,
            "joined_at": time.time()
        }

        self.file_manager.save_game(game_id, game_data)

        return {
            "player_id": player_id,
            "name": player_name,
            "game_id": game_id,
            "is_master": is_first
        }

    def start_game(self, game_id: str) -> Dict[str, Any]:
        """Startet ein Spiel"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        player_ids = list(game_data["players"].keys())
        if len(player_ids) < 3:
            raise ValueError("At least 3 players required")

        # Spiel starten
        game_data["status"] = "started"
        secret_word = random.choice(SECRET_WORDS)
        game_data["word"] = secret_word
        game_data["started_at"] = time.time()

        # Impostor auswählen
        impostor_id = random.choice(player_ids)
        game_data["impostorId"] = impostor_id

        # Rollen zuweisen
        for pid in player_ids:
            role = "impostor" if pid == impostor_id else "normal"
            game_data["players"][pid]["role"] = role

        # Spielreihenfolge festlegen
        random.shuffle(player_ids)
        game_data["turn_order"] = player_ids
        game_data["current_turn_index"] = 0

        self.file_manager.save_game(game_id, game_data)

        return {
            "status": "started",
            "impostorId": impostor_id,
            "word": secret_word
        }

    def submit_word(self, game_id: str, player_id: str, word: str) -> Dict[str, Any]:
        """Speichert ein Hinweiswort eines Spielers"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        if player_id not in game_data["players"]:
            raise ValueError("Player not found")

        # Prüfen ob Spieler eliminiert
        if self._is_player_eliminated(game_data, player_id):
            raise ValueError("Eliminated players cannot submit words")

        # Prüfen ob Impostor das Wort erraten hat
        player_role = game_data["players"][player_id]["role"]
        secret_word = game_data.get("word", "")

        if player_role == "impostor" and word.lower() == secret_word.lower():
            # Impostor hat das Wort erraten!
            game_data["status"] = "finished"
            game_data["winner"] = "impostor"
            game_data["end_reason"] = "word_guessed"
            game_data["finished_at"] = time.time()

            self.file_manager.save_game(game_id, game_data)

            return {
                "status": "game_over",
                "winner": "impostor",
                "reason": "word_guessed"
            }

        # Prüfen ob Spieler dran ist
        if not self._is_player_turn(game_data, player_id):
            raise ValueError("Not your turn")

        # Wort speichern
        game_data["history"].append({
            "player_id": player_id,
            "word": word,
            "timestamp": time.time()
        })

        # Nächster Spieler
        self._advance_turn(game_data)

        self.file_manager.save_game(game_id, game_data)

        return {
            "status": "ok",
            "next_turn_index": game_data["current_turn_index"]
        }

    def get_game_state_for_player(self, game_id: str, player_id: str) -> Dict[str, Any]:
        """Gibt den Spielzustand für einen bestimmten Spieler zurück"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        players = game_data.get("players", {})
        if player_id not in players:
            raise ValueError("Player not found")

        # Prüfen ob Spiel beendet
        if game_data.get("status") == "finished":
            return {
                "game_status": "finished",
                "winner": game_data.get("winner", "unknown"),
                "end_reason": game_data.get("end_reason", "unknown"),
                "your_role": players[player_id]["role"],
                "word": game_data.get("word"),
                "impostor_id": game_data.get("impostorId"),
                "history": game_data.get("history", []),
                "eliminated_players": game_data.get("eliminated_players", [])
            }

        # Prüfen ob Spieler eliminiert
        if self._is_player_eliminated(game_data, player_id):
            return {
                "status": "eliminated",
                "message": "Du wurdest aus dem Spiel entfernt!"
            }

        player = players[player_id]
        is_impostor = player["role"] == "impostor"

        # Aktueller Spieler bestimmen
        current_player_name = self._get_current_player_name(game_data)

        # Vote-Informationen
        active_vote = self._get_vote_info_for_player(game_data, player_id)

        return {
            "player_name": player["name"],
            "your_role": player["role"],
            "your_word": None if is_impostor else game_data.get("word"),
            "game_status": game_data.get("status"),
            "current_player": current_player_name,
            "is_master": player.get("is_master", False),
            "history": game_data.get("history", []),
            "eliminated_players": game_data.get("eliminated_players", []),
            "active_vote": active_vote
        }

    def get_players_in_game(self, game_id: str) -> List[Dict[str, Any]]:
        """Gibt eine Liste aller Spieler im Spiel zurück"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        players = game_data.get("players", {})
        eliminated = game_data.get("eliminated_players", [])

        return [
            {
                "player_id": pid,
                "name": pdata.get("name", ""),
                "role": pdata.get("role", "pending"),
                "is_master": pdata.get("is_master", False),
                "eliminated": pdata.get("eliminated", False) or pid in eliminated
            }
            for pid, pdata in players.items()
        ]

    def restart_game(self, game_id: str) -> Dict[str, Any]:
        """Startet ein Spiel neu (für Revanche)"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        # Spieler zurücksetzen
        for pid in game_data["players"]:
            game_data["players"][pid]["role"] = "pending"
            game_data["players"][pid]["vote"] = None
            game_data["players"][pid]["ready"] = False
            game_data["players"][pid]["eliminated"] = False

        # Spiel zurücksetzen
        game_data["status"] = "lobby"
        game_data["word"] = None
        game_data["votes"] = None
        game_data["history"] = []
        game_data["eliminated_players"] = []

        # Game-Ende Daten entfernen
        for key in ["winner", "end_reason", "finished_at", "started_at"]:
            if key in game_data:
                del game_data[key]

        self.file_manager.save_game(game_id, game_data)

        return {"status": "restarted"}

    def end_game(self, game_id: str, winner: str = "unknown", reason: str = "unknown") -> Dict[str, Any]:
        """Beendet ein Spiel"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        game_data["status"] = "finished"
        game_data["winner"] = winner
        game_data["end_reason"] = reason
        game_data["finished_at"] = time.time()

        self.file_manager.save_game(game_id, game_data)

        return {
            "status": "game_ended",
            "winner": winner,
            "reason": reason
        }

    # ===== PRIVATE HELPER METHODS =====

    def _is_player_eliminated(self, game_data: Dict, player_id: str) -> bool:
        """Prüft ob ein Spieler eliminiert ist"""
        return (game_data["players"][player_id].get("eliminated", False) or
                player_id in game_data.get("eliminated_players", []))

    def _is_player_turn(self, game_data: Dict, player_id: str) -> bool:
        """Prüft ob ein Spieler an der Reihe ist"""
        current_index = game_data.get("current_turn_index", 0)
        turn_order = game_data.get("turn_order", [])

        if not turn_order:
            return False

        # Aktive Spieler-Reihenfolge
        active_turn_order = [pid for pid in turn_order
                           if not self._is_player_eliminated(game_data, pid)]

        if not active_turn_order:
            return False

        # Index anpassen falls nötig
        if current_index >= len(active_turn_order):
            current_index = current_index % len(active_turn_order)
            game_data["current_turn_index"] = current_index

        current_player_id = active_turn_order[current_index % len(active_turn_order)]
        return player_id == current_player_id

    def _advance_turn(self, game_data: Dict) -> None:
        """Geht zum nächsten Spieler über"""
        current_index = game_data.get("current_turn_index", 0)
        turn_order = game_data.get("turn_order", [])

        # Aktive Spieler
        active_turn_order = [pid for pid in turn_order
                           if not self._is_player_eliminated(game_data, pid)]

        if active_turn_order:
            game_data["current_turn_index"] = (current_index + 1) % len(active_turn_order)

    def _get_current_player_name(self, game_data: Dict) -> Optional[str]:
        """Gibt den Namen des aktuellen Spielers zurück"""
        current_index = game_data.get("current_turn_index", 0)
        turn_order = game_data.get("turn_order", [])
        players = game_data.get("players", {})

        # Aktive Spieler
        active_turn_order = [pid for pid in turn_order
                           if not self._is_player_eliminated(game_data, pid)]

        if not active_turn_order:
            return None

        # Index anpassen falls nötig
        if current_index >= len(active_turn_order):
            current_index = current_index % len(active_turn_order)
            game_data["current_turn_index"] = current_index

        current_player_id = active_turn_order[current_index % len(active_turn_order)]
        return players[current_player_id]["name"] if current_player_id else None

    def _get_vote_info_for_player(self, game_data: Dict, player_id: str) -> Optional[Dict]:
        """Gibt Vote-Informationen für einen Spieler zurück"""
        votes = game_data.get("votes")
        if not votes:
            return None

        players = game_data.get("players", {})

        initiator_id = votes.get("initiator")
        suspect_id = votes.get("suspect")

        initiator_name = players.get(initiator_id, {}).get("name") if initiator_id else None
        suspect_name = players.get(suspect_id, {}).get("name") if suspect_id else None

        return {
            "initiator_id": initiator_id,
            "initiator_name": initiator_name,
            "suspect_id": suspect_id,
            "suspect_name": suspect_name,
            "votes": votes.get("votes", {}),
            "result": votes.get("result"),
            "status": votes.get("status", "active"),
            "started_at": votes.get("started_at"),
            "duration": votes.get("duration", 30),
            "up_votes": votes.get("up_votes", 0),
            "down_votes": votes.get("down_votes", 0)
        }