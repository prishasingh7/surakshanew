const LABEL_HUMAN = 1;
const TARGET_SESSIONS = 50;
const MAX_MOUSE_EVENTS = 500;

let mouseData = [];
let keyData = [];
let recordedSessions = [];
let sessionStart = performance.now();
let isCapturing = true;

const deviceData = {
  userAgent: navigator.userAgent,
  screen: [window.screen.width, window.screen.height],
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
};

const form = document.getElementById("loginForm");
const participantInput = document.getElementById("participant");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const sessionCount = document.getElementById("sessionCount");
const mouseCount = document.getElementById("mouseCount");
const keyCount = document.getElementById("keyCount");
const targetCount = document.getElementById("targetCount");
const statusMessage = document.getElementById("statusMessage");
const jsonPreview = document.getElementById("jsonPreview");
const resetButton = document.getElementById("resetButton");
const downloadLastButton = document.getElementById("downloadLastButton");
const downloadAllButton = document.getElementById("downloadAllButton");

targetCount.textContent = TARGET_SESSIONS;

document.addEventListener("mousemove", captureMouseMovement);
document.addEventListener("keydown", captureKeyDown);
document.addEventListener("keyup", captureKeyUp);
form.addEventListener("submit", recordSession);
resetButton.addEventListener("click", resetCurrentSession);
downloadLastButton.addEventListener("click", downloadLastSession);
downloadAllButton.addEventListener("click", downloadAllSessions);

updateStats();

function captureMouseMovement(event) {
  if (!isCapturing) {
    return;
  }

  mouseData.push({
    x: event.clientX,
    y: event.clientY,
    t: Math.round(performance.now() - sessionStart)
  });

  if (mouseData.length > MAX_MOUSE_EVENTS) {
    mouseData.shift();
  }

  updateStats();
}

function captureKeyDown(event) {
  if (!isCapturing || isIgnoredKey(event.key)) {
    return;
  }

  keyData.push({
    key: event.key,
    down: Math.round(performance.now() - sessionStart),
    up: null
  });

  updateStats();
}

function captureKeyUp(event) {
  if (!isCapturing || isIgnoredKey(event.key)) {
    return;
  }

  const lastOpenEntry = [...keyData].reverse().find((entry) => entry.key === event.key && entry.up === null);

  if (lastOpenEntry) {
    lastOpenEntry.up = Math.round(performance.now() - sessionStart);
  }

  updateStats();
}

function recordSession(event) {
  event.preventDefault();
  isCapturing = false;
  const participant = participantInput.value;

  const session = buildSessionPayload();
  recordedSessions.push(session);
  jsonPreview.textContent = JSON.stringify(session, null, 2);

  const count = recordedSessions.length;
  statusMessage.textContent = count >= TARGET_SESSIONS
    ? `Target reached: ${count} sessions recorded.`
    : `Session ${count} recorded. Reset and repeat for the next login.`;
  statusMessage.classList.toggle("complete", count >= TARGET_SESSIONS);

  downloadLastButton.disabled = false;
  downloadAllButton.disabled = false;
  sessionCount.textContent = count;

  form.reset();
  participantInput.value = participant;
  resetCurrentSession(false);
  usernameInput.focus();
}

function buildSessionPayload() {
  return {
    mouse: mouseData.map((entry) => ({ ...entry })),
    keyboard: normalizeKeyboardData(keyData),
    device: { ...deviceData },
    label: LABEL_HUMAN
  };
}

function normalizeKeyboardData(entries) {
  const fallbackTime = Math.round(performance.now() - sessionStart);

  return entries.map((entry) => ({
    key: entry.key,
    down: entry.down,
    up: entry.up ?? fallbackTime
  }));
}

function resetCurrentSession(shouldUpdateMessage = true) {
  mouseData = [];
  keyData = [];
  sessionStart = performance.now();
  isCapturing = true;

  if (shouldUpdateMessage) {
    statusMessage.textContent = "Current capture reset. Start the next login attempt.";
    statusMessage.classList.remove("complete");
    jsonPreview.textContent = "{}";
    usernameInput.value = "";
    passwordInput.value = "";
    usernameInput.focus();
  }

  updateStats();
}

function downloadLastSession() {
  const lastSession = recordedSessions[recordedSessions.length - 1];

  if (!lastSession) {
    return;
  }

  downloadJson(lastSession, getFileName("session"));
}

function downloadAllSessions() {
  downloadJson(recordedSessions, getFileName("all-sessions"));
}

function downloadJson(data, fileName) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

function getFileName(prefix) {
  const participant = participantInput.value.trim().replace(/[^a-z0-9_-]/gi, "-") || "participant";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");

  return `${participant}-${prefix}-${stamp}.json`;
}

function updateStats() {
  mouseCount.textContent = mouseData.length;
  keyCount.textContent = keyData.length;
}

function isIgnoredKey(key) {
  return ["Tab", "Shift", "Control", "Alt", "Meta", "CapsLock", "Escape"].includes(key);
}
