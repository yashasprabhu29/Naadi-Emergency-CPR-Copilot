import { useCallback, useState } from "react";

import { AudioUploadPanel } from "./components/AudioUploadPanel.jsx";
import { CallInfoPanel } from "./components/CallInfoPanel.jsx";
import { EmergencyPlaceholder } from "./components/EmergencyPlaceholder.jsx";
import { SystemStatus } from "./components/SystemStatus.jsx";
import { TopBar } from "./components/TopBar.jsx";
import { TranscriptPanel } from "./components/TranscriptPanel.jsx";
import { useSystemHealth } from "./hooks/useSystemHealth.js";
import { transcribeAudio } from "./services/api.js";

function currentCallState(status) {
  if (status === "uploading") return "TRANSCRIBING";
  if (status === "success") return "REVIEW TRANSCRIPT";
  if (status === "error") return "ACTION REQUIRED";
  return "READY FOR INTAKE";
}

export default function App() {
  const { health, status: healthStatus, error: healthError, refresh } = useSystemHealth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [transcriptionStatus, setTranscriptionStatus] = useState("idle");
  const [transcriptionError, setTranscriptionError] = useState("");
  const [result, setResult] = useState(null);
  const [notes, setNotes] = useState("");

  const handleFileSelected = useCallback((file, validationError) => {
    setSelectedFile(file);
    setFileError(validationError || "");
    setTranscriptionError("");
    if (validationError) {
      setTranscriptionStatus("idle");
      setResult(null);
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!selectedFile || fileError || transcriptionStatus === "uploading") return;

    setTranscriptionStatus("uploading");
    setTranscriptionError("");
    setResult(null);
    try {
      const transcription = await transcribeAudio(selectedFile);
      setResult(transcription);
      setTranscriptionStatus("success");
    } catch (error) {
      setTranscriptionError(error.message || "The transcription request failed.");
      setTranscriptionStatus("error");
    }
  }, [fileError, selectedFile, transcriptionStatus]);

  const transcriptPanelError = transcriptionError || fileError;

  return (
    <div className="app-shell">
      <TopBar
        backendStatus={healthStatus}
        prismaConfigured={Boolean(health?.gnani_api_key_configured)}
        callState={currentCallState(transcriptionStatus)}
      />

      <main className="dashboard-main">
        <section className="page-intro">
          <div>
            <p className="eyebrow">OPERATOR CONSOLE / STAGED CALL WORKSPACE</p>
            <h1>Understand the call. Support the response.</h1>
            <p className="page-intro__copy">
              Load a short recording to establish a verified multilingual transcript for human review.
            </p>
          </div>
          <div className="prototype-note">
            <span className="prototype-note__signal" aria-hidden="true" />
            <div><strong>Prototype mode</strong><span>Decision support only · No emergency service connection</span></div>
          </div>
        </section>

        <div className="dashboard-grid dashboard-grid--primary">
          <AudioUploadPanel
            selectedFile={selectedFile}
            onFileSelected={handleFileSelected}
            onSubmit={handleSubmit}
            status={transcriptionStatus}
            error={fileError}
          />
          <TranscriptPanel
            result={result}
            status={transcriptionStatus}
            error={transcriptPanelError}
          />
        </div>

        <div className="dashboard-grid dashboard-grid--secondary">
          <EmergencyPlaceholder />
          <CallInfoPanel notes={notes} onNotesChange={setNotes} />
          <SystemStatus
            healthStatus={healthStatus}
            health={health}
            error={healthError}
            onRefresh={() => refresh()}
          />
        </div>
      </main>

      <footer className="app-footer">
        <span>NAADI / INTERNAL OPERATOR WORKSPACE</span>
        <span>Gnani Prisma REST · Human review required</span>
      </footer>
    </div>
  );
}
