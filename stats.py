#!/usr/bin/env python3
# stats.py - SusWords Statistics System (Standalone Version)

import json
import os
from collections import defaultdict, Counter
from datetime import datetime
import time

def load_all_games():
    """Lädt alle Spiel-JSONs aus dem /games Verzeichnis"""
    games_dir = "games"
    all_games = []

    print(f"🔍 Suche nach Spiel-Files in: {os.path.abspath(games_dir)}")

    if not os.path.exists(games_dir):
        print(f"❌ Verzeichnis {games_dir} existiert nicht!")
        return []

    files = [f for f in os.listdir(games_dir) if f.endswith('.json')]
    print(f"📁 Gefundene JSON-Files: {len(files)}")

    for filename in files:
        try:
            filepath = os.path.join(games_dir, filename)
            with open(filepath, 'r') as f:
                game_data = json.load(f)
                game_data['filename'] = filename
                all_games.append(game_data)
            print(f"✅ Geladen: {filename}")
        except Exception as e:
            print(f"❌ Fehler beim Laden von {filename}: {e}")
            continue

    print(f"📊 Insgesamt {len(all_games)} Spiele geladen\n")
    return all_games

def calculate_overview_stats(all_games, finished_games):
    """Grundlegende Übersichtsstatistiken"""
    impostor_wins = len([g for g in finished_games if g.get('winner') == 'impostor'])
    player_wins = len([g for g in finished_games if g.get('winner') == 'players'])

    return {
        'total_games': len(all_games),
        'finished_games': len(finished_games),
        'active_games': len([g for g in all_games if g.get('status') in ['lobby', 'started']]),
        'impostor_wins': impostor_wins,
        'player_wins': player_wins,
        'impostor_win_rate': round((impostor_wins / len(finished_games) * 100), 1) if finished_games else 0,
        'avg_game_length': round(sum(len(g.get('history', [])) for g in finished_games) / len(finished_games), 1) if finished_games else 0
    }

def calculate_player_stats(finished_games):
    """Spieler-bezogene Statistiken"""
    player_games = defaultdict(lambda: {
        'total_games': 0,
        'impostor_games': 0,
        'impostor_wins': 0,
        'player_wins': 0,
        'eliminated': 0
    })

    name_frequency = Counter()

    for game in finished_games:
        impostor_id = game.get('impostorId')
        winner = game.get('winner')
        players = game.get('players', {})
        eliminated = game.get('eliminated_players', [])

        for player_id, player_data in players.items():
            name = player_data.get('name', 'Unknown')
            name_frequency[name] += 1

            stats = player_games[name]
            stats['total_games'] += 1

            is_impostor = (player_id == impostor_id)
            if is_impostor:
                stats['impostor_games'] += 1
                if winner == 'impostor':
                    stats['impostor_wins'] += 1
            else:
                if winner == 'players':
                    stats['player_wins'] += 1

            if player_id in eliminated:
                stats['eliminated'] += 1

    # Top-Listen erstellen
    impostor_winrates = []
    detective_scores = []

    for name, stats in player_games.items():
        if stats['impostor_games'] > 0:
            impostor_wr = round((stats['impostor_wins'] / stats['impostor_games']) * 100, 1)
            impostor_winrates.append((name, impostor_wr, stats['impostor_games']))

        player_games_count = stats['total_games'] - stats['impostor_games']
        if player_games_count > 0:
            detective_score = round((stats['player_wins'] / player_games_count) * 100, 1)
            detective_scores.append((name, detective_score, player_games_count))

    return {
        'most_common_names': name_frequency.most_common(10),
        'top_impostors': sorted(impostor_winrates, key=lambda x: x[1], reverse=True)[:5],
        'top_detectives': sorted(detective_scores, key=lambda x: x[1], reverse=True)[:5],
        'total_unique_players': len(player_games)
    }

def calculate_word_stats(finished_games):
    """Wort-bezogene Statistiken"""
    secret_words = Counter()
    hint_words = Counter()

    for game in finished_games:
        secret_word = game.get('word')
        if secret_word:
            secret_words[secret_word] += 1

        history = game.get('history', [])
        for entry in history:
            word = entry.get('word')
            if word:
                hint_words[word.lower()] += 1

    return {
        'most_common_secret_words': secret_words.most_common(10),
        'most_common_hints': hint_words.most_common(15),
        'total_unique_hints': len(hint_words),
        'total_hints_given': sum(hint_words.values())
    }

