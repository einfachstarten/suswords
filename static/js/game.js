const urlParams = new URLSearchParams(window.location.search);
const gameId = urlParams.get("game_id");
const playerId = urlParams.get("player_id");

let playerName = "";
let isImpostor = false;
let isPolling = false;
let gamePollingInterval = null;
let lastGameState = null;
let connectionStatus = "connected";
let retryAttempts = 0;
let maxRetryAttempts = 5;

const VOTE_PHASES = {
  VOTING: 'voting',
  PROCESSING: 'processing',
  RESULTS: 'results',
  FINISHED: 'finished'
};

let currentVotePhase = null;
let voteTimerInterval = null;
let resultsProgressInterval = null;
let currentSuspectId = null;
let hasVoted = false;
let isPlayerSuspect = false;
let observer = null;

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
    setupMutationObserver();
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
    hintInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter' && !document.getElementById("submitBtn").disabled) {
        const word = hintInput.value.trim();
        if (word) submitWord(word);
      }
    });
  }

  const voteUpBtn = document.getElementById("voteUpBtn");
  const voteDownBtn = document.getElementById("voteDownBtn");

  if (voteUpBtn) {
    voteUpBtn.addEventListener("click", () => castVote('up'));
  }
  if (voteDownBtn) {
    voteDownBtn.addEventListener("click", () => castVote('down'));
  }
}

