const urlParams = new URLSearchParams(window.location.search);
const gameId = urlParams.get("game_id");
const playerId = urlParams.get("player_id");

let playerName = "";
let isImpostor = false;
let isPolling = false;
let isVoting = false;
let gamePollingInterval = null;
let votePollingInterval = null;
let lastGameState = null;
let currentSuspectId = null;
let connectionStatus = "connected";
let retryAttempts = 0;
let maxRetryAttempts = 5;

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

if (!gameId || !playerId) {
  document.getElementById("gameSection").innerHTML =
    "<div id='errorMessage'>Fehler: Game ID oder Player ID fehlt in der URL.</div>";
} else {
  document.addEventListener('DOMContentLoaded', initGame);
}

async function initGame() {
  try {
    await lookupOwnPlayerName();
    await monitorGame();
    startGamePolling();
    setupEventListeners();
  } catch (err) {
    console.error("Fehler beim Initialisieren des Spiels:", err);
    document.getElementById("gameSection").innerHTML =
      `<div id='errorMessage'>Fehler beim Starten des Spiels: ${err.message}</div>`;
    updateConnectionStatus("error");
  }
}

function setupEventListeners() {
  const hintInput = document.getElementById("hint");
  if (hintInput) {
    hintInput.addEventListener("input", updateSubmitButton);
  }

  const closeVoteBtn = document.getElementById("closeVote");
  if (closeVoteBtn) {
    closeVoteBtn.addEventListener("click", hideSusOverlay);
  }

  // Vote buttons als Event-Listener statt onclick
  const voteUpBtn = document.getElementById("voteUpBtn");
  const voteDownBtn = document.getElementById("voteDownBtn");

  if (voteUpBtn) {
    voteUpBtn.onclick = () => castVote('up');
  }
  if (voteDownBtn) {
    voteDownBtn.onclick = () => castVote('down');
  }
}

function startGamePolling() {
  if (gamePollingInterval) clearInterval(gamePollingInterval);
  gamePollingInterval = setInterval(monitorGame, 3000);
}

function updateConnectionStatus(status) {
  const statusElem = document.getElementById("connectionStatus");
  connectionStatus = status;

  statusElem.className = "connection-status";
  switch (status) {
    case "connected":
      statusElem.classList.add("status-connected");
      statusElem.innerText = "Verbunden";
      break;
    case "polling":
      statusElem.classList.add("status-polling");
      statusElem.innerText = "Aktualisiere...";
      break;
    case "error":
      statusElem.classList.add("status-error");
      statusElem.innerText = "Verbindungsfehler";
      break;
  }
}

async function lookupOwnPlayerName() {
  try {
    updateConnectionStatus("polling");
    const res = await fetch(`/players_in_game/${gameId}`);
    if (!res.ok) throw new Error(`Server-Fehler: ${res.status}`);

    const data = await res.json();
    const player = data.players.find(p => p.player_id === playerId);

    if (!player) {
      throw new Error("Spieler nicht im Spiel gefunden");
    }

    playerName = player.name;
    document.getElementById("playerNameBanner").innerText = `🎮 Spieler: ${playerName}`;
    updateConnectionStatus("connected");
    retryAttempts = 0;
    return data;
  } catch (err) {
    console.error("Fehler beim Abrufen des Spielernamens:", err);
    document.getElementById("playerNameBanner").innerHTML =
      `Spieler: <span style="color: #ff5555">Verbindungsfehler</span>`;

    retryAttempts++;
    updateConnectionStatus("error");

    if (retryAttempts <= maxRetryAttempts) {
      console.log(`Versuch ${retryAttempts}/${maxRetryAttempts}: Wiederverbinden in 5 Sekunden...`);
      setTimeout(lookupOwnPlayerName, 5000);
    }

    throw err;
  }
}

