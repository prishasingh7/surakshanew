const MAX_MOUSE_EVENTS = 500;
const MAX_KEYBOARD_EVENTS = 200;

function isFiniteNumber(value) {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
}

function toNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function relativeTime(value, sessionStart, fallback = 0) {
  const numericValue = toNumber(value, fallback);

  if (!isFiniteNumber(sessionStart)) {
    return Math.max(0, Math.round(numericValue));
  }

  return Math.max(0, Math.round(numericValue - Number(sessionStart)));
}

function limitRecent(entries, limit) {
  return Array.isArray(entries) ? entries.slice(-limit) : [];
}

function compactObject(value) {
  if (Array.isArray(value)) {
    return value.map(compactObject).filter((entry) => entry !== undefined);
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .map(([key, entry]) => [key, compactObject(entry)])
        .filter(([, entry]) => entry !== undefined)
    );
  }

  if (value === undefined || value === null || Number.isNaN(value)) {
    return undefined;
  }

  return value;
}

function normalizeMouseEvents(mouseEvents, sessionStart) {
  return limitRecent(mouseEvents, MAX_MOUSE_EVENTS)
    .filter((event) => event && isFiniteNumber(event.x) && isFiniteNumber(event.y) && isFiniteNumber(event.t))
    .map((event) => ({
      x: toNumber(event.x),
      y: toNumber(event.y),
      t: relativeTime(event.t, sessionStart)
    }));
}

function normalizeKeyboardEvents(keyboardEvents, sessionStart, fallbackUpTime) {
  return limitRecent(keyboardEvents, MAX_KEYBOARD_EVENTS)
    .filter((event) => event && typeof event.key === "string" && isFiniteNumber(event.down))
    .map((event) => {
      const down = relativeTime(event.down, sessionStart);
      const up = relativeTime(event.up ?? fallbackUpTime ?? event.down, sessionStart, down);

      return {
        key: event.key,
        down,
        up: Math.max(down, up)
      };
    });
}

function normalizeDevice(device = {}) {
  const screen = Array.isArray(device.screen) ? device.screen : [];

  return compactObject({
    userAgent: String(device.userAgent || ""),
    screen: [
      Math.max(0, Math.round(toNumber(screen[0]))),
      Math.max(0, Math.round(toNumber(screen[1])))
    ],
    timezone: String(device.timezone || ""),
    webdriver: typeof device.webdriver === "boolean" ? device.webdriver : undefined,
    pluginsCount: isFiniteNumber(device.pluginsCount) ? Math.max(0, Math.round(toNumber(device.pluginsCount))) : undefined,
    languagesCount: isFiniteNumber(device.languagesCount) ? Math.max(0, Math.round(toNumber(device.languagesCount))) : undefined,
    hardwareConcurrency: isFiniteNumber(device.hardwareConcurrency) ? Math.max(0, Math.round(toNumber(device.hardwareConcurrency))) : undefined,
    deviceMemory: isFiniteNumber(device.deviceMemory) ? toNumber(device.deviceMemory) : undefined,
    maxTouchPoints: isFiniteNumber(device.maxTouchPoints) ? Math.max(0, Math.round(toNumber(device.maxTouchPoints))) : undefined,
    refreshRate: isFiniteNumber(device.refreshRate) ? toNumber(device.refreshRate) : undefined,
    webglVendor: String(device.webglVendor || ""),
    webglRenderer: String(device.webglRenderer || ""),
    platform: String(device.platform || "")
  });
}

export function buildPayload(telemetryState) {
  const now = performance.now();
  const sessionStart = telemetryState.sessionStart;
  const payload = {
    mouse: normalizeMouseEvents(telemetryState.mouse, sessionStart),
    keyboard: normalizeKeyboardEvents(telemetryState.keyboard, sessionStart, now),
    device: normalizeDevice(telemetryState.device),
    honeypotFilled: Boolean(telemetryState.honeypotFilled),
    timeToFirstInput: telemetryState.timeToFirstInput == null
      ? undefined
      : Math.max(0, Math.round(toNumber(telemetryState.timeToFirstInput))),
    timeToSubmit: telemetryState.timeToSubmit == null
      ? undefined
      : Math.max(0, Math.round(toNumber(telemetryState.timeToSubmit))),
    pasteCount: Math.max(0, Math.round(toNumber(telemetryState.pasteCount)))
  };

  return compactObject(payload);
}
