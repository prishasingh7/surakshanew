const API_URL = "http://localhost:8000/predict";
const MAX_MOUSE_EVENTS = 300;

let mouseData = [];
let keyData = [];
let isCapturing = true;

// Lightweight fingerprint data is collected once and reused for each request.
const deviceData = {
  userAgent: navigator.userAgent,
  screen: [window.screen.width, window.screen.height],
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
};

const form = document.getElementById("loginForm");
const loginButton = document.getElementById("loginButton");
const botButton = document.getElementById("botButton");
const riskValue = document.getElementById("riskValue");
const riskBar = document.getElementById("riskBar");
const statusMessage = document.getElementById("statusMessage");
const loadingIndicator = document.getElementById("loadingIndicator");

document.addEventListener("mousemove", captureMouseMovement);
document.addEventListener("keydown", captureKeyDown);
document.addEventListener("keyup", captureKeyUp);
form.addEventListener("submit", handleLogin);
botButton.addEventListener("click", handleBotSimulation);

function captureMouseMovement(event) {
  if (!isCapturing) {
    return;
  }

  // Keep only recent movement so the demo payload stays small.
  mouseData.push({
    x: event.clientX,
    y: event.clientY,
    t: performance.now()
  });

  if (mouseData.length > MAX_MOUSE_EVENTS) {
    mouseData.shift();
  }
}

function captureKeyDown(event) {
  if (!isCapturing || isIgnoredKey(event.key)) {
    return;
  }

  // Each keydown starts a press interval; keyup completes it.
  keyData.push({
    key: event.key,
    down: performance.now(),
    up: null
  });
}

function captureKeyUp(event) {
  if (!isCapturing || isIgnoredKey(event.key)) {
    return;
  }

  const lastOpenEntry = [...keyData].reverse().find((entry) => entry.key === event.key && entry.up === null);

  if (lastOpenEntry) {
    lastOpenEntry.up = performance.now();
  }
}

function isIgnoredKey(key) {
  return ["Tab", "Shift", "Control", "Alt", "Meta"].includes(key);
}

async function handleLogin(event) {
  event.preventDefault();
  isCapturing = false;

  // The backend contract accepts behavioral data only, not credentials.
  const payload = {
    mouse: mouseData,
    keyboard: normalizeKeyboardData(keyData),
    device: deviceData
  };

  console.log("SURAKSHA payload:", payload);
  await analyzePayload(payload);
  resetCollection();
}

async function handleBotSimulation() {
  isCapturing = false;
  resetUi();

  const payload = {
    mouse: generateBotMouseData(),
    keyboard: generateBotKeyboardData("bot-user"),
    device: deviceData
  };

  console.log("SURAKSHA bot payload:", payload);
  await analyzePayload(payload);
  resetCollection();
}

async function analyzePayload(payload) {
  setLoading(true);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const result = await response.json();
    displayResult(result);
  } catch (error) {
    console.error("SURAKSHA API error:", error);
    displayFallbackError();
  } finally {
    setLoading(false);
  }
}

function displayResult(result) {
  const riskScore = clamp(Number(result.risk_score), 0, 1);
  const percent = Math.round(riskScore * 100);
  const state = getRiskState(riskScore);

  riskValue.textContent = `${percent}%`;
  riskBar.style.width = `${percent}%`;
  riskBar.style.backgroundColor = state.color;
  statusMessage.textContent = result.message || state.label;
  statusMessage.className = `status-message ${state.className}`;
}

function displayFallbackError() {
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = "Unable to reach prediction API";
  statusMessage.className = "status-message status-suspicious";
}

function getRiskState(riskScore) {
  if (riskScore > 0.7) {
    return {
      label: "Human",
      className: "status-human",
      color: "var(--human)"
    };
  }

  if (riskScore >= 0.4) {
    return {
      label: "Suspicious",
      className: "status-suspicious",
      color: "var(--suspicious)"
    };
  }

  return {
    label: "Bot",
    className: "status-bot",
    color: "var(--bot)"
  };
}

function setLoading(isLoading) {
  loginButton.disabled = isLoading;
  botButton.disabled = isLoading;
  loadingIndicator.hidden = !isLoading;

  if (isLoading) {
    statusMessage.textContent = "Analyzing behavioral patterns...";
    statusMessage.className = "status-message";
  }
}

function resetCollection() {
  mouseData = [];
  keyData = [];
  isCapturing = true;
}

function resetUi() {
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = "Awaiting login attempt";
  statusMessage.className = "status-message";
}

function normalizeKeyboardData(entries) {
  return entries.map((entry) => ({
    key: entry.key,
    down: entry.down,
    up: entry.up ?? performance.now()
  }));
}

function generateBotMouseData() {
  const points = [];
  const startTime = performance.now();

  // Synthetic bot movement: straight path, constant position deltas, uniform timing.
  for (let index = 0; index < 80; index += 1) {
    points.push({
      x: 120 + index * 6,
      y: 180 + index * 3,
      t: startTime + index * 16
    });
  }

  return points;
}

function generateBotKeyboardData(text) {
  const entries = [];
  const startTime = performance.now() + 100;
  const delay = 90;
  const duration = 35;

  // Synthetic bot typing: fixed delay and identical press duration per key.
  text.split("").forEach((key, index) => {
    const down = startTime + index * delay;

    entries.push({
      key,
      down,
      up: down + duration
    });
  });

  return entries;
}

function clamp(value, min, max) {
  if (Number.isNaN(value)) {
    return min;
  }

  return Math.min(Math.max(value, min), max);
}
