import { useCallback, useState } from "react";

import { AudioUploadPanel } from "./components/AudioUploadPanel.jsx";
import { CallInfoPanel } from "./components/CallInfoPanel.jsx";
import { EmergencyPanel } from "./components/EmergencyPanel.jsx";
import { SystemStatus } from "./components/SystemStatus.jsx";
import { TopBar } from "./components/TopBar.jsx";
import { TranscriptPanel } from "./components/TranscriptPanel.jsx";
import { useSystemHealth } from "./hooks/useSystemHealth.js";
import { transcribeAudio, analyzeEmergency } from "./services/api.js";
import { parseTranscriptToUtterances } from "./utils/utteranceParser.js";

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
  const [emergencyAnalysis, setEmergencyAnalysis] = useState(null);
  const [emergencyAnalyzing, setEmergencyAnalyzing] = useState(false);
  const [emergencyError, setEmergencyError] = useState("");

  const handleFileSelected = useCallback((file, validationError) => {
    setSelectedFile(file);
    setFileError(validationError || "");
    setTranscriptionError("");
    if (validationError) {
      setTranscriptionStatus("idle");
      setResult(null);
      setEmergencyAnalysis(null);
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!selectedFile || fileError || transcriptionStatus === "uploading") return;

    setTranscriptionStatus("uploading");
    setTranscriptionError("");
    setResult(null);
    setEmergencyAnalysis(null);
    setEmergencyError("");

    try {
      const transcription = await transcribeAudio(selectedFile);
      setResult(transcription);
      setTranscriptionStatus("success");

      // Automatically analyze transcript for emergency indicators
      // Parse transcript into structured utterances with unique IDs
      if (transcription.transcript) {
        setEmergencyAnalyzing(true);
        try {
          const utterances = parseTranscriptToUtterances(
            transcription.transcript,
            "caller",
            {
              language: transcription.detected_language || null,
              confidence: transcription.confidence || null,
              source: "sentence_boundary",
            }
          );
          const analysis = await analyzeEmergency(utterances);
          setEmergencyAnalysis(analysis);
        } catch (error) {
          setEmergencyError(error.message || "Emergency analysis failed.");
        } finally {
          setEmergencyAnalyzing(false);
        }
      }
    } catch (error) {
      setTranscriptionError(error.message || "The transcription request failed.");
      setTranscriptionStatus("error");
    }
  }, [fileError, selectedFile, transcriptionStatus]);

  const handleEmergencyConfirm = useCallback(() => {
    // In a real system, this would log the operator acknowledgment
    // and potentially trigger next steps in the protocol
    console.log("Operator acknowledged emergency detection at:", new Date().toISOString());
  }, []);

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
          <EmergencyPanel
            analysis={emergencyAnalysis}
            onConfirm={handleEmergencyConfirm}
            isAnalyzing={emergencyAnalyzing}
            error={emergencyError}
          />
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