function setupMutationObserver() {
  observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
        const wordSection = document.getElementById("wordSection");
        const hintInput = document.getElementById("hint");

        if (wordSection && !wordSection.classList.contains("hidden") && hintInput && !hintInput.disabled) {
          setTimeout(() => {
            hintInput.focus();
          }, 100);
        }
      }
    });
  });

  const wordSection = document.getElementById("wordSection");
  if (wordSection) {
    observer.observe(wordSection, { attributes: true });
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
      clearVotingTimers();
      updateConnectionStatus("connected");
      return;
    }

    if (data.status === "eliminated") {
      document.getElementById("gameSection").innerHTML =
        `<div id='errorMessage'>${data.message || "Du wurdest aus dem Spiel entfernt!"}</div>`;
      clearInterval(gamePollingInterval);
      clearVotingTimers();
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

      if (data.active_vote && currentVotePhase === null) {
        await handleActiveVote(data.active_vote);
      } else if (!data.active_vote && currentVotePhase !== null) {
        clearVotingTimers();
        hideVotingOverlay();
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

async function handleActiveVote(voteData) {
  console.log("[VOTE] Active vote detected:", voteData);

  currentSuspectId = voteData.suspect_id;
  isPlayerSuspect = (voteData.suspect_id === playerId);
  hasVoted = voteData.votes && voteData.votes[playerId] !== undefined;

  const initiatorName = voteData.initiator_name || "Unbekannt";
  const suspectName = voteData.suspect_name || "Unbekannt";

  if (voteData.result) {
    await showVoteResults(voteData);
    return;
  }

  await startVotingPhase(initiatorName, suspectName);
}

async function startVotingPhase(initiatorName, suspectName) {
  console.log("[VOTE] Starting voting phase");

  currentVotePhase = VOTE_PHASES.VOTING;

  const susTextElement = document.getElementById("susText");
  if (susTextElement) {
    susTextElement.innerText = `${initiatorName} verdächtigt ${suspectName}`;
  }

  showVotingOverlay();
  showVotingSection();

  if (isPlayerSuspect) {
    showSuspectWaitingSection();
  } else {
    hideSuspectWaitingSection();

    if (hasVoted) {
      showVoteCastConfirmation();
      disableVoteButtons();
    } else {
      hideVoteCastConfirmation();
      enableVoteButtons();
    }
  }

  await startVoteTimer();
}

async function startVoteTimer() {
  console.log("[VOTE] Starting 30-second timer");

  let timeLeft = 30;
  updateTimerDisplay(timeLeft);

  clearVotingTimers();
  voteTimerInterval = setInterval(async () => {
    timeLeft--;
    updateTimerDisplay(timeLeft);

    if (timeLeft % 5 === 0) {
      await checkVoteStatus();
    }

    if (timeLeft <= 0) {
      clearVotingTimers();
      await checkVoteStatus();
    }
  }, 1000);
}

function updateTimerDisplay(seconds) {
  const timerElement = document.getElementById("timerSeconds");
  const suspectTimerElement = document.getElementById("suspectTimerSeconds");

  if (timerElement) {
    timerElement.textContent = seconds;
  }
  if (suspectTimerElement) {
    suspectTimerElement.textContent = seconds;
  }

  const voteTimer = document.getElementById("voteTimer");
  const suspectTimer = document.querySelector(".suspect-timer");

  if (seconds <= 10) {
    if (voteTimer) voteTimer.classList.add("warning");
    if (suspectTimer) suspectTimer.classList.add("warning");
  } else {
    if (voteTimer) voteTimer.classList.remove("warning");
    if (suspectTimer) suspectTimer.classList.remove("warning");
  }
}

async function checkVoteStatus() {
  try {
    const res = await fetch(`/vote_status/${gameId}/${playerId}`);
    if (!res.ok) {
      console.warn("[VOTE] Vote status check failed:", res.status);
      return;
    }

    const voteData = await res.json();

    if (!voteData.active) {
      clearVotingTimers();
      hideVotingOverlay();
      return;
    }

    updateVoteProgress(voteData);

    if (voteData.result) {
      clearVotingTimers();
      await showVoteResults(voteData);
    }
  } catch (err) {
    console.error("[VOTE] Error checking vote status:", err);
  }
}

function updateVoteProgress(voteData) {
  const votesCountElem = document.getElementById("votesCount");
  const votesTotalElem = document.getElementById("votesTotal");
  const progressSection = document.getElementById("voteProgress");

  if (votesCountElem && votesTotalElem) {
    votesCountElem.textContent = voteData.votes_cast || 0;
    votesTotalElem.textContent = voteData.votes_needed || 0;
  }

  if (progressSection && voteData.votes_cast > 0) {
    progressSection.classList.remove("hidden");
  }
}

async function showProcessingPhase() {
  console.log("[VOTE] Showing processing phase");

  currentVotePhase = VOTE_PHASES.PROCESSING;

  hideVotingSection();
  hideSuspectWaitingSection();

  const processingSection = document.getElementById("processingSection");
  if (processingSection) {
    processingSection.classList.remove("hidden");
  }

  return new Promise(resolve => {
    setTimeout(() => {
      const processingSection = document.getElementById("processingSection");
      if (processingSection) {
        processingSection.classList.add("hidden");
      }
      resolve();
    }, 1500);
  });
}

async function showVoteResults(voteData) {
  console.log("[VOTE] Showing vote results:", voteData);

  currentVotePhase = VOTE_PHASES.RESULTS;

  await showProcessingPhase();

  const upVotes = voteData.votes?.up || 0;
  const downVotes = voteData.votes?.down || 0;
  const result = voteData.result;

  const voteNumbersElement = document.getElementById("voteNumbers");
  if (voteNumbersElement) {
    voteNumbersElement.textContent = `👍 ${upVotes} vs 👎 ${downVotes}`;
  }

  const outcomeElement = document.getElementById("voteOutcome");
  if (outcomeElement) {
    const { message, className } = getVoteResultMessage(result);
    outcomeElement.textContent = message;
    outcomeElement.className = `vote-outcome ${className}`;
  }

  showResultsSection();
  showVoteResultNotification(result);

  await startResultsProgress();
}

function getVoteResultMessage(result) {
  switch (result) {
    case "impostor_eliminated":
      if (isImpostor) {
        return { message: "Du wurdest als Impostor entlarvt!", className: "lose" };
      } else {
        return { message: "Der Impostor wurde gefunden! Ihr habt gewonnen!", className: "win" };
      }
    case "impostor_wins":
      if (isImpostor) {
        return { message: "Du hast als Impostor gewonnen!", className: "win" };
      } else {
        return { message: "Der Impostor hat gewonnen!", className: "lose" };
      }
    case "player_eliminated":
      if (isImpostor) {
        return { message: "Ein unschuldiger Spieler wurde entfernt!", className: "win" };
      } else {
        return { message: "Ein unschuldiger Spieler wurde entfernt.", className: "neutral" };
      }
    case "vote_failed":
      return { message: "Abstimmung fehlgeschlagen. Spieler bleibt im Spiel.", className: "neutral" };
    default:
      return { message: "Abstimmung beendet.", className: "neutral" };
  }
}

function showVoteResultNotification(result) {
  let message = "";
  let type = "success";
  let icon = "✅";

  switch (result) {
    case "impostor_eliminated":
      if (isImpostor) {
        message = "VERLOREN! Du wurdest als Impostor entlarvt!";
        type = "danger";
        icon = "💀";
      } else {
        message = "GEWONNEN! Ihr habt den Impostor gefunden!";
        type = "success";
        icon = "🏆";
      }
      break;
    case "impostor_wins":
      if (isImpostor) {
        message = "GEWONNEN! Du hast als Impostor überlebt!";
        type = "success";
        icon = "🏆";
      } else {
        message = "VERLOREN! Der Impostor hat gewonnen!";
        type = "danger";
        icon = "💀";
      }
      break;
    case "player_eliminated":
      if (isImpostor) {
        message = "ERFOLG! Ein unschuldiger Spieler wurde entfernt!";
        type = "success";
        icon = "😈";
      } else {
        message = "Ein unschuldiger Spieler wurde entfernt.";
        type = "warning";
        icon = "⚠️";
      }
      break;
    case "vote_failed":
      message = "Abstimmung fehlgeschlagen.";
      type = "warning";
      icon = "🤷";
      break;
  }

  if (message) {
    showToast(message, type, icon);
  }
}

async function startResultsProgress() {
  console.log("[VOTE] Starting 8-second results progress");

  return new Promise(resolve => {
    let timeLeft = 8;
    const progressFill = document.getElementById("progressFill");
    const countdownElement = document.getElementById("progressCountdown");

    if (countdownElement) {
      countdownElement.textContent = timeLeft;
    }

    clearVotingTimers();
    resultsProgressInterval = setInterval(() => {
      timeLeft--;

      if (countdownElement) {
        countdownElement.textContent = timeLeft;
      }

      if (progressFill) {
        const progress = ((8 - timeLeft) / 8) * 100;
        progressFill.style.width = `${progress}%`;
      }

      if (timeLeft <= 0) {
        clearVotingTimers();
        resolve();
        handleVoteCompletion();
      }
    }, 1000);
  });
}

async function handleVoteCompletion() {
  console.log("[VOTE] Vote completed, handling next action");

  currentVotePhase = VOTE_PHASES.FINISHED;

  try {
    await fetch("/clear_vote", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId })
    });
  } catch (err) {
    console.error("[VOTE] Error clearing vote:", err);
  }

  hideVotingOverlay();

  if (lastGameState && lastGameState.game_status === "finished") {
    return;
  }

  await monitorGame();
}

