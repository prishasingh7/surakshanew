import { predictBehavior } from "./services/api.js";
import { buildPayload } from "./utils/buildPayload.js";

const MAX_MOUSE_EVENTS = 500;

let mouseData = [];
let keyData = [];
let sessionStart = performance.now();
let firstInputAt = null;
let pasteCount = 0;
let isCapturing = true;
let deviceData = collectDeviceData();

const form = document.getElementById("loginForm");
const honeypotInput = document.getElementById("companyWebsite");
const loginButton = document.getElementById("loginButton");
const botButton = document.getElementById("botButton");
const riskValue = document.getElementById("riskValue");
const riskBar = document.getElementById("riskBar");
const statusMessage = document.getElementById("statusMessage");
const loadingIndicator = document.getElementById("loadingIndicator");

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
  await analyzePayload(payload);
  resetCollection();
}

async function handleBotSimulation() {
  isCapturing = false;
  resetUi();

  const botSessionStart = performance.now();
  const mouse = generateBotMouseData(botSessionStart);
  const keyboard = generateBotKeyboardData("bot-user", mouse.at(-1)?.t ?? botSessionStart);
  const payload = buildPayload({
    mouse,
    keyboard,
    device: {
      ...collectDeviceData(),
      userAgent: "Mozilla/5.0 HeadlessChrome/124.0 Selenium",
      webdriver: true,
      pluginsCount: 0,
      languagesCount: 0,
      webglVendor: "Google Inc.",
      webglRenderer: "Google SwiftShader"
    },
    sessionStart: botSessionStart,
    timeToFirstInput: 40,
    timeToSubmit: 820,
    pasteCount: 0,
    honeypotFilled: false
  });

  console.log("SURAKSHA bot payload:", payload);
  await analyzePayload(payload);
  resetCollection();
}

async function analyzePayload(payload) {
  setLoading(true);

  try {
    const result = await predictBehavior(payload);
    validatePredictionResponse(result);
    displayResult(result);
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
  if (!Number.isFinite(Number(result.risk_score)) || typeof result.message !== "string") {
    throw new Error("Prediction API returned an incomplete response");
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

function displayFallbackError(error) {
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = getFriendlyErrorMessage(error);
  statusMessage.className = "status-message status-suspicious";
}

function getFriendlyErrorMessage(error) {
  if (error?.code === "TIMEOUT") {
    return "Prediction request timed out. Please try again.";
  }

  if (error?.code === "NETWORK") {
    return "Backend is unavailable. Check the API URL or ngrok tunnel.";
  }

  return error?.message || "Unable to complete behavioral analysis.";
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
  riskValue.textContent = "--";
  riskBar.style.width = "0%";
  riskBar.style.backgroundColor = "var(--muted)";
  statusMessage.textContent = "Awaiting login attempt";
  statusMessage.className = "status-message";
}

function generateBotMouseData(startTime) {
  const points = [];

  for (let index = 0; index < 80; index += 1) {
    points.push({
      x: 120 + index * 6,
      y: 180 + index * 3,
      t: startTime + index * 16
    });
  }

  return points;
}

function generateBotKeyboardData(text, startTime) {
  const entries = [];
  const delay = 90;
  const duration = 35;

  text.split("").forEach((key, index) => {
    const down = startTime + 100 + index * delay;

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
