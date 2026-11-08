const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, "");

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
    response = await fetch(`${API_BASE_URL}${path}`, options);
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