function showVotingOverlay() {
  const overlay = document.getElementById("susOverlay");
  if (overlay) {
    overlay.style.display = "flex";
  }
}

function hideVotingOverlay() {
  const overlay = document.getElementById("susOverlay");
  if (overlay) {
    overlay.style.display = "none";
  }

  currentVotePhase = null;
  currentSuspectId = null;
  hasVoted = false;
  isPlayerSuspect = false;
}

function showVotingSection() {
  hideAllVotingSections();
  const votingSection = document.getElementById("votingSection");
  if (votingSection) {
    votingSection.classList.remove("hidden");
  }
}

function showSuspectWaitingSection() {
  hideAllVotingSections();
  const suspectSection = document.getElementById("suspectWaitingSection");
  if (suspectSection) {
    suspectSection.classList.remove("hidden");
  }
}

function showResultsSection() {
  hideAllVotingSections();
  const resultsSection = document.getElementById("resultsSection");
  if (resultsSection) {
    resultsSection.classList.remove("hidden");
  }
}

function hideAllVotingSections() {
  const sections = ["votingSection", "processingSection", "resultsSection", "suspectWaitingSection"];
  sections.forEach(sectionId => {
    const section = document.getElementById(sectionId);
    if (section) {
      section.classList.add("hidden");
    }
  });
}

function hideSuspectWaitingSection() {
  const suspectSection = document.getElementById("suspectWaitingSection");
  if (suspectSection) {
    suspectSection.classList.add("hidden");
  }
}

