import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  transcribeAudio,
  validateAudioFile,
} from "./api.js";

function validFile() {
  return new File([new Uint8Array([1, 2, 3])], "call.wav", { type: "audio/wav" });
}

describe("frontend API service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends the recording as multipart FormData without setting Content-Type", async () => {
    const responseBody = {
      success: true,
      transcript: "verified transcript",
      model: "prisma-v3.0",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(responseBody),
    });

    await expect(transcribeAudio(validFile())).resolves.toEqual(responseBody);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({ Accept: "application/json" });
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("audio").name).toBe("call.wav");
  });

  it("returns a useful error for a backend error envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 503,
      json: vi.fn().mockResolvedValue({
        success: false,
        error: { code: "GNANI_NOT_CONFIGURED", message: "Configure the backend key." },
      }),
    });

    await expect(transcribeAudio(validFile())).rejects.toMatchObject({
      status: 503,
      code: "GNANI_NOT_CONFIGURED",
      message: "Configure the backend key.",
    });
  });

  it("handles network failure and empty transcription responses", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("offline"));
    await expect(transcribeAudio(validFile())).rejects.toMatchObject({ code: "NETWORK_ERROR" });

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({ success: true }),
    });
    await expect(transcribeAudio(validFile())).rejects.toMatchObject({ code: "EMPTY_RESPONSE" });
  });

  it("validates unsupported and empty files before fetch", () => {
    expect(validateAudioFile(new File(["x"], "call.txt", { type: "text/plain" }))).toMatch(/Unsupported/);
    expect(validateAudioFile(new File([], "call.wav", { type: "audio/wav" }))).toMatch(/empty/);
  });

  it("exposes ApiError as an Error subclass", () => {
    expect(new ApiError("message")).toBeInstanceOf(Error);
  });
});