def calculate_gameplay_stats(finished_games):
    """Gameplay-Mechanik Statistiken"""
    end_reasons = Counter()
    game_lengths = []
    player_counts = []

    for game in finished_games:
        end_reasons[game.get('end_reason', 'unknown')] += 1
        game_lengths.append(len(game.get('history', [])))
        player_counts.append(len(game.get('players', {})))

    return {
        'end_reasons': dict(end_reasons),
        'avg_game_length': round(sum(game_lengths) / len(game_lengths), 1) if game_lengths else 0,
        'game_length_distribution': {
            'short (1-5 rounds)': len([l for l in game_lengths if 1 <= l <= 5]),
            'medium (6-10 rounds)': len([l for l in game_lengths if 6 <= l <= 10]),
            'long (11+ rounds)': len([l for l in game_lengths if l > 10])
        },
        'player_count_distribution': dict(Counter(player_counts))
    }

def print_stats():
    """Hauptfunktion: Lädt und zeigt alle Statistiken"""
    print("🎯 SusWords Statistics Analysis")
    print("=" * 50)

    # Spiele laden
    games = load_all_games()

    if not games:
        print("❌ Keine Spiele gefunden! Stelle sicher, dass:")
        print("   - Das 'games' Verzeichnis existiert")
        print("   - JSON-Files im games/ Verzeichnis liegen")
        print("   - Du im richtigen Verzeichnis bist (neben app.py)")
        return

    # Filter für beendete Spiele
    finished_games = [g for g in games if g.get('status') == 'finished']

    print(f"📊 ÜBERSICHT")
    print("-" * 30)
    overview = calculate_overview_stats(games, finished_games)
    for key, value in overview.items():
        print(f"  {key}: {value}")

    if not finished_games:
        print("\n⚠️  Keine beendeten Spiele gefunden!")
        print("   Nur beendete Spiele werden für detaillierte Stats verwendet.")
        return

    print(f"\n👥 SPIELER-STATISTIKEN")
    print("-" * 30)
    player_stats = calculate_player_stats(finished_games)
    print(f"  Unique Players: {player_stats['total_unique_players']}")

    print(f"\n🏆 TOP IMPOSTORS:")
    for i, (name, winrate, games) in enumerate(player_stats['top_impostors'], 1):
        print(f"    {i}. {name}: {winrate}% ({games} Spiele)")

    print(f"\n🕵️ TOP DETECTIVES:")
    for i, (name, winrate, games) in enumerate(player_stats['top_detectives'], 1):
        print(f"    {i}. {name}: {winrate}% ({games} Spiele)")

    print(f"\n📛 HÄUFIGSTE NAMEN:")
    for name, count in player_stats['most_common_names'][:5]:
        print(f"    {name}: {count}x")

    print(f"\n🔤 WORT-STATISTIKEN")
    print("-" * 30)
    word_stats = calculate_word_stats(finished_games)
    print(f"  Total Hints: {word_stats['total_hints_given']}")
    print(f"  Unique Hints: {word_stats['total_unique_hints']}")

    print(f"\n🎯 HÄUFIGSTE GEHEIMWÖRTER:")
    for word, count in word_stats['most_common_secret_words'][:5]:
        print(f"    {word}: {count}x")

    print(f"\n💡 HÄUFIGSTE HINWEISE:")
    for word, count in word_stats['most_common_hints'][:8]:
        print(f"    {word}: {count}x")

    print(f"\n🎮 GAMEPLAY-STATISTIKEN")
    print("-" * 30)
    gameplay = calculate_gameplay_stats(finished_games)
    print(f"  Durchschnittliche Länge: {gameplay['avg_game_length']} Runden")

    print(f"\n📏 SPIEL-LÄNGEN:")
    for length, count in gameplay['game_length_distribution'].items():
        print(f"    {length}: {count} Spiele")

    print(f"\n👥 SPIELER-ANZAHL:")
    for players, count in gameplay['player_count_distribution'].items():
        print(f"    {players} Spieler: {count} Spiele")

    print(f"\n🏁 SPIEL-ENDEN:")
    for reason, count in gameplay['end_reasons'].items():
        print(f"    {reason}: {count}x")

    print(f"\n✅ Analyse abgeschlossen!")

if __name__ == "__main__":
    print_stats()