// static/js/create_game.js

let gameId = null;
let playerId = null;
let isMaster = false;
let joinLink = '';

const bgMusic = document.getElementById("bgMusic");
const muteBtn = document.getElementById("muteBtn");

function toggleMute() {
  bgMusic.muted = !bgMusic.muted;
  muteBtn.innerText = bgMusic.muted ? "🔇" : "🔈";
}

// Custom Toast System
function showToast(message, type = 'success', icon = '✅') {
  const existingToasts = document.querySelectorAll('.toast');
  existingToasts.forEach(toast => toast.remove());

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div class="toast-message">${message}</div>
    <button class="toast-close" onclick="this.parentElement.remove()">OK</button>
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.remove();
    }
  }, 4000);
}

function showErrorToast(message) {
  showToast(message, 'error', '❌');
}

function showSuccessToast(message) {
  showToast(message, 'success', '✅');
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

// Game Code Copy Functionality
async function copyGameCode() {
  if (!gameId) {
    showErrorToast("Kein Spiel-Code verfügbar!");
    return;
  }

  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(gameId);
    } else {
      // Fallback für ältere Browser
      const gameCodeInput = document.getElementById('gameCodeValue');
      if (gameCodeInput) {
        gameCodeInput.select();
        gameCodeInput.setSelectionRange(0, 99999); // Für mobile
        document.execCommand('copy');
      } else {
        // Weitere Fallback-Option
        const textArea = document.createElement('textarea');
        textArea.value = gameId;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
    }

    showSuccessToast("Spiel-Code kopiert! 📋");

  } catch (error) {
    console.error('Copy failed:', error);
    showErrorToast("Code: " + gameId + " (manuell kopieren)");
  }
}

async function createGame() {
  const nameInput = document.getElementById("playerName");
  const name = nameInput.value.trim();

  if (!name) {
    nameInput.focus();
    showErrorToast("Bitte gib einen Namen ein!");
    return;
  }

  const createBtn = document.querySelector('button[onclick="createGame()"]');
  setButtonLoading(createBtn, true);

  try {
    const res = await fetch("/create_game", { method: "POST" });
    const data = await res.json();
    gameId = data.game_id;

    const joinRes = await fetch("/join_game", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, name })
    });
    const joinData = await joinRes.json();

    if (joinData.error) {
      throw new Error(joinData.error);
    }

    playerId = joinData.player_id;
    isMaster = joinData.is_master;

    // Show game sections
    document.getElementById("setupSection").classList.add("hidden");
    document.getElementById("joinLinkBox").classList.remove("hidden");
    document.getElementById("lobbyBox").classList.remove("hidden");

    // Update game code display
    document.getElementById("gameCodeValue").value = gameId;

    // Generate QR Code and link
    joinLink = `${window.location.origin}/games/${gameId}/join`;

    new QRCode(document.getElementById("qrcode"), {
      text: joinLink,
      width: 200,
      height: 200,
      colorDark: "#1d1b3a",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.H
    });

    showSuccessToast("Spiel erfolgreich erstellt!");
    refreshLobby();
    setInterval(refreshLobby, 3000);

  } catch (error) {
    console.error('Error creating game:', error);
    showErrorToast(`Fehler beim Erstellen: ${error.message}`);
  } finally {
    setButtonLoading(createBtn, false);
  }
}

async function refreshLobby() {
  try {
    const res = await fetch(`/players_in_game/${gameId}`);
    const data = await res.json();

    const playerListContainer = document.getElementById("playerList");
    playerListContainer.innerHTML = "";

    data.players.forEach(p => {
      const playerDiv = document.createElement("div");
      playerDiv.className = `lobby-player ${p.is_master ? 'master' : ''}`;

      const adminIcon = p.is_master ? "👑 " : "";
      const roleStatus = p.role === "pending" ? "⏳ wartet" : (p.role === "impostor" ? "🕵️" : "✅");

      playerDiv.innerHTML = `
        <div class="player-name">${adminIcon}${p.name}</div>
        <div class="player-status">${roleStatus}</div>
      `;

      playerListContainer.appendChild(playerDiv);
    });

    const startBtn = document.getElementById("startButton");
    const hint = document.getElementById("hint");

    if (isMaster) {
      if (data.players.length >= 3) {
        startBtn.disabled = false;
        hint.style.display = "none";
      } else {
        startBtn.disabled = true;
        hint.style.display = "block";
      }
    }

    // Check if game started
    const state = await fetch(`/game_state/${gameId}/${playerId}`).then(r => r.json());
    if (state.game_status === "started") {
      window.location.href = `/game?game_id=${gameId}&player_id=${playerId}`;
    }
  } catch (error) {
    console.error('Error refreshing lobby:', error);
  }
}

async function startGame() {
  const startBtn = document.getElementById("startButton");
  setButtonLoading(startBtn, true);

  try {
    const res = await fetch(`/start_game`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId })
    });

    const data = await res.json();
    if (data.status === "started") {
      showSuccessToast("Spiel wird gestartet...");
      setTimeout(() => {
        window.location.href = `/game?game_id=${gameId}&player_id=${playerId}`;
      }, 1000);
    } else {
      throw new Error(data.error || "Unbekannter Fehler");
    }
  } catch (error) {
    console.error('Error starting game:', error);
    showErrorToast(`Fehler beim Starten: ${error.message}`);
    setButtonLoading(startBtn, false);
  }
}

async function copyAndShareLink() {
  const copyBtn = document.querySelector('.copy-btn');
  setButtonLoading(copyBtn, true);

  try {
    if (navigator.share) {
      await navigator.share({
        title: 'SusWords - Finde den Impostor!',
        text: 'Komm in mein SusWords Spiel!',
        url: joinLink
      });
      showSuccessToast("Link geteilt!");
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(joinLink);
      showSuccessToast("Link in Zwischenablage kopiert!");
    } else {
      const textArea = document.createElement('textarea');
      textArea.value = joinLink;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      showSuccessToast("Link kopiert!");
    }
  } catch (error) {
    console.error('Error sharing:', error);
    showErrorToast("Konnte Link nicht teilen. Kopiere ihn manuell.");
  } finally {
    setButtonLoading(copyBtn, false);
  }
}

// Improve input experience
document.addEventListener('DOMContentLoaded', () => {
  const playerNameInput = document.getElementById("playerName");

  if (playerNameInput) {
    playerNameInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        createGame();
      }
    });

    // Auto-focus on name input
    playerNameInput.focus();
  }
});