// static/js/join.js

// Get game ID from HTML data attribute or URL
let gameId = document.querySelector('.container').dataset.gameId;
const music = document.getElementById("lobbyMusic");
const muteBtn = document.getElementById("muteBtn");

function toggleMute() {
  music.muted = !music.muted;
  muteBtn.innerText = music.muted ? "🔈 Musik an" : "🔊 Musik aus";
}

// Button loading state
function setButtonLoading(button, loading = true) {
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.textContent = 'Wird geladen...';
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.classList.remove('loading');
    button.disabled = false;
  }
}

async function loadGame() {
  const gameCodeInput = document.getElementById("gameCodeInput");
  const inputGameId = gameCodeInput.value.trim().toUpperCase();

  if (!inputGameId) {
    gameCodeInput.focus();
    alert("Bitte gib einen Game Code ein.");
    return;
  }

  const loadBtn = document.querySelector('button[onclick="loadGame()"]');
  setButtonLoading(loadBtn, true);

  try {
    // Check if game exists by trying to get players
    const res = await fetch(`/players_in_game/${inputGameId}`);

    if (!res.ok) {
      throw new Error("Spiel nicht gefunden");
    }

    const data = await res.json();

    if (!data.players) {
      throw new Error("Ungültiger Game Code");
    }

    // Game exists! Update the page
    gameId = inputGameId;
    document.querySelector('.container').dataset.gameId = gameId;
    document.getElementById("displayGameId").textContent = gameId;
    document.getElementById("pageTitle").textContent = "🎮 Du wurdest zu einem Spiel eingeladen!";

    // Hide game code section and show join section
    document.getElementById("gameCodeSection").style.display = "none";
    document.getElementById("joinSection").style.display = "block";

    // Focus on name input
    document.getElementById("playerName").focus();

  } catch (error) {
    console.error('Error loading game:', error);
    alert(`Fehler: ${error.message}. Überprüfe den Game Code.`);
  } finally {
    setButtonLoading(loadBtn, false);
  }
}

async function joinGame() {
  if (!gameId) {
    alert("Kein Game Code gefunden. Bitte lade zuerst ein Spiel.");
    return;
  }

  const nameInput = document.getElementById("playerName");
  const name = nameInput.value.trim();

  if (!name) {
    nameInput.focus();
    alert("Bitte gib einen Namen ein.");
    return;
  }

  const joinBtn = document.querySelector('button[onclick="joinGame()"]');
  setButtonLoading(joinBtn, true);

  try {
    const res = await fetch("/join_game", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, name })
    });

    const data = await res.json();

    if (data.error) {
      alert(data.error);
      setButtonLoading(joinBtn, false);
      return;
    }

    // Hide join controls and show waiting message
    document.getElementById("playerName").style.display = "none";
    joinBtn.style.display = "none";
    document.getElementById("muteBtn").style.display = "none";
    document.getElementById("waitingMessage").style.display = "block";

    // Start polling for game start
    const checkStart = setInterval(async () => {
      try {
        const res = await fetch(`/game_state/${gameId}/${data.player_id}`);
        const state = await res.json();

        if (state.game_status === "started") {
          clearInterval(checkStart);
          window.location.href = `/game?game_id=${gameId}&player_id=${data.player_id}`;
        }
      } catch (error) {
        console.error('Error checking game state:', error);
        // Continue polling even if there's an error
      }
    }, 3000);

  } catch (error) {
    console.error('Error joining game:', error);
    alert("Fehler beim Beitreten. Bitte versuche es erneut.");
    setButtonLoading(joinBtn, false);
  }
}

// Improve input experience
document.addEventListener('DOMContentLoaded', () => {
  const gameCodeInput = document.getElementById("gameCodeInput");
  const playerNameInput = document.getElementById("playerName");

  // Game Code Input handlers
  if (gameCodeInput) {
    gameCodeInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        loadGame();
      }
    });

    // Auto-uppercase and focus
    gameCodeInput.addEventListener('input', function(e) {
      e.target.value = e.target.value.toUpperCase();
    });

    // Auto-focus if no game ID is present
    if (!gameId) {
      gameCodeInput.focus();
    }
  }

  // Player Name Input handlers
  if (playerNameInput) {
    playerNameInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        joinGame();
      }
    });

    // Auto-focus if game ID is present
    if (gameId) {
      playerNameInput.focus();
    }
  }
});