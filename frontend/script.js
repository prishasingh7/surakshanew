import { predictBehavior } from "./services/api.js";
import { buildPayload } from "./utils/buildPayload.js";

const MAX_MOUSE_EVENTS = 500;
const BOT_SESSION_DATA_URL = "/bot-sessions.json";

let mouseData = [];
let keyData = [];
let sessionStart = performance.now();
let firstInputAt = null;
let pasteCount = 0;
let isCapturing = true;
let deviceData = collectDeviceData();
let botSessionCache = null;

const form = document.getElementById("loginForm");
const honeypotInput = document.getElementById("companyWebsite");
const loginButton = document.getElementById("loginButton");
const botButton = document.getElementById("botButton");
const classificationBadge = document.getElementById("classificationBadge");
const riskValue = document.getElementById("riskValue");
const riskBar = document.getElementById("riskBar");
const statusMessage = document.getElementById("statusMessage");
const loadingIndicator = document.getElementById("loadingIndicator");
const reasonsPanel = document.getElementById("reasonsPanel");
const reasonsList = document.getElementById("reasonsList");
const botSignalsPanel = document.getElementById("botSignalsPanel");
const botSignalsList = document.getElementById("botSignalsList");

document.addEventListener("mousemove", captureMouseMovement);
document.addEventListener("keydown", captureKeyDown);
document.addEventListener("keyup", captureKeyUp);
document.addEventListener("paste", capturePaste);
form.addEventListener("submit", handleLogin);
botButton.addEventListener("click", handleBotSimulation);

estimateRefreshRate().then((refreshRate) => {
  deviceData = {
    ...deviceData,
    refreshRate
  };
});

