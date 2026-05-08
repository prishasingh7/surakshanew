const REQUEST_TIMEOUT_MS = 10000;

function readConfiguredApiUrl() {
  return (
    import.meta.env?.VITE_API_URL ||
    window.__SURAKSHA_API_URL__ ||
    ""
  );
}

function buildPredictUrl() {
  const configuredUrl = readConfiguredApiUrl().trim().replace(/\/+$/, "");

  if (!configuredUrl) {
    throw createApiError("API URL is not configured. Set VITE_API_URL.", {
      code: "CONFIG"
    });
  }

  if (configuredUrl.endsWith("/predict")) {
    return configuredUrl;
  }

  return `${configuredUrl}/predict`;
}

function createApiError(message, details = {}) {
  const error = new Error(message);
  Object.assign(error, details);
  return error;
}

export async function predictBehavior(payload) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(buildPredictUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    if (!response.ok) {
      throw createApiError(`Prediction API returned ${response.status}`, {
        status: response.status
      });
    }

    let result;
    try {
      result = await response.json();
    } catch (error) {
      throw createApiError("Prediction API returned malformed JSON", {
        code: "MALFORMED",
        cause: error
      });
    }

    if (typeof result !== "object" || result === null) {
      throw createApiError("Prediction API returned an invalid response", {
        code: "MALFORMED"
      });
    }

    return result;
  } catch (error) {
    if (error.name === "AbortError") {
      throw createApiError("Prediction request timed out", {
        code: "TIMEOUT",
        cause: error
      });
    }

    if (error instanceof TypeError) {
      throw createApiError("Unable to reach prediction API", {
        code: "NETWORK",
        cause: error
      });
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