function showVoteCastConfirmation() {
  const confirmation = document.getElementById("voteCastConfirmation");
  if (confirmation) {
    confirmation.classList.remove("hidden");
  }
}

function hideVoteCastConfirmation() {
  const confirmation = document.getElementById("voteCastConfirmation");
  if (confirmation) {
    confirmation.classList.add("hidden");
  }
}

function enableVoteButtons() {
  const upBtn = document.getElementById("voteUpBtn");
  const downBtn = document.getElementById("voteDownBtn");

  if (upBtn) upBtn.disabled = false;
  if (downBtn) downBtn.disabled = false;
}

function disableVoteButtons() {
  const upBtn = document.getElementById("voteUpBtn");
  const downBtn = document.getElementById("voteDownBtn");

  if (upBtn) upBtn.disabled = true;
  if (downBtn) downBtn.disabled = true;
}

function clearVotingTimers() {
  if (voteTimerInterval) {
    clearInterval(voteTimerInterval);
    voteTimerInterval = null;
  }
  if (resultsProgressInterval) {
    clearInterval(resultsProgressInterval);
    resultsProgressInterval = null;
  }
}

function cleanupObservers() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
}

async function castVote(vote) {
  if (currentVotePhase !== VOTE_PHASES.VOTING) {
    console.log("[VOTE] Cannot vote - not in voting phase");
    return;
  }

  if (isPlayerSuspect) {
    showToast("Du kannst nicht über dich selbst abstimmen!", "warning", "⚠️");
    return;
  }

  if (hasVoted) {
    showToast("Du hast bereits abgestimmt!", "warning", "⚠️");
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
    console.log("[VOTE] Vote cast response:", data);

    hasVoted = true;

    showVoteCastConfirmation();
    disableVoteButtons();

    if (data.total_votes !== undefined && data.total_possible_votes !== undefined) {
      updateVoteProgress({
        votes_cast: data.total_votes,
        votes_needed: data.total_possible_votes
      });
    }

    updateConnectionStatus("connected");
  } catch (err) {
    console.error("Fehler beim Abstimmen:", err);
    showToast(`Fehler beim Abstimmen: ${err.message}`, "danger", "❌");
    updateConnectionStatus("error");
  } finally {
    setButtonLoading(upBtn, false);
    setButtonLoading(downBtn, false);
  }
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
    btn.type = "button";
    btn.addEventListener("click", () => {
      console.log("SUS button clicked for:", p.name);
      if (currentVotePhase === null) {
        startVote(p.player_id, p.name);
      } else {
        console.log("Already in voting phase, ignoring click");
  suspects.forEach(p => {
    const btn = document.createElement("button");
    btn.textContent = `SUS ${p.name}`;
    btn.type = "button";
    btn.addEventListener("click", () => {
      console.log("SUS button clicked for:", p.name);
      if (currentVotePhase === null) {
        startVote(p.player_id, p.name);
      } else {
        console.log("Already in voting phase, ignoring click");
        showToast("Es läuft bereits eine Abstimmung!", "warning", "⚠️");
      }
    });
    container.appendChild(btn);
  });
}

async function startVote(suspectId, suspectName) {
  if (currentVotePhase !== null) {
    console.log("Already in voting phase, ignoring startVote call");
    showToast("Es läuft bereits eine Abstimmung!", "warning", "⚠️");
    return;
  }

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
      const initiatorName = data.initiator_name || playerName;
      const finalSuspectName = data.suspect_name || suspectName || "Unbekannt";

      console.log("Vote gestartet:", { initiatorName, finalSuspectName });

      currentSuspectId = suspectId;
      isPlayerSuspect = false;
      hasVoted = false;

      await startVotingPhase(initiatorName, finalSuspectName);
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

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && currentVotePhase !== null) {
    checkVoteStatus();
  }
});

window.addEventListener("beforeunload", (e) => {
  if (gamePollingInterval) clearInterval(gamePollingInterval);
  clearVotingTimers();
  cleanupObservers();

  if (currentVotePhase === VOTE_PHASES.VOTING && !hasVoted) {
    e.preventDefault();
    e.returnValue = "Du hast noch nicht abgestimmt! Wirklich verlassen?";
    return e.returnValue;
  }
});

console.log("[GAME] New voting system initialized successfully!");