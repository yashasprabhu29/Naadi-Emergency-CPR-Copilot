import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";
import { ApiError, getApiHealth, transcribeAudio } from "./services/api.js";

vi.mock("./services/api.js", async () => {
  const actual = await vi.importActual("./services/api.js");
  return {
    ...actual,
    getApiHealth: vi.fn(),
    transcribeAudio: vi.fn(),
  };
});

const health = {
  status: "ok",
  service: "Naadi",
  version: "0.1.0",
  gnani_api_key_configured: true,
  prisma_model: "prisma-v3.0",
};

function audioFile(name = "call.wav", type = "audio/wav") {
  return new File([new Uint8Array([1, 2, 3])], name, { type });
}

describe("Naadi operator dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getApiHealth.mockResolvedValue(health);
  });

  it("renders operator workspace and real system status", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /understand the call/i })).toBeInTheDocument();
    expect(screen.getByText("Emergency detection engine not yet connected.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Configured")).toBeInTheDocument());
    expect(screen.getByText("Backend online")).toBeInTheDocument();
  });

  it("rejects unsupported files before making an upload request", async () => {
    const user = userEvent.setup();
    render(<App />);
    const input = screen.getByLabelText("Choose audio recording");

    fireEvent.change(input, {
      target: { files: [new File(["not audio"], "call.txt", { type: "text/plain" })] },
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Unsupported audio format");
    expect(screen.getByRole("button", { name: /transcribe staged call/i })).toBeDisabled();
    expect(transcribeAudio).not.toHaveBeenCalled();
  });

  it("shows loading state and renders a successful backend response", async () => {
    const user = userEvent.setup();
    let resolveRequest;
    transcribeAudio.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
    render(<App />);
    await user.upload(screen.getByLabelText("Choose audio recording"), audioFile());
    await user.click(screen.getByRole("button", { name: /transcribe staged call/i }));

    expect(screen.getByText("Sending recording to Prisma…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /transcribing recording/i })).toBeDisabled();

    await act(async () => {
      resolveRequest({
        success: true,
        request_id: "req-frontend-1",
        transcript: "ನನಗೆ chest pain ಇದೆ",
        detected_language_code: "kn-IN",
        model: "prisma-v3.0",
        processing_time: 0.42,
        end_to_end_latency: 0.55,
      });
    });

    expect(await screen.findByText("ನನಗೆ chest pain ಇದೆ")).toBeInTheDocument();
    expect(screen.getByText("req-frontend-1")).toBeInTheDocument();
    expect(screen.getByText("0.42 s")).toBeInTheDocument();
  });

  it("shows backend errors and allows a later retry", async () => {
    const user = userEvent.setup();
    transcribeAudio.mockRejectedValueOnce(new ApiError("Gnani credentials are missing.", {
      status: 503,
      code: "GNANI_NOT_CONFIGURED",
    }));
    render(<App />);
    await user.upload(screen.getByLabelText("Choose audio recording"), audioFile());
    await user.click(screen.getByRole("button", { name: /transcribe staged call/i }));

    expect(await screen.findByText("Gnani credentials are missing.")).toBeInTheDocument();
    expect(screen.getByText("Transcription unavailable")).toBeInTheDocument();
  });

  it("prevents duplicate submissions while a request is pending", async () => {
    const user = userEvent.setup();
    transcribeAudio.mockReturnValue(new Promise(() => {}));
    render(<App />);
    await user.upload(screen.getByLabelText("Choose audio recording"), audioFile());
    const submit = screen.getByRole("button", { name: /transcribe staged call/i });
    await user.click(submit);
    await user.click(submit);

    expect(transcribeAudio).toHaveBeenCalledTimes(1);
  });

  it("shows network failure from the health check without fake data", async () => {
    getApiHealth.mockRejectedValue(new ApiError("Cannot reach the Naadi backend.", {
      code: "NETWORK_ERROR",
    }));
    render(<App />);

    expect(await screen.findByText("Cannot reach the Naadi backend.")).toBeInTheDocument();
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
    expect(screen.getByText("Not configured")).toBeInTheDocument();
  });
});
