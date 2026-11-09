// In development the API runs on its own port. In production the backend
// serves this site, so API calls go to the same origin.
const DEFAULT_API_BASE_URL = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/$/, "");

// ---------- Access code (public deployments) ----------
// Kept in sessionStorage, so it is forgotten when the tab closes.
const ACCESS_KEY = "naadi-access-code";
export const ACCESS_REQUIRED_EVENT = "naadi:access-required";

export function getAccessCode() {
  try {
    return window.sessionStorage.getItem(ACCESS_KEY) || "";
  } catch {
    return "";
  }
}

export function setAccessCode(code) {
  try {
    window.sessionStorage.setItem(ACCESS_KEY, code);
  } catch {
    // storage blocked; the code then lasts only until reload
  }
}

export function clearAccessCode() {
  try {
    window.sessionStorage.removeItem(ACCESS_KEY);
  } catch {
    // ignore
  }
}

function withAccess(headers = {}) {
  const code = getAccessCode();
  return code ? { ...headers, "X-Naadi-Access": code } : headers;
}

function noticeAccessDenied(status, code) {
  if (status === 401 && (code === "ACCESS_CODE_REQUIRED" || code === "ACCESS_CODE_INVALID")) {
    clearAccessCode();
    window.dispatchEvent(new Event(ACCESS_REQUIRED_EVENT));
  }
}

export const SUPPORTED_AUDIO_EXTENSIONS = [
  ".wav",
  ".mp3",
  ".ogg",
  ".flac",
  ".aac",
  ".m4a",
];

export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

export class ApiError extends Error {
  constructor(message, { status = 0, code = "API_ERROR", body = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

function fileExtension(file) {
  return `.${file.name.split(".").pop()?.toLowerCase() || ""}`;
}

export function validateAudioFile(file) {
  if (!file) {
    return "Choose an audio recording first.";
  }

  if (!SUPPORTED_AUDIO_EXTENSIONS.includes(fileExtension(file))) {
    return "Unsupported audio format. Use WAV, MP3, OGG, FLAC, AAC or M4A.";
  }

  if (file.size === 0) {
    return "The selected audio file is empty.";
  }

  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return "The selected file exceeds the 25 MiB upload limit.";
  }

  return null;
}

async function parseResponse(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    throw new ApiError("The backend returned an unreadable response.", {
      status: response.status,
      code: "MALFORMED_RESPONSE",
    });
  }
  return body;
}

async function requestJson(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: withAccess(options.headers) });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new ApiError(
      "Cannot reach the Naadi backend. Check that FastAPI is running.",
      { code: "NETWORK_ERROR" },
    );
  }

  const body = await parseResponse(response);
  if (!response.ok) {
    const detail = body?.error;
    noticeAccessDenied(response.status, detail?.code);
    throw new ApiError(detail?.message || `Backend request failed (${response.status}).`, {
      status: response.status,
      code: detail?.code || "HTTP_ERROR",
      body,
    });
  }

  return body;
}

export async function getApiHealth({ signal } = {}) {
  const body = await requestJson("/api/v1/health", {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!body || typeof body.status !== "string") {
    throw new ApiError("The backend health response was incomplete.", {
      code: "MALFORMED_RESPONSE",
      body,
    });
  }
  return body;
}

export async function transcribeAudio(file, { signal } = {}) {
  const validationError = validateAudioFile(file);
  if (validationError) {
    throw new ApiError(validationError, { code: "INVALID_AUDIO" });
  }

  const formData = new FormData();
  formData.append("audio", file);

  const body = await requestJson("/api/v1/transcriptions", {
    method: "POST",
    headers: { Accept: "application/json" },
    body: formData,
    signal,
  });

  if (!body || body.success !== true || typeof body.transcript !== "string") {
    throw new ApiError("The backend returned an empty transcription response.", {
      code: "EMPTY_RESPONSE",
      body,
    });
  }

  return body;
}

export async function analyzeEmergency(utterances, { signal } = {}) {
  if (!Array.isArray(utterances) || utterances.length === 0) {
    throw new ApiError("At least one utterance is required for emergency analysis.", {
      code: "INVALID_INPUT",
    });
  }

  const body = await requestJson("/api/v1/emergency/analyze", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ utterances }),
    signal,
  });

  if (!body || typeof body.status !== "string") {
    throw new ApiError("The backend returned an incomplete emergency analysis response.", {
      code: "MALFORMED_RESPONSE",
      body,
    });
  }

  return body;
}

