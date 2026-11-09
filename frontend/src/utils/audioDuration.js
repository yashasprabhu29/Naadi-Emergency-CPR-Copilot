export const MAX_REST_DURATION_SECONDS = 30;

function ascii(view, offset) {
  return String.fromCharCode(view.getUint8(offset), view.getUint8(offset + 1), view.getUint8(offset + 2), view.getUint8(offset + 3));
}

/**
 * Duration of a PCM WAV from its header. Streamed WAVs (including Gnani
 * Timbre output) often store 0xFFFFFFFF as the data size, so the real size is
 * capped at the bytes actually present in the file. Returns null if the file
 * is not a readable RIFF/WAVE file.
 */
export async function readWavDuration(file) {
  try {
    const buffer = await file.slice(0, 65536).arrayBuffer();
    const view = new DataView(buffer);
    if (view.byteLength < 12 || ascii(view, 0) !== "RIFF" || ascii(view, 8) !== "WAVE") return null;

    let offset = 12;
    let byteRate = 0;
    while (offset + 8 <= view.byteLength) {
      const id = ascii(view, offset);
      const size = view.getUint32(offset + 4, true);
      const body = offset + 8;
      if (id === "fmt " && body + 12 <= view.byteLength) {
        byteRate = view.getUint32(body + 8, true);
      } else if (id === "data") {
        if (!byteRate) return null;
        const present = Math.max(file.size - body, 0);
        return Math.min(size, present) / byteRate;
      }
      offset = body + size + (size % 2);
    }
    return null;
  } catch {
    return null;
  }
}

/** True when a file named .wav does not start with a RIFF/WAVE header. */
export async function isMislabelledWav(file) {
  if (!file || !/\.wav$/i.test(file.name || "")) return false;
  try {
    const view = new DataView(await file.slice(0, 12).arrayBuffer());
    return view.byteLength < 12 || ascii(view, 0) !== "RIFF" || ascii(view, 8) !== "WAVE";
  } catch {
    return false;
  }
}

/**
 * Read an audio file's duration in the browser without uploading it.
 * Resolves to seconds, or null when the browser cannot read the file
 * (the backend and Gnani still validate it in that case).
 */
export async function readAudioDuration(file, timeoutMs = 4000) {
  if (file && /\.wav$/i.test(file.name || "")) {
    const wavSeconds = await readWavDuration(file);
    if (wavSeconds != null) return wavSeconds;
  }
  return readMediaDuration(file, timeoutMs);
}

function readMediaDuration(file, timeoutMs) {
  return new Promise((resolve) => {
    if (
      !file ||
      typeof window === "undefined" ||
      typeof URL?.createObjectURL !== "function" ||
      typeof Audio !== "function"
    ) {
      resolve(null);
      return;
    }

    let url;
    try {
      url = URL.createObjectURL(file);
    } catch {
      resolve(null);
      return;
    }

    const audio = new Audio();
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      audio.removeAttribute("src");
      URL.revokeObjectURL(url);
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), timeoutMs);

    audio.preload = "metadata";
    audio.addEventListener("loadedmetadata", () => {
      const seconds = audio.duration;
      finish(Number.isFinite(seconds) && seconds > 0 ? seconds : null);
    });
    audio.addEventListener("error", () => finish(null));
    audio.src = url;
  });
}

export function formatDuration(seconds) {
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return minutes > 0 ? `${minutes} min ${rest} s` : `${rest} s`;
}
