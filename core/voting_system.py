#!/usr/bin/env python3
"""
voting_system.py - Abstimmungssystem für SusWords
Verwaltet alle Vote-bezogenen Funktionen
"""

import time
from typing import Dict, List, Optional, Any

class VotingSystem:
    """Verwaltet das Abstimmungssystem"""

    def __init__(self, file_manager):
        self.file_manager = file_manager

    def start_vote(self, game_id: str, initiator_id: str, suspect_id: str) -> Dict[str, Any]:
        """Startet eine Abstimmung gegen einen Spieler"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        players = game_data.get("players", {})
        if initiator_id not in players or suspect_id not in players:
            raise ValueError("Player not found")

        # Prüfungen
        if game_data.get("votes") is not None:
            raise ValueError("Vote already in progress")

        if self._is_player_eliminated(game_data, suspect_id):
            raise ValueError("Player already eliminated")

        if not self._is_player_turn(game_data, initiator_id):
            raise ValueError("Only current player may start a vote")

        # Vote erstellen
        initiator_name = players[initiator_id]["name"]
        suspect_name = players[suspect_id]["name"]

        game_data["votes"] = {
            "initiator": initiator_id,
            "initiator_name": initiator_name,
            "suspect": suspect_id,
            "suspect_name": suspect_name,
            "votes": {},
            "result": None,
            "started_at": time.time(),
            "duration": 30,  # 30 Sekunden
            "status": "active",
            "up_votes": 0,
            "down_votes": 0
        }

        self.file_manager.save_game(game_id, game_data)

        return {
            "status": "vote_started",
            "suspect": suspect_id,
            "suspect_name": suspect_name,
            "initiator_name": initiator_name,
            "duration": 30
        }

    def cast_vote(self, game_id: str, voter_id: str, vote: str) -> Dict[str, Any]:
        """Gibt eine Stimme ab"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        # Timeout prüfen
        if self._check_vote_timeout(game_data):
            self.file_manager.save_game(game_id, game_data)
            raise ValueError("Vote has timed out")

        votes_data = game_data.get("votes")
        if not votes_data or votes_data.get("status") != "active":
            raise ValueError("No active vote")

        # Prüfungen
        if voter_id == votes_data["suspect"]:
            raise ValueError("Suspect cannot vote")

        if self._is_player_eliminated(game_data, voter_id):
            raise ValueError("Eliminated players cannot vote")

        if voter_id in votes_data["votes"]:
            raise ValueError("Player has already voted")

        # Stimme speichern
        game_data["votes"]["votes"][voter_id] = vote

        # Zählen für Rückgabe
        total_votes = len(votes_data["votes"]) + 1  # +1 für die gerade abgegebene Stimme

        # Aktive Spieler zählen (ohne Suspect)
        active_players = [pid for pid, p in game_data["players"].items()
                         if not p.get("eliminated", False)
                         and pid not in game_data.get("eliminated_players", [])
                         and pid != votes_data["suspect"]]
        total_possible_votes = len(active_players)

        self.file_manager.save_game(game_id, game_data)

        return {
            "status": "vote_recorded",
            "message": "Vote recorded successfully",
            "total_votes": total_votes,
            "total_possible_votes": total_possible_votes
        }

    def get_vote_status(self, game_id: str, player_id: str) -> Dict[str, Any]:
        """Gibt den aktuellen Vote-Status zurück"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        # Timeout prüfen
        if self._check_vote_timeout(game_data):
            self.file_manager.save_game(game_id, game_data)

        votes = game_data.get("votes")

        if not votes or "suspect" not in votes or not votes.get("suspect"):
            return {"active": False}

        # Aktive Spieler zählen
        active_players = [pid for pid, p in game_data["players"].items()
                         if not p.get("eliminated", False)
                         and pid not in game_data.get("eliminated_players", [])
                         and pid != votes.get("suspect")]

        votes_needed = len(active_players)
        votes_cast = len(votes.get("votes", {}))

        # Kann der Spieler abstimmen?
        can_vote = (
            player_id in active_players and
            player_id not in votes.get("votes", {}) and
            player_id != votes.get("suspect") and
            votes.get("status") == "active"
        )

        # Spieler-Namen für UI
        voter_names = {}
        for voter_id, vote_value in votes.get("votes", {}).items():
            voter_name = game_data["players"].get(voter_id, {}).get("name", "Unknown")
            voter_names[voter_id] = {
                "name": voter_name,
                "vote": vote_value
            }

        # Verbleibende Zeit
        elapsed = time.time() - votes.get("started_at", 0)
        remaining = max(0, votes.get("duration", 30) - elapsed)

        response_data = {
            "active": votes.get("status") in ["active", "completed"],
            "initiator_id": votes.get("initiator"),
            "initiator_name": votes.get("initiator_name", "???"),
            "suspect_id": votes.get("suspect"),
            "suspect_name": votes.get("suspect_name", "???"),
            "already_voted": player_id in votes.get("votes", {}),
            "can_vote": can_vote,
            "votes_cast": votes_cast,
            "votes_needed": votes_needed,
            "voters": voter_names,
            "result": votes.get("result"),
            "status": votes.get("status", "active"),
            "remaining_seconds": int(remaining),
            "up_votes": votes.get("up_votes", 0),
            "down_votes": votes.get("down_votes", 0)
        }

        # Zusätzliche Infos bei Ergebnis
        if votes.get("result") and votes.get("status") == "completed":
            self._add_vote_result_info(response_data, game_data, player_id)

        return response_data

    def get_vote_time_remaining(self, game_id: str) -> Dict[str, Any]:
        """Gibt verbleibende Voting-Zeit zurück"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        votes = game_data.get("votes")
        if not votes or votes.get("status") != "active":
            return {"active": False}

        elapsed = time.time() - votes.get("started_at", 0)
        remaining = max(0, votes.get("duration", 30) - elapsed)

        # Auto-beenden bei Timeout
        if remaining <= 0:
            if self._check_vote_timeout(game_data):
                self.file_manager.save_game(game_id, game_data)

        return {
            "active": remaining > 0,
            "remaining_seconds": int(remaining),
            "total_duration": votes.get("duration", 30),
            "votes_cast": len(votes.get("votes", {})),
            "status": votes.get("status", "active")
        }

    def reveal_vote(self, game_id: str) -> Dict[str, Any]:
        """Erzwingt die Auswertung einer Abstimmung"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        votes = game_data.get("votes")
        if not votes or "votes" not in votes:
            raise ValueError("No active vote")

        # Ergebnis verarbeiten
        self._process_vote_result(game_data)
        game_data["votes"]["status"] = "completed"

        self.file_manager.save_game(game_id, game_data)

        return {
            "result": votes.get("result", "no_consensus"),
            "votes": votes.get("votes", {}),
            "up_votes": votes.get("up_votes", 0),
            "down_votes": votes.get("down_votes", 0)
        }

    def clear_vote(self, game_id: str) -> Dict[str, Any]:
        """Entfernt die Abstimmung komplett"""
        game_data = self.file_manager.load_game(game_id)
        if not game_data:
            raise ValueError("Game not found")

        game_data["votes"] = None

        self.file_manager.save_game(game_id, game_data)

        return {"status": "vote_cleared"}

    # ===== PRIVATE HELPER METHODS =====

    def _check_vote_timeout(self, game_data: Dict) -> bool:
        """Prüft und verarbeitet Vote-Timeout"""
        votes = game_data.get("votes")
        if not votes or votes.get("status") != "active":
            return False

        elapsed = time.time() - votes.get("started_at", 0)
        if elapsed >= votes.get("duration", 30):
            # Vote automatisch beenden
            self._process_vote_result(game_data)
            votes["status"] = "completed"
            return True
        return False

    def _process_vote_result(self, game_data: Dict) -> None:
        """Verarbeitet das Vote-Ergebnis"""
        votes_data = game_data["votes"]
        vote_counts = {"up": 0, "down": 0}

        for vote in votes_data["votes"].values():
            if vote in vote_counts:
                vote_counts[vote] += 1

        # Ergebnis speichern
        votes_data["up_votes"] = vote_counts["up"]
        votes_data["down_votes"] = vote_counts["down"]

        # Ergebnis bestimmen
        if vote_counts["up"] > vote_counts["down"]:
            # Spieler eliminieren
            suspect_id = votes_data["suspect"]
            if suspect_id not in game_data.get("eliminated_players", []):
                if "eliminated_players" not in game_data:
                    game_data["eliminated_players"] = []
                game_data["eliminated_players"].append(suspect_id)
                game_data["players"][suspect_id]["eliminated"] = True

            # Spiel-Ende prüfen
            if suspect_id == game_data.get("impostorId"):
                game_data["status"] = "finished"
                game_data["winner"] = "players"
                game_data["end_reason"] = "impostor_found"
                game_data["finished_at"] = time.time()
                votes_data["result"] = "impostor_eliminated"
            else:
                # Prüfen ob nur noch Impostor + 1 Spieler übrig
                active_players = [pid for pid, p in game_data["players"].items()
                                if not p.get("eliminated", False) and
                                pid not in game_data.get("eliminated_players", [])]

                # Impostor noch im Spiel?
                impostor_id = game_data.get("impostorId")
                impostor_still_in_game = (impostor_id in active_players)

                if impostor_still_in_game and len(active_players) <= 2:
                    game_data["status"] = "finished"
                    game_data["winner"] = "impostor"
                    game_data["end_reason"] = "not_enough_players"
                    game_data["finished_at"] = time.time()
                    votes_data["result"] = "impostor_wins"
                else:
                    votes_data["result"] = "player_eliminated"
                    # Spielreihenfolge aktualisieren
                    self._update_turn_after_elimination(game_data, suspect_id)
        else:
            votes_data["result"] = "vote_failed"

    def _update_turn_after_elimination(self, game_data: Dict, eliminated_player_id: str) -> None:
        """Aktualisiert die Spielreihenfolge nach einer Elimination"""
        current_index = game_data.get("current_turn_index", 0)
        turn_order = game_data.get("turn_order", [])

        # Aktive Spieler nach Elimination
        active_turn_order = [pid for pid in turn_order
                           if not game_data["players"].get(pid, {}).get("eliminated", False)
                           and pid not in game_data.get("eliminated_players", [])]

        if active_turn_order:
            # Aktueller Spieler
            if current_index < len(turn_order):
                current_player_id = turn_order[current_index]
            else:
                current_player_id = turn_order[0] if turn_order else None

            # Wenn aktueller Spieler eliminiert wurde
            if current_player_id not in active_turn_order or current_player_id == eliminated_player_id:
                # Nächsten aktiven Spieler finden
                current_idx_in_original = -1
                for i, pid in enumerate(turn_order):
                    if pid == current_player_id:
                        current_idx_in_original = i
                        break

                # Nächsten aktiven Spieler suchen
                next_idx_in_original = (current_idx_in_original + 1) % len(turn_order)
                attempts = 0
                while attempts < len(turn_order):
                    next_player_id = turn_order[next_idx_in_original]
                    if next_player_id in active_turn_order:
                        game_data["current_turn_index"] = next_idx_in_original
                        break
                    next_idx_in_original = (next_idx_in_original + 1) % len(turn_order)
                    attempts += 1

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

    def _add_vote_result_info(self, response_data: Dict, game_data: Dict, player_id: str) -> None:
        """Fügt zusätzliche Informationen zum Vote-Ergebnis hinzu"""
        votes = game_data.get("votes", {})
        suspect_id = votes.get("suspect")
        impostor_id = game_data.get("impostorId")

        if votes.get("result") == "impostor_eliminated":
            response_data["game_status"] = "finished"
            response_data["winner"] = "players"
            response_data["end_reason"] = "impostor_found"
            response_data["secret_word"] = game_data.get("word")
            response_data["eliminated_player"] = {
                "id": suspect_id,
                "name": game_data["players"][suspect_id]["name"],
                "was_impostor": True
            }
        elif votes.get("result") == "impostor_wins":
            response_data["game_status"] = "finished"
            response_data["winner"] = "impostor"
            response_data["end_reason"] = "not_enough_players"
            response_data["secret_word"] = game_data.get("word")
        elif votes.get("result") == "player_eliminated":
            response_data["eliminated_player"] = {
                "id": suspect_id,
                "name": game_data["players"][suspect_id]["name"],
                "was_impostor": False
            }
            # Ist der anfragende Spieler der Impostor?
            response_data["is_player_impostor"] = (player_id == impostor_id)