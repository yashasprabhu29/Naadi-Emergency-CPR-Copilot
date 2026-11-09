import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AudioUploadPanel } from "../components/AudioUploadPanel.jsx";
import { CallInfoPanel } from "../components/CallInfoPanel.jsx";
import { CallSteps } from "../components/CallSteps.jsx";
import { CprCoach } from "../components/CprCoach.jsx";
import { EmergencyPanel } from "../components/EmergencyPanel.jsx";
import { LiveMicPanel } from "../components/LiveMicPanel.jsx";
import { PulseTrace } from "../components/PulseTrace.jsx";
import { SystemStatus } from "../components/SystemStatus.jsx";
import { TranscriptPanel } from "../components/TranscriptPanel.jsx";
import { useLiveCall } from "../hooks/useLiveCall.js";
import { analyzeEmergency, saveCall, transcribeAudio } from "../services/api.js";
import { SITE } from "../site.js";
import { formatDuration, isMislabelledWav, MAX_REST_DURATION_SECONDS, readAudioDuration } from "../utils/audioDuration.js";
import { parseTranscriptToUtterances } from "../utils/utteranceParser.js";

export function callStateLabel(transcriptionStatus, analysis) {
  if (transcriptionStatus === "live") return analysis?.status === "potential_emergency" ? "Possible arrest" : "Live call";
  if (transcriptionStatus === "uploading") return "Transcribing";
  if (transcriptionStatus === "error") return "Action required";
  if (transcriptionStatus === "success") {
    return analysis?.status === "potential_emergency" ? "Possible arrest" : "Review transcript";
  }
  return "Ready for intake";
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function ModeSwitch({ mode, onChange, disabled }) {
  return (
    <div className="segmented" role="group" aria-label="Input">
      {[
        { value: "upload", label: "Recording" },
        { value: "live", label: "Live microphone" },
      ].map((option) => (
        <button
          key={option.value}
          type="button"
          className={`segmented__option${mode === option.value ? " is-selected" : ""}`}
          aria-pressed={mode === option.value}
          onClick={() => onChange(option.value)}
          disabled={disabled && mode !== option.value}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function ConsolePage({ health, healthStatus, healthError, onRefreshHealth, onCallStateChange }) {
  const [mode, setMode] = useState("upload");
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [transcriptionStatus, setTranscriptionStatus] = useState("idle");
  const [transcriptionError, setTranscriptionError] = useState("");
  const [result, setResult] = useState(null);
  const [notes, setNotes] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [acknowledgedAt, setAcknowledgedAt] = useState(null);
  const [timings, setTimings] = useState({});
  const [fileDuration, setFileDuration] = useState(null);
  const [saveState, setSaveState] = useState({ status: "idle" });
  const [utteranceInputs, setUtteranceInputs] = useState([]);
  const inFlight = useRef(false);
  const selectedRef = useRef(null);
  const liveRun = useRef(0);

  const report = useCallback((status, nextAnalysis) => {
    setTranscriptionStatus(status);
    onCallStateChange?.(callStateLabel(status, nextAnalysis));
  }, [onCallStateChange]);

  const clearCall = useCallback(() => {
    setResult(null);
    setAnalysis(null);
    setAnalysisError("");
    setAcknowledgedAt(null);
    setTimings({});
    setSaveState({ status: "idle" });
    setUtteranceInputs([]);
  }, []);

  // ---------- Live microphone ----------
  const handleLiveTranscript = useCallback(async (utterances, startedAt) => {
    const run = ++liveRun.current;
    const inputs = utterances.map((utterance) => ({
      text: utterance.text,
      speaker: "caller",
      utterance_index: utterance.index,
      utterance_id: `live-${utterance.index}`,
      timestamp: Math.round(utterance.at * 100) / 100,
      language: utterance.language,
      source: "manual",
    }));
    setUtteranceInputs(inputs);
    const latencies = utterances.map((utterance) => utterance.latencyMs).filter((value) => typeof value === "number");
    setTimings((previous) => ({ ...previous, medianLatency: median(latencies) }));

    setAnalyzing(true);
    setAnalysisError("");
    try {
      const nextAnalysis = await analyzeEmergency(inputs);
      if (run !== liveRun.current) return; // a newer sentence superseded this one
      setAnalysis(nextAnalysis);
      if (nextAnalysis.status === "potential_emergency" && startedAt) {
        setTimings((previous) => (previous.timeToFlag != null ? previous : { ...previous, timeToFlag: performance.now() - startedAt }));
      }
      onCallStateChange?.(callStateLabel("live", nextAnalysis));
    } catch (error) {
      if (run === liveRun.current) setAnalysisError(error.message || "Emergency analysis failed.");
    } finally {
      if (run === liveRun.current) setAnalyzing(false);
    }
  }, [onCallStateChange]);

  const live = useLiveCall({ onTranscript: handleLiveTranscript });
  const liveBusy = live.status === "connecting" || live.status === "live" || live.status === "stopping";

  const startLive = useCallback(() => {
    clearCall();
    liveRun.current += 1;
    onCallStateChange?.("Live call");
    live.start();
  }, [clearCall, live, onCallStateChange]);

  useEffect(() => {
    if (live.status === "ended" || live.status === "error") {
      onCallStateChange?.(analysis?.status === "potential_emergency" ? "Possible arrest" : live.utterances.length ? "Review transcript" : "Ready for intake");
    }
  }, [live.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeMode = useCallback((next) => {
    if (liveBusy || next === mode) return;
    setMode(next);
    clearCall();
    live.reset();
    setTranscriptionStatus("idle");
    setTranscriptionError("");
    onCallStateChange?.(callStateLabel("idle", null));
  }, [clearCall, live, liveBusy, mode, onCallStateChange]);

  // ---------- Uploaded recording ----------
  const handleFileSelected = useCallback((file, validationError) => {
    selectedRef.current = file;
    setSelectedFile(file);
    setFileDuration(null);
    setFileError(validationError || "");
    setTranscriptionError("");

    if (file && !validationError) {
      isMislabelledWav(file).then((mislabelled) => {
        if (mislabelled && selectedRef.current === file) {
          setFileError(
            "This file is named .wav but is not a WAV recording. Rename it to its real format (for example .mp3) or export it as WAV.",
          );
        }
      });
      readAudioDuration(file).then((seconds) => {
        if (selectedRef.current !== file || seconds == null) return;
        setFileDuration(seconds);
        if (seconds > MAX_REST_DURATION_SECONDS + 0.5) {
          setFileError(
            `This recording is ${formatDuration(seconds)} long. Prisma accepts up to ${MAX_REST_DURATION_SECONDS} seconds per request, so trim it first or use Live microphone.`,
          );
        }
      });
    }

    if (validationError) {
      report("idle", null);
      clearCall();
    }
  }, [clearCall, report]);

  const handleSubmit = useCallback(async () => {
    if (!selectedFile || fileError || inFlight.current) return;
    inFlight.current = true;

    report("uploading", null);
    setTranscriptionError("");
    clearCall();

    try {
      const startedAt = performance.now();
      const transcription = await transcribeAudio(selectedFile);
      setTimings({ transcription: performance.now() - startedAt });
      setResult(transcription);
      report("success", null);

      if (transcription.transcript) {
        setAnalyzing(true);
        try {
          const utterances = parseTranscriptToUtterances(transcription.transcript, "caller", {
            language: transcription.detected_language_code || null,
            source: "sentence_boundary",
          });
          setUtteranceInputs(utterances);
          if (utterances.length > 0) {
            const analysisStartedAt = performance.now();
            const nextAnalysis = await analyzeEmergency(utterances);
            setTimings((previous) => ({ ...previous, analysis: performance.now() - analysisStartedAt }));
            setAnalysis(nextAnalysis);
            report("success", nextAnalysis);
          }
        } catch (error) {
          setAnalysisError(error.message || "Emergency analysis failed.");
        } finally {
          setAnalyzing(false);
        }
      }
    } catch (error) {
      setTranscriptionError(error.message || "The transcription request failed.");
      report("error", null);
    } finally {
      inFlight.current = false;
    }
  }, [clearCall, fileError, report, selectedFile]);

  const handleConfirm = useCallback(() => setAcknowledgedAt(new Date()), []);

  // ---------- Saving to the call log ----------
  const isLive = mode === "live";
  const transcriptText = isLive ? live.utterances.map((utterance) => utterance.text).join(" ") : result?.transcript || "";
  const languageCode = isLive ? live.utterances.find((utterance) => utterance.language)?.language || null : result?.detected_language_code;
  const canSave = Boolean(transcriptText) && !liveBusy && !analyzing && saveState.status !== "saved";

  const handleSave = useCallback(async ({ label, noise_condition }) => {
    setSaveState({ status: "saving" });
    try {
      await saveCall({
        source: isLive ? "live" : "upload",
        recording_name: isLive ? null : selectedFile?.name || null,
        language_code: languageCode || null,
        model: isLive ? live.config?.model || null : result?.model || null,
        request_id: isLive ? null : result?.request_id || null,
        transcript: transcriptText,
        utterances: utteranceInputs.map((utterance) => ({
          text: utterance.text,
          language: utterance.language || null,
          utterance_index: utterance.utterance_index,
          timestamp: utterance.timestamp ?? null,
        })),
        analysis_status: analysis?.status || null,
        risk_category: analysis?.risk_category || null,
        matched_indicators: (analysis?.matched_indicators || []).map((indicator) => ({
          phrase: indicator.phrase,
          category: indicator.category,
          utterance_index: indicator.utterance_index,
          utterance_text: indicator.utterance_text,
        })),
        transcription_ms: isLive ? timings.medianLatency ?? null : timings.transcription ?? null,
        analysis_ms: timings.analysis ?? null,
        time_to_flag_ms: timings.timeToFlag ?? null,
        reviewed_at: acknowledgedAt ? acknowledgedAt.toISOString() : null,
        label,
        noise_condition,
      });
      setSaveState({ status: "saved" });
    } catch (error) {
      setSaveState({ status: "error", message: error.message || "The call could not be saved." });
    }
  }, [acknowledgedAt, analysis, isLive, languageCode, live.config, result, selectedFile, timings, transcriptText, utteranceInputs]);

  // A fresh console starts with a fresh call state in the top bar.
  useEffect(() => {
    onCallStateChange?.(callStateLabel("idle", null));
  }, [onCallStateChange]);

  const steps = useMemo(() => {
    if (isLive) {
      const failed = live.status === "error" ? 2 : analysisError ? 3 : null;
      const active = analysis?.status && analysis.status !== "no_indicator" ? 4 : live.utterances.length ? 3 : liveBusy ? 2 : 1;
      return { active, failed };
    }
    const active = analysis ? 4 : analyzing || analysisError ? 3 : transcriptionStatus === "uploading" || transcriptionStatus === "error" ? 2 : 1;
    const failed = transcriptionStatus === "error" ? 2 : analysisError ? 3 : null;
    return { active, failed };
  }, [analysis, analysisError, analyzing, isLive, live.status, live.utterances.length, liveBusy, transcriptionStatus]);

  const coachReady = Boolean(acknowledgedAt) && (analysis?.status === "potential_emergency" || analysis?.status === "review_required");
  const modeSwitch = <ModeSwitch mode={mode} onChange={changeMode} disabled={liveBusy || transcriptionStatus === "uploading"} />;
  const liveControls = { ...live, start: startLive };

  return (
    <main className="console" id="main">
      <section className="hero reveal" style={{ "--reveal-order": 0 }}>
        <div className="hero__copy">
          <p className="eyebrow">Operator console</p>
          <h1>
            Understand the call and flag a possible <span className="hero__accent">cardiac arrest</span>
          </h1>
          <p className="hero__lede">
            Load a staged recording or listen live. Gnani Prisma transcribes the caller, Naadi&apos;s rule-based detector
            marks the phrases that suggest the patient is unresponsive or not breathing normally, and once you review the
            flag it coaches hands-only CPR in the caller&apos;s language.
          </p>
        </div>
        <aside className="notice" aria-label="Prototype notice">
          <PulseTrace className="pulse-trace--run" />
          <p className="notice__title">Prototype, not an emergency service</p>
          <p className="notice__body">
            Not connected to 108 or 112. In a real emergency, call {SITE.emergencyNumbers}.
          </p>
        </aside>
      </section>

      <CallSteps active={steps.active} failed={steps.failed} />

      <div className="grid grid--primary">
        {isLive ? (
          <LiveMicPanel live={liveControls} modeSwitch={modeSwitch} />
        ) : (
          <AudioUploadPanel
            selectedFile={selectedFile}
            fileDuration={fileDuration}
            onFileSelected={handleFileSelected}
            onSubmit={handleSubmit}
            status={transcriptionStatus}
            error={fileError}
            modeSwitch={modeSwitch}
          />
        )}
        <TranscriptPanel
          mode={mode}
          result={result}
          status={transcriptionStatus}
          error={transcriptionError || fileError}
          indicators={analysis?.matched_indicators}
          live={live}
        />
      </div>

      <div className="grid grid--secondary">
        <div className="stack">
          <EmergencyPanel
            analysis={analysis}
            onConfirm={handleConfirm}
            acknowledgedAt={acknowledgedAt}
            isAnalyzing={analyzing && !analysis}
            error={analysisError}
          />
          {/* No key on purpose: a language change mid-call must not restart coaching. */}
          {coachReady && <CprCoach detectedLanguage={languageCode} />}
          <SystemStatus
            healthStatus={healthStatus}
            health={health}
            error={healthError}
            onRefresh={() => onRefreshHealth()}
          />
        </div>
        <div className="stack">
          <CallInfoPanel
            key={`${mode}-${saveState.status === "idle" && !transcriptText ? "empty" : "call"}`}
            mode={mode}
            fileName={selectedFile?.name}
            languageCode={languageCode}
            analysis={analysis}
            acknowledgedAt={acknowledgedAt}
            timings={timings}
            notes={notes}
            onNotesChange={setNotes}
            canSave={canSave}
            onSave={handleSave}
            saveState={saveState}
          />
        </div>
      </div>
    </main>
  );
}