async function monitorGame() {
  if (isPolling) return;
  isPolling = true;
  updateConnectionStatus("polling");

  try {
    const res = await fetch(`/game_state/${gameId}/${playerId}`);
    if (!res.ok) throw new Error(`Server-Fehler: ${res.status}`);

    const data = await res.json();

    if (data.game_status === "finished") {
      showGameOverScreen(data);
      clearInterval(gamePollingInterval);
      if (votePollingInterval) clearInterval(votePollingInterval);
      updateConnectionStatus("connected");
      return;
    }

    if (data.status === "eliminated") {
      document.getElementById("gameSection").innerHTML =
        `<div id='errorMessage'>${data.message || "Du wurdest aus dem Spiel entfernt!"}</div>`;
      clearInterval(gamePollingInterval);
      if (votePollingInterval) clearInterval(votePollingInterval);
      updateConnectionStatus("connected");
      return;
    }

    if (!data || data.error) {
      throw new Error(data?.error || "Unbekannter Serverfehler");
    }

    lastGameState = data;

    try {
      const playersRes = await fetch(`/players_in_game/${gameId}`);
      if (!playersRes.ok) throw new Error(`Fehler beim Laden der Spielerliste: ${playersRes.status}`);
      const playersData = await playersRes.json();

      updateGameUI(data, playersData);

      if (data.active_vote) {
        handleActiveVote(data);
      } else {
        if (votePollingInterval) {
          clearInterval(votePollingInterval);
          votePollingInterval = null;
        }

        if (document.getElementById("susOverlay").style.display === "flex") {
          hideSusOverlay();
        }
      }

      updateConnectionStatus("connected");
      retryAttempts = 0;
    } catch (playersErr) {
      console.error("Fehler beim Laden der Spielerliste:", playersErr);
      updateGameUI(data, { players: [] });
      updateConnectionStatus("error");
    }
  } catch (err) {
    console.error("Fehler beim Aktualisieren des Spielstatus:", err);
    document.getElementById("status").innerHTML =
      `<span style="color: #ff5555">Verbindungsfehler: ${err.message}</span>`;

    retryAttempts++;
    updateConnectionStatus("error");

    if (retryAttempts > maxRetryAttempts) {
      console.log(`Zu viele fehlgeschlagene Versuche. Polling wird reduziert.`);
      if (gamePollingInterval) {
        clearInterval(gamePollingInterval);
        gamePollingInterval = setInterval(monitorGame, 10000);
      }
    }
  } finally {
    isPolling = false;
  }
}

function handleActiveVote(data) {
  if (data.active_vote.overlay_hidden) {
    hideSusOverlay();
    setTimeout(async () => {
      try {
        await clearVoteWithRetry();
      } catch (err) {
        console.error("Fehler beim Löschen des Votings:", err);
      }
    }, 500);
    return;
  }

  const hasVotes = Object.keys(data.active_vote.votes || {}).length > 0;
  const hasResult = !!data.active_vote.result;

  if (!hasVotes && !hasResult) {
    return;
  }

  const isPlayerSuspect = data.active_vote.suspect_id === playerId;
  currentSuspectId = data.active_vote.suspect_id;
  const initiatorName = data.active_vote.initiator_name || "Unbekannt";
  const suspectName = data.active_vote.suspect_name || "Unbekannt";

  if (document.getElementById("susOverlay").style.display !== "flex") {
    const hasVoted = data.active_vote.votes && data.active_vote.votes[playerId];
    showSusOverlay(initiatorName, suspectName, isPlayerSuspect, hasVoted);
  }

  if (!votePollingInterval) {
    votePollingInterval = setInterval(async () => {
      try {
        const voteRes = await fetch(`/vote_status/${gameId}/${playerId}`);
        if (!voteRes.ok) throw new Error(`Vote status error: ${voteRes.status}`);

        const voteData = await voteRes.json();
        if (voteData.active) {
          updateVoteDisplay(voteData);
        } else if (document.getElementById("susOverlay").style.display === "flex") {
          hideSusOverlay();
        }
      } catch (err) {
        console.error("Fehler beim Vote-Status:", err);
      }
    }, 1000);
  }
}