function captureMouseMovement(event) {
  if (!isCapturing) {
    return;
  }

  markFirstInput();
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

  markFirstInput();
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

function capturePaste() {
  if (!isCapturing) {
    return;
  }

  markFirstInput();
  pasteCount += 1;
}

function markFirstInput() {
  if (firstInputAt === null) {
    firstInputAt = performance.now();
  }
}

function isIgnoredKey(key) {
  return ["Tab", "Shift", "Control", "Alt", "Meta"].includes(key);
}

async function handleLogin(event) {
  event.preventDefault();
  isCapturing = false;

  const telemetryState = getTelemetryState();
  const payload = buildPayload(telemetryState);

  console.log("SURAKSHA payload:", payload);
  await analyzePayload(payload, {
    source: "human"
  });
  resetCollection();
}

async function handleBotSimulation() {
  isCapturing = false;
  resetUi();

  try {
    const botSession = await pickRandomBotSession();
    const payload = buildPayload({
      mouse: botSession.mouse,
      keyboard: botSession.keyboard,
      device: botSession.device,
      sessionStart: 0,
      timeToFirstInput: estimateTimeToFirstInput(botSession),
      timeToSubmit: estimateTimeToSubmit(botSession),
      pasteCount: estimatePasteCount(botSession),
      honeypotFilled: false
    });

    console.log("SURAKSHA dataset bot payload:", payload);
    await analyzePayload(payload, {
      source: "bot-simulation",
      botSignals: describeBotSession(botSession, payload)
    });
  } catch (error) {
    console.error("SURAKSHA bot session error:", error);
    displayFallbackError(error);
  } finally {
    resetCollection();
  }
}

async function analyzePayload(payload, context = {}) {
  setLoading(true);
  clearAnalysisDetails();

  try {
    const result = await predictBehavior(payload);
    validatePredictionResponse(result);
    displayResult(result, context);
  } catch (error) {
    console.error("SURAKSHA API error:", error);
    displayFallbackError(error);
  } finally {
    setLoading(false);
  }
}

function getTelemetryState() {
  const now = performance.now();

  return {
    mouse: mouseData,
    keyboard: keyData,
    device: deviceData,
    sessionStart,
    honeypotFilled: Boolean(honeypotInput?.value.trim()),
    timeToFirstInput: firstInputAt === null ? undefined : firstInputAt - sessionStart,
    timeToSubmit: now - sessionStart,
    pasteCount
  };
}

function collectDeviceData() {
  const webglInfo = getWebglInfo();

  return {
    userAgent: navigator.userAgent,
    screen: [window.screen.width, window.screen.height],
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    webdriver: Boolean(navigator.webdriver),
    pluginsCount: navigator.plugins?.length ?? 0,
    languagesCount: navigator.languages?.length ?? (navigator.language ? 1 : 0),
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory,
    maxTouchPoints: navigator.maxTouchPoints,
    webglVendor: webglInfo.vendor,
    webglRenderer: webglInfo.renderer,
    platform: navigator.platform
  };
}

function getWebglInfo() {
  const canvas = document.createElement("canvas");
  const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");

  if (!gl) {
    return {
      vendor: "",
      renderer: ""
    };
  }

  const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");

  return {
    vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
    renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
  };
}

function estimateRefreshRate() {
  return new Promise((resolve) => {
    const samples = [];
    let previousTime = performance.now();

    function sample(currentTime) {
      samples.push(currentTime - previousTime);
      previousTime = currentTime;

      if (samples.length < 8) {
        window.requestAnimationFrame(sample);
        return;
      }

      const averageFrameTime = samples.reduce((total, value) => total + value, 0) / samples.length;
      resolve(Math.round(1000 / averageFrameTime));
    }

    window.requestAnimationFrame(sample);
  });
}

function validatePredictionResponse(result) {
  const hasValidScore = Number.isFinite(Number(result?.risk_score));
  const hasValidClassification = typeof result?.is_human === "boolean";
  const hasValidMessage = typeof result?.message === "string";

  if (!hasValidScore || !hasValidClassification || !hasValidMessage) {
    const error = new Error("Prediction API returned an incomplete response");
    error.code = "MALFORMED";
    throw error;
  }
}

function displayResult(result, context = {}) {
  const riskScore = clamp(Number(result.risk_score), 0, 1);
  const percent = Math.round(riskScore * 100);
  const state = getRiskState(riskScore, result.is_human);
  const reasons = Array.isArray(result.reasons) ? result.reasons : [];

  classificationBadge.textContent = state.label;
  classificationBadge.className = `classification-badge ${state.badgeClass}`;
  riskValue.textContent = `${percent}%`;
  riskBar.style.width = `${percent}%`;
  riskBar.style.backgroundColor = state.color;
  statusMessage.textContent = result.message || state.label;
  statusMessage.className = `status-message ${state.className}`;
  renderList(reasonsList, reasons);
  reasonsPanel.hidden = reasons.length === 0;

  if (context.source === "bot-simulation" && Array.isArray(context.botSignals)) {
    renderList(botSignalsList, context.botSignals);
    botSignalsPanel.hidden = context.botSignals.length === 0;
  }
}

function displayFallbackError(error) {
  classificationBadge.textContent = "Error";
  classificationBadge.className = "classification-badge classification-error";
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = getFriendlyErrorMessage(error);
  statusMessage.className = "status-message status-suspicious";
  clearAnalysisDetails();
}

function getFriendlyErrorMessage(error) {
  if (error?.code === "CONFIG") {
    return "Frontend API URL is not configured. Set VITE_API_URL.";
  }

  if (error?.code === "TIMEOUT") {
    return "Prediction request timed out. Please try again.";
  }

  if (error?.code === "NETWORK") {
    return "Backend is unavailable. Check the API URL or ngrok tunnel.";
  }

  if (error?.code === "MALFORMED") {
    return "Backend returned an unreadable response. Please retry the analysis.";
  }

  if (error?.code === "BOT_DATA") {
    return "Bot sample data could not be loaded. Please refresh and try again.";
  }

  if (Number.isFinite(Number(error?.status))) {
    return `Backend rejected the request with status ${error.status}.`;
  }

  return error?.message || "Unable to complete behavioral analysis.";
}

function getRiskState(riskScore, isHuman) {
  if (isHuman && riskScore > 0.7) {
    return {
      label: "Human",
      badgeClass: "classification-human",
      className: "status-human",
      color: "var(--human)"
    };
  }

  if (riskScore >= 0.4) {
    return {
      label: "Suspicious",
      badgeClass: "classification-suspicious",
      className: "status-suspicious",
      color: "var(--suspicious)"
    };
  }

  return {
    label: "Bot",
    badgeClass: "classification-bot",
    className: "status-bot",
    color: "var(--bot)"
  };
}

function setLoading(isLoading) {
  loginButton.disabled = isLoading;
  botButton.disabled = isLoading;
  loadingIndicator.hidden = !isLoading;

  if (isLoading) {
    statusMessage.textContent = "Analyzing behavioral biometrics...";
    statusMessage.className = "status-message";
  }
}

function resetCollection() {
  mouseData = [];
  keyData = [];
  sessionStart = performance.now();
  firstInputAt = null;
  pasteCount = 0;
  isCapturing = true;
  deviceData = collectDeviceData();

  if (honeypotInput) {
    honeypotInput.value = "";
  }
}

function resetUi() {
  classificationBadge.textContent = "Awaiting";
  classificationBadge.className = "classification-badge classification-idle";
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = "Awaiting login attempt";
  statusMessage.className = "status-message";
  clearAnalysisDetails();
}

function clearAnalysisDetails() {
  renderList(reasonsList, []);
  renderList(botSignalsList, []);
  reasonsPanel.hidden = true;
  botSignalsPanel.hidden = true;
}

function renderList(listElement, items) {
  listElement.replaceChildren();

  items.filter(Boolean).forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = String(item);
    listElement.appendChild(listItem);
  });
}

