import { useEffect, useRef } from "react";

import { languageName } from "../site.js";
import { highlightSegments } from "../utils/highlight.js";
import { StatusBadge } from "./StatusBadge.jsx";

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span className="metric__label">{label}</span>
      <strong className="metric__value">{value || "Not returned"}</strong>
    </div>
  );
}

function seconds(value) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)} s` : null;
}

function clock(value) {
  const total = Math.max(0, Math.floor(value));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

const CATEGORY_LABEL = {
  unresponsive: "Unresponsive",
  abnormal_breathing: "Abnormal breathing",
};

function Highlighted({ text, indicators, className = "transcript__text" }) {
  const segments = highlightSegments(text, indicators);
  const hasMarks = segments.some((segment) => segment.category);

  if (!hasMarks) {
    return <p className={className}>{text}</p>;
  }

  return (
    <p className={className}>
      {segments.map((segment, index) =>
        segment.category ? (
          <mark
            key={index}
            className={`evidence-mark evidence-mark--${segment.category}`}
            title={CATEGORY_LABEL[segment.category] || segment.category}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
}

function Legend() {
  return (
    <ul className="legend" aria-label="Highlight legend">
      <li><span className="legend__swatch legend__swatch--unresponsive" />Unresponsive</li>
      <li><span className="legend__swatch legend__swatch--abnormal_breathing" />Abnormal breathing</li>
    </ul>
  );
}

function Waveform({ active = false }) {
  return (
    <div className={`waveform${active ? " waveform--active" : ""}`} aria-hidden="true">
      {Array.from({ length: 24 }, (_, index) => <i key={index} style={{ "--bar": index }} />)}
    </div>
  );
}

function LiveTranscript({ utterances, status, indicators }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [utterances.length]);

  if (utterances.length === 0) {
    const listening = status === "live" || status === "connecting";
    return (
      <div className="empty-state" role="status" aria-live="polite">
        <Waveform active={listening} />
        <h3>{listening ? "Listening for the caller" : "No live call yet"}</h3>
        <p>
          {listening
            ? "Each sentence appears here when the speaker pauses."
            : "Choose Live microphone and start listening. Sentences appear here as Prisma returns them."}
        </p>
      </div>
    );
  }

  return (
    <div className="transcript">
      <ol className="utterances" aria-live="polite">
        {utterances.map((utterance) => (
          <li key={utterance.index} className="utterance">
            <span className="utterance__time">{clock(utterance.at)}</span>
            <div className="utterance__body">
              <Highlighted
                className="utterance__text"
                text={utterance.text}
                indicators={(indicators || []).filter((indicator) => indicator.utterance_index === utterance.index)}
              />
              <span className="utterance__meta">
                {languageName(utterance.language) || "Language not detected"}
                {utterance.latencyMs != null ? `, ${utterance.latencyMs} ms` : ""}
              </span>
            </div>
          </li>
        ))}
      </ol>
      <div ref={endRef} />
      {indicators?.length > 0 && <Legend />}
    </div>
  );
}

export function TranscriptPanel({ mode = "upload", result, status, error, indicators, live }) {
  const isLive = mode === "live";
  const hasTranscript = !isLive && status === "success" && result;
  const language = hasTranscript ? result.detected_language_code : null;

  return (
    <section className="panel transcript-panel reveal" style={{ "--reveal-order": 2 }} aria-labelledby="transcript-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">02</span>Gnani Prisma output</p>
          <h2 id="transcript-title">Transcript</h2>
        </div>
        {hasTranscript && <StatusBadge tone="success">Received</StatusBadge>}
        {isLive && live?.status === "live" && <StatusBadge tone="danger" pulse>Live</StatusBadge>}
      </div>

      {isLive && <LiveTranscript utterances={live?.utterances || []} status={live?.status} indicators={indicators} />}

      {!isLive && status === "idle" && (
        <div className="empty-state">
          <Waveform />
          <h3>Awaiting staged audio</h3>
          <p>The transcript appears here after Prisma processes a recording. Phrases the detector relies on are highlighted.</p>
        </div>
      )}

      {!isLive && status === "uploading" && (
        <div className="empty-state empty-state--loading" role="status" aria-live="polite">
          <Waveform active />
          <h3>Prisma is processing the call</h3>
          <p>Waiting for the transcription response.</p>
        </div>
      )}

      {!isLive && status === "error" && (
        <div className="empty-state empty-state--error" role="alert">
          <h3>Transcription unavailable</h3>
          <p>{error || "The backend did not return a transcription."}</p>
        </div>
      )}

      {hasTranscript && (
        <div className="transcript">
          <div className="transcript__body">
            {language && <span className="language-tag" lang="en">{languageName(language)}</span>}
            {result.transcript ? (
              <Highlighted text={result.transcript} indicators={indicators} />
            ) : (
              <p className="transcript__text transcript__text--empty">Prisma returned an empty transcript.</p>
            )}
          </div>

          {indicators?.length > 0 && <Legend />}

          <div className="metrics-grid">
            <Metric label="Detected language" value={result.detected_language_code} />
            <Metric label="Model" value={result.model} />
            <Metric label="Processing" value={seconds(result.processing_time)} />
            <Metric label="End-to-end" value={seconds(result.end_to_end_latency)} />
          </div>
          <div className="request-reference">
            <span>Request reference</span>
            <code>{result.request_id || "Not returned by Prisma"}</code>
          </div>
        </div>
      )}
    </section>
  );
}