function updateVoteDisplay(voteData) {
  if (!voteData || !voteData.active) return;

  const upVotes = voteData.votes.up || 0;
  const downVotes = voteData.votes.down || 0;

  let countElement = document.querySelector(".vote-count");
  if (!countElement) {
    countElement = document.createElement("div");
    countElement.classList.add("vote-count");
    document.getElementById("voteResult").insertAdjacentElement('beforebegin', countElement);
  }
  countElement.innerHTML = `Stand der Abstimmung: 👍 ${upVotes} vs 👎 ${downVotes}`;

  const votesCountElem = document.getElementById("votesCount");
  if (votesCountElem) {
    votesCountElem.textContent = `${voteData.votes_cast}/${voteData.votes_needed}`;
  }

  const voterList = document.getElementById("voterList");
  if (voterList) {
    voterList.innerHTML = "";
    const voters = voteData.voters || {};

    document.getElementById("voteSummary").classList.remove("hidden");

    Object.entries(voters).forEach(([voterId, voterInfo]) => {
      const li = document.createElement("li");
      const voteEmoji = voterInfo.vote === "up" ? "👍" : "👎";
      li.textContent = `${voterInfo.name}: ${voteEmoji}`;
      li.classList.add(voterInfo.vote === "up" ? "voted-up" : "voted-down");
      voterList.appendChild(li);
    });
  }

  // WICHTIG: Check ob alle Votes abgegeben wurden
  const allVotesCompleted = voteData.votes_cast >= voteData.votes_needed;

  if (voteData.result || allVotesCompleted) {
    document.getElementById("voteResult").classList.remove("hidden");
    document.querySelector(".vote-btns").style.display = "none";
    document.getElementById("voteTimer").classList.add("hidden");

    const resultText = voteData.result ? getVoteResultText(voteData.result) : "Abstimmung abgeschlossen";
    document.getElementById("voteResult").innerHTML =
      `${resultText} (👍 ${upVotes} vs 👎 ${downVotes})`;

    if (["impostor_eliminated", "impostor_wins", "player_eliminated"].includes(voteData.result)) {
      showVoteResultNotification(voteData.result);
    }

    // WICHTIG: Overlay automatisch schließen nach Voting-Ende
    console.log("Vote completed, closing overlay in 3 seconds...");
    setTimeout(() => {
      console.log("Hiding overlay and clearing vote...");
      hideSusOverlay();

      // Vote löschen und Game-Status neu laden
      setTimeout(async () => {
        try {
          await clearVoteWithRetry();
          await monitorGame(); // Spiel-Status neu laden
          console.log("Vote cleared, game reloaded");
        } catch (err) {
          console.error("Fehler beim Beenden:", err);
        }
      }, 500);
    }, 3000); // 3 Sekunden anzeigen, dann schließen
  }

  if (voteData.overlay_hidden) {
    hideSusOverlay();
    setTimeout(async () => {
      try {
        await clearVoteWithRetry();
      } catch (err) {
        console.error("Fehler beim Löschen des Votings:", err);
      }
    }, 500);
  }
}

function showVoteResultNotification(result) {
  let message = "";
  let type = "success";

  switch (result) {
    case "impostor_eliminated":
      if (isImpostor) {
        message = "VERLOREN! Du wurdest als Impostor entlarvt!";
        type = "danger";
      } else {
        message = "GEWONNEN! Ihr habt den Impostor gefunden!";
        type = "success";
      }
      break;
    case "impostor_wins":
      if (isImpostor) {
        message = "GEWONNEN! Du hast als Impostor überlebt!";
        type = "success";
      } else {
        message = "VERLOREN! Der Impostor hat überlebt!";
        type = "danger";
      }
      break;
    case "player_eliminated":
      if (isImpostor) {
        message = "ERFOLG! Ein unschuldiger Spieler wurde entfernt!";
        type = "success";
      } else {
        message = "OH NEIN! Ein unschuldiger Spieler wurde entfernt!";
        type = "warning";
      }
      break;
  }

  if (message) {
    showToast(message, type, type === 'success' ? '🏆' : type === 'danger' ? '💀' : '⚠️');
  }
}

function showGameOverScreen(data) {
  const isImpostor = data.your_role === "impostor";
  const impostorWon = data.winner === "impostor";
  const secretWord = data.word || data.your_word || "???";

  let message = "";
  let emoji = "";
  let colorClass = "";

  if (isImpostor) {
    if (impostorWon) {
      if (data.end_reason === "word_guessed") {
        message = "Du hast das Wort erraten und gewonnen!";
        showToast("GEWONNEN! Du hast das geheime Wort erraten!", "success", "🏆");
      } else {
        message = "Du hast gewonnen! Die Spieler konnten dich nicht finden.";
        showToast("GEWONNEN! Du hast alle anderen überlebt!", "success", "🏆");
      }
      emoji = "🏆";
      colorClass = "success";
    } else {
      message = "Game Over! Du wurdest entlarvt.";
      showToast("VERLOREN! Du wurdest als Impostor entlarvt!", "danger", "💀");
      emoji = "🚫";
      colorClass = "danger";
    }
  } else {
    if (impostorWon) {
      if (data.end_reason === "word_guessed") {
        message = "Game Over! Der Impostor hat das Wort erraten.";
        showToast("VERLOREN! Der Impostor hat das Wort erraten!", "danger", "💀");
      } else {
        message = "Game Over! Der Impostor hat gewonnen.";
        showToast("VERLOREN! Der Impostor hat überlebt!", "danger", "💀");
      }
      emoji = "💀";
      colorClass = "danger";
    } else {
      message = "Gratulation! Ihr habt den Impostor gefunden und das Spiel gewonnen!";
      showToast("GEWONNEN! Der Impostor wurde enttarnt!", "success", "🏆");
      emoji = "🏆";
      colorClass = "success";
    }
  }

  document.getElementById("gameSection").innerHTML = `
    <div class="game-over ${colorClass}">
      <h2>${emoji} Spiel beendet ${emoji}</h2>
      <p>${message}</p>
      <p>Das geheime Wort war: <strong>${secretWord}</strong></p>
      <p id="redirectCountdown">Weiterleitung zur Ergebnisseite in <span id="countdown">5</span> Sekunden...</p>
    </div>
  `;

  let countdown = 5;
  const countdownInterval = setInterval(() => {
    countdown--;
    const countdownElem = document.getElementById("countdown");
    if (countdownElem) {
      countdownElem.textContent = countdown;
    }

    if (countdown <= 0) {
      clearInterval(countdownInterval);
      redirectToGameEnded(data);
    }
  }, 1000);
}