async function pickRandomBotSession() {
  const sessions = await loadBotSessions();
  const index = Math.floor(Math.random() * sessions.length);
  return sessions[index];
}

async function loadBotSessions() {
  if (botSessionCache) {
    return botSessionCache;
  }

  const response = await fetch(BOT_SESSION_DATA_URL, {
    cache: "no-store"
  });

  if (!response.ok) {
    const error = new Error("Unable to load bot session dataset.");
    error.code = "BOT_DATA";
    throw error;
  }

  const sessions = await response.json();
  if (!Array.isArray(sessions) || sessions.length === 0) {
    const error = new Error("Bot session dataset is empty or malformed.");
    error.code = "BOT_DATA";
    throw error;
  }

  botSessionCache = sessions.filter((session) => (
    session &&
    Array.isArray(session.mouse) &&
    Array.isArray(session.keyboard) &&
    session.device &&
    typeof session.device === "object"
  ));

  if (botSessionCache.length === 0) {
    const error = new Error("Bot session dataset has no usable sessions.");
    error.code = "BOT_DATA";
    throw error;
  }

  return botSessionCache;
}

function estimateTimeToFirstInput(session) {
  const mouseTimes = session.mouse.map((event) => Number(event.t)).filter(Number.isFinite);
  const keyTimes = session.keyboard.map((event) => Number(event.down)).filter(Number.isFinite);
  const firstTime = Math.min(...mouseTimes, ...keyTimes);
  return Number.isFinite(firstTime) ? firstTime : undefined;
}

function estimateTimeToSubmit(session) {
  const mouseTimes = session.mouse.map((event) => Number(event.t)).filter(Number.isFinite);
  const keyTimes = session.keyboard.map((event) => Number(event.up ?? event.down)).filter(Number.isFinite);
  const lastTime = Math.max(...mouseTimes, ...keyTimes);
  return Number.isFinite(lastTime) ? lastTime : undefined;
}

function estimatePasteCount(session) {
  return session.keyboard.filter((event) => String(event.key).toLowerCase() === "paste").length;
}

function describeBotSession(session, payload) {
  const device = payload.device || {};
  const userAgent = String(device.userAgent || "").toLowerCase();
  const renderer = String(device.webglRenderer || "").toLowerCase();
  const signals = [
    "Random bot session selected from backend dataset",
    `${payload.mouse.length} mouse events and ${payload.keyboard.length} keyboard events`
  ];

  if (userAgent.includes("headless") || userAgent.includes("selenium") || userAgent.includes("playwright")) {
    signals.push("Automation-like user agent present");
  }

  if (device.webdriver) {
    signals.push("Webdriver flag present");
  }

  if (device.pluginsCount === 0) {
    signals.push("Browser reports zero plugins");
  }

  if (device.languagesCount === 0) {
    signals.push("Browser languages are missing");
  }

  if (renderer.includes("swiftshader") || renderer.includes("software")) {
    signals.push("Software-rendered WebGL signal present");
  }

  if (hasLowMouseTimingVariance(payload.mouse)) {
    signals.push("Mouse timing has low variance");
  }

  if (hasStraightMousePath(payload.mouse)) {
    signals.push("Mouse path is unusually straight");
  }

  if (hasLowKeyboardTimingVariance(payload.keyboard)) {
    signals.push("Keyboard timing has low variance");
  }

  if (signals.length === 2) {
    signals.push("Human-like bot sample with subtle behavioral anomalies");
  }

  return signals;
}

function hasLowMouseTimingVariance(mouse) {
  const intervals = mouse.slice(1).map((event, index) => event.t - mouse[index].t);
  return intervals.length >= 8 && standardDeviation(intervals) < 12;
}

function hasLowKeyboardTimingVariance(keyboard) {
  const dwellTimes = keyboard.map((event) => event.up - event.down);
  return dwellTimes.length >= 4 && standardDeviation(dwellTimes) < 10;
}

function hasStraightMousePath(mouse) {
  if (mouse.length < 3) {
    return false;
  }

  const first = mouse[0];
  const last = mouse[mouse.length - 1];
  const straightDistance = Math.hypot(last.x - first.x, last.y - first.y);
  const pathLength = mouse.slice(1).reduce((total, event, index) => {
    const previous = mouse[index];
    return total + Math.hypot(event.x - previous.x, event.y - previous.y);
  }, 0);

  return pathLength > 120 && straightDistance / pathLength > 0.96;
}

function standardDeviation(values) {
  if (values.length < 2) {
    return 0;
  }

  const average = values.reduce((total, value) => total + value, 0) / values.length;
  const variance = values.reduce((total, value) => total + (value - average) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function clamp(value, min, max) {
  if (Number.isNaN(value)) {
    return min;
  }

  return Math.min(Math.max(value, min), max);
}