// ---------- Live microphone (WebSocket relay to Gnani Prisma realtime) ----------

/** Absolute ws:// or wss:// URL for the live relay, same origin in production. */
export function streamUrl() {
  if (API_BASE_URL) return `${API_BASE_URL.replace(/^http/i, "ws")}/api/v1/stream`;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/api/v1/stream`;
}

/** fetch() with the access header and the shared network/access handling. */
async function fetchWithAccess(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: withAccess(options.headers) });
  } catch {
    throw new ApiError("Cannot reach the Naadi backend. Check that FastAPI is running.", { code: "NETWORK_ERROR" });
  }
  if (!response.ok) {
    let message = `Backend request failed (${response.status}).`;
    let code = "HTTP_ERROR";
    try {
      const body = await response.json();
      message = body?.error?.message || message;
      code = body?.error?.code || code;
    } catch {
      // keep the generic message
    }
    noticeAccessDenied(response.status, code);
    throw new ApiError(message, { status: response.status, code });
  }
  return response;
}

export async function verifyAccessCode(code) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/access/verify`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
  } catch {
    throw new ApiError("Cannot reach the Naadi backend.", { code: "NETWORK_ERROR" });
  }
  if (response.status === 204) return true;
  let message = "That access code is not right.";
  try {
    message = (await response.json())?.error?.message || message;
  } catch {
    // keep the default message
  }
  throw new ApiError(message, { status: response.status, code: "ACCESS_CODE_INVALID" });
}

// ---------- Timbre CPR coaching prompts ----------

const promptAudioCache = new Map();

export async function listPrompts({ signal } = {}) {
  return requestJson("/api/v1/tts/prompts", { headers: { Accept: "application/json" }, signal });
}

/** Returns an object URL for the prompt's WAV audio, cached for the session. */
export async function getPromptAudioUrl(promptId) {
  if (promptAudioCache.has(promptId)) return promptAudioCache.get(promptId);

  const response = await fetchWithAccess("/api/v1/tts/synthesize-prompt", {
    method: "POST",
    headers: { Accept: "audio/wav, application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ prompt_id: promptId }),
  });
  if ((response.headers.get("content-type") || "").includes("application/json")) {
    throw new ApiError("Could not load the coaching audio.", { status: response.status, code: "TTS_ERROR" });
  }

  const url = URL.createObjectURL(await response.blob());
  promptAudioCache.set(promptId, url);
  return url;
}

// ---------- Saved call log (SQLite) ----------

export async function listCalls({ signal } = {}) {
  return requestJson("/api/v1/calls", { headers: { Accept: "application/json" }, signal });
}

export async function saveCall(record) {
  return requestJson("/api/v1/calls", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(record),
  });
}

export async function updateCall(id, changes) {
  return requestJson(`/api/v1/calls/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

async function requestNoContent(path, options) {
  await fetchWithAccess(path, options);
}

export async function deleteCall(id) {
  return requestNoContent(`/api/v1/calls/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function deleteAllCalls() {
  return requestNoContent("/api/v1/calls", { method: "DELETE" });
}

/** Downloads the call log as CSV (a plain link could not send the access code). */
export async function downloadCallsCsv() {
  const response = await fetchWithAccess("/api/v1/calls/export.csv", { headers: { Accept: "text/csv" } });
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "naadi-calls.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