function redirectToGameEnded(gameData) {
  const params = new URLSearchParams({
    game_id: gameId,
    player_id: playerId,
    result: gameData.end_reason || "game_ended",
    winner: gameData.winner || "unknown",
    word: gameData.word || gameData.your_word || "???",
    is_impostor: (gameData.your_role === "impostor").toString()
  });

  window.location.href = `/game_ended?${params.toString()}`;
}

function updateGameUI(data, playersData) {
  const currentPlayer = data.current_player;
  const isMyTurn = currentPlayer === data.player_name;
  isImpostor = data.your_role === "impostor";

  document.getElementById("turnInfo").innerHTML =
    `🎯 <b>Aktueller Spieler:</b> ${currentPlayer || '-'}`;

  document.getElementById("status").innerHTML = isImpostor
    ? "🕵️ Du bist der Impostor! Versuche das Wort zu erraten."
    : `🔤 <b>Geheimes Wort:</b> ${data.your_word || '-'}`;

  const input = document.getElementById("hint");
  const btn = document.getElementById("submitBtn");
  document.getElementById("wordSection").classList.toggle("hidden", !isMyTurn);

  const playerMap = {};
  if (playersData && playersData.players) {
    playersData.players.forEach(p => playerMap[p.player_id] = p.name);
  }

  if (isMyTurn) {
    input.disabled = false;
    input.focus();
    updateSubmitButton();
    setupSusButtons(playersData.players || []);
  } else {
    input.disabled = true;
    btn.disabled = true;
    document.getElementById("susAction").innerHTML = "";
  }

  const historyContainer = document.getElementById("historyList");
  historyContainer.innerHTML = "";

  const eliminatedPlayers = data.eliminated_players || [];

  data.history.forEach(entry => {
    const li = document.createElement("li");
    const playerName = playerMap[entry.player_id] || entry.player_id;
    const isEliminated = eliminatedPlayers.includes(entry.player_id) ||
        playersData?.players?.find(p => p.player_id === entry.player_id)?.eliminated;

    if (isEliminated) {
      li.innerHTML = `<strike>${playerName}: ${entry.word}</strike>`;
      li.classList.add("eliminated-player");
    } else {
      li.textContent = `${playerName}: ${entry.word}`;
    }

    historyContainer.appendChild(li);
  });
}

async function clearVoteWithRetry(maxRetries = 3) {
  let attempts = 0;

  while (attempts < maxRetries) {
    try {
      const res = await fetch("/clear_vote", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      console.log("Vote successfully cleared");
      await monitorGame();
      return;
    } catch (err) {
      console.error(`Failed to clear vote (attempt ${attempts + 1}/${maxRetries}):`, err);
      attempts++;

      if (attempts < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 1000 * attempts));
      } else {
        throw err;
      }
    }
  }
}

function updateSubmitButton() {
  const input = document.getElementById("hint");
  const btn = document.getElementById("submitBtn");
  const errorMsg = document.getElementById("errorMessage");
  const charCount = document.getElementById("charCount");

  const word = input.value.trim();
  charCount.textContent = word.length;

  if (word.length === 0) {
    btn.disabled = true;
    errorMsg.classList.add("hidden");
    return;
  }

  if (!/^[\wäöüÄÖÜß]+$/.test(word)) {
    btn.disabled = true;
    errorMsg.innerText = "Bitte nur Buchstaben und Zahlen verwenden";
    errorMsg.classList.remove("hidden");
    return;
  }

  errorMsg.classList.add("hidden");
  btn.disabled = false;
  btn.onclick = () => submitWord(word);
}

async function submitWord(word) {
  if (!word) return;

  const btn = document.getElementById("submitBtn");
  setButtonLoading(btn, true);

  try {
    const res = await fetch(`/submit_word`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        player_id: playerId,
        word: word.trim()
      })
    });

    if (!res.ok) {
      throw new Error(`Server-Fehler: ${res.status}`);
    }

    const data = await res.json();

    if (data.status === "game_over" && data.winner === "impostor") {
      showToast("GEWONNEN! Du hast das geheime Wort erraten!", "success", "🏆");
    }

    document.getElementById("hint").value = "";
    document.getElementById("charCount").textContent = "0";
    await monitorGame();
  } catch (err) {
    console.error("Fehler beim Senden des Wortes:", err);
    showToast(`Fehler beim Senden: ${err.message}`, "danger", "❌");
  } finally {
    setButtonLoading(btn, false);
  }
}

function setupSusButtons(players) {
  if (!players || !Array.isArray(players) || players.length === 0) {
    console.warn("[setupSusButtons] Keine Spieler gefunden");
    return;
  }

  const suspects = players.filter(p =>
    p.player_id !== playerId &&
    !p.eliminated &&
    !lastGameState?.eliminated_players?.includes(p.player_id)
  );

  const container = document.getElementById("susAction");
  container.innerHTML = "<label>🕵️ Verdächtigen:</label>";

  if (suspects.length === 0) {
    container.innerHTML += "<p>Keine weiteren Spieler verfügbar!</p>";
    return;
  }

  console.log("Setting up SUS buttons for:", suspects.length, "players");

  suspects.forEach(p => {
    const btn = document.createElement("button");
    btn.textContent = `SUS ${p.name}`;
    btn.type = "button"; // Wichtig für korrekte Funktion
    btn.addEventListener("click", () => {
      console.log("SUS button clicked for:", p.name);
      if (!isVoting) {
        startVote(p.player_id, p.name);
      } else {
        console.log("Already voting, ignoring click");
      }
    });
    container.appendChild(btn);
  });
}

async function startVote(suspectId, suspectName) {
  if (isVoting) {
    console.log("Already voting, ignoring startVote call");
    return;
  }

  isVoting = true;
  console.log("Starting vote against:", suspectName, suspectId);

  const targetButton = event?.target;
  if (targetButton) {
    setButtonLoading(targetButton, true);
  }

  try {
    updateConnectionStatus("polling");
    const res = await fetch("/start_vote", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        initiator_id: playerId,
        suspect_id: suspectId
      })
    });

    if (!res.ok) {
      throw new Error(`Server-Fehler: ${res.status}`);
    }

    const data = await res.json();
    console.log("Vote start response:", data);

    if (data.status === "vote_started") {
      currentSuspectId = suspectId;
      const initiatorName = data.initiator_name || playerName;
      const finalSuspectName = data.suspect_name || suspectName || "Unbekannt";

      console.log("Vote gestartet:", { initiatorName, finalSuspectName });
      showSusOverlay(initiatorName, finalSuspectName, false, false);
      updateConnectionStatus("connected");
    } else {
      throw new Error(data.error || "Unbekannter Fehler");
    }
  } catch (err) {
    console.error("Fehler beim Starten des Votes:", err);
    showToast(`Fehler beim Starten des Votes: ${err.message}`, "danger", "❌");
    updateConnectionStatus("error");
  } finally {
    if (targetButton) {
      setButtonLoading(targetButton, false);
    }
    isVoting = false;
  }
}

function showSusOverlay(from, to, isPlayerSuspect, hasVoted) {
  console.log("[SUS] Overlay anzeigen:", from, "susst", to);

  document.getElementById("susText").innerText = `${from} SUSST ${to}`;
  document.getElementById("susOverlay").style.display = "flex";
  document.getElementById("voteResult").classList.add("hidden");
  document.getElementById("closeVote").classList.toggle("hidden", isPlayerSuspect);

  if (isPlayerSuspect) {
    document.querySelector(".vote-btns").style.display = "none";
    document.getElementById("voteResult").classList.remove("hidden");
    document.getElementById("voteResult").innerHTML = "Du wirst verdächtigt! Warte auf die Abstimmung...";
  } else if (hasVoted) {
    document.querySelector(".vote-btns").style.display = "none";
    document.getElementById("voteResult").classList.remove("hidden");
    document.getElementById("voteResult").innerHTML = "Du hast bereits abgestimmt!";
  } else {
    document.querySelector(".vote-btns").style.display = "flex";
    document.getElementById("voteUpBtn").disabled = false;
    document.getElementById("voteDownBtn").disabled = false;
  }

  const timerElem = document.getElementById("voteTimer");
  timerElem.classList.remove("hidden");

  let secondsLeft = 15;
  const countdown = setInterval(() => {
    secondsLeft--;

    if (secondsLeft <= 0) {
      clearInterval(countdown);
      timerElem.innerHTML = "Abstimmung wird ausgewertet...";
    } else {
      timerElem.innerHTML = `Zeit zum Abstimmen: ${secondsLeft}s`;

      if (secondsLeft <= 5) {
        timerElem.style.color = "red";
        timerElem.style.fontWeight = "bold";
      }
    }
  }, 1000);

  window.voteTimer = countdown;

  document.getElementById("voteSummary").classList.remove("hidden");
  document.getElementById("voterList").innerHTML = "";
}

function hideSusOverlay() {
  document.getElementById("susOverlay").style.display = "none";
  document.getElementById("voteResult").classList.add("hidden");
  document.getElementById("voteSummary").classList.add("hidden");
  document.getElementById("voteTimer").classList.add("hidden");
  currentSuspectId = null;

  if (window.voteTimer) {
    clearInterval(window.voteTimer);
    window.voteTimer = null;
  }
}

async function castVote(vote) {
  if (currentSuspectId === playerId) {
    showToast("Du kannst nicht über dich selbst abstimmen!", "warning", "⚠️");
    return;
  }

  const upBtn = document.getElementById("voteUpBtn");
  const downBtn = document.getElementById("voteDownBtn");

  setButtonLoading(upBtn, true);
  setButtonLoading(downBtn, true);

  try {
    updateConnectionStatus("polling");
    const res = await fetch("/cast_vote", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        voter_id: playerId,
        vote
      })
    });

    if (!res.ok) {
      throw new Error(`Server-Fehler: ${res.status}`);
    }

    const data = await res.json();

    document.querySelector(".vote-btns").style.display = "none";
    document.getElementById("voteResult").classList.remove("hidden");

    if (data.up_votes !== undefined && data.down_votes !== undefined) {
      let countElement = document.querySelector(".vote-count");
      if (!countElement) {
        countElement = document.createElement("div");
        countElement.classList.add("vote-count");
        document.getElementById("voteResult").insertAdjacentElement('beforebegin', countElement);
      }
      countElement.innerHTML = `Stand der Abstimmung: 👍 ${data.up_votes} vs 👎 ${data.down_votes}`;

      const votesCountElem = document.getElementById("votesCount");
      if (votesCountElem) {
        votesCountElem.textContent = `${data.total_votes}/${data.total_possible_votes}`;
      }
    }

    if (data.status === "vote_completed") {
      const resultText = getVoteResultText(data.result);
      document.getElementById("voteResult").innerHTML =
        `${resultText} (👍 ${data.up_votes} vs 👎 ${data.down_votes})`;

      if (["impostor_eliminated", "impostor_wins", "player_eliminated"].includes(data.result)) {
        showVoteResultNotification(data.result);
      }
    } else {
      document.getElementById("voteResult").innerHTML = "Danke für dein Vote!";
    }

    await monitorGame();
    updateConnectionStatus("connected");
  } catch (err) {
    console.error("Fehler beim Abstimmen:", err);
    showToast(`Fehler beim Abstimmen: ${err.message}`, "danger", "❌");
    updateConnectionStatus("error");
    setButtonLoading(upBtn, false);
    setButtonLoading(downBtn, false);
  }
}

function getVoteResultText(result) {
  switch (result) {
    case "impostor_eliminated": return "Der Impostor wurde entfernt! Spiel vorbei!";
    case "impostor_wins": return "Der Impostor hat gewonnen!";
    case "player_eliminated": return "Spieler wurde entfernt!";
    case "vote_failed": return "Spieler bleibt im Spiel!";
    default: return "Abstimmung abgeschlossen!";
  }
}

// Cleanup when page unloads
window.addEventListener("beforeunload", () => {
  if (gamePollingInterval) clearInterval(gamePollingInterval);
  if (votePollingInterval) clearInterval(votePollingInterval);
});