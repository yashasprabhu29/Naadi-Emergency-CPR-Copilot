import { StatusBadge } from "./StatusBadge.jsx";

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

export function TranscriptPanel({ result, status, error }) {
  const hasTranscript = status === "success" && result;

  return (
    <section className="panel transcript-panel" aria-labelledby="transcript-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">PRISMA OUTPUT</p>
          <h2 id="transcript-title">Live transcription</h2>
        </div>
        {hasTranscript ? <StatusBadge tone="success">Received</StatusBadge> : <span className="panel-index">02</span>}
      </div>

      {status === "idle" && (
        <div className="empty-state">
          <div className="waveform-placeholder" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
          <h3>Awaiting staged audio</h3>
          <p>Transcription output will appear here after a recording is processed.</p>
        </div>
      )}

      {status === "uploading" && (
        <div className="empty-state empty-state--loading" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          <h3>Prisma is processing the call</h3>
          <p>Waiting for the verified transcription response.</p>
        </div>
      )}

      {status === "error" && (
        <div className="empty-state empty-state--error" role="alert">
          <div className="empty-state-symbol" aria-hidden="true">!</div>
          <h3>Transcription unavailable</h3>
          <p>{error || "The backend did not return a transcription."}</p>
        </div>
      )}

      {hasTranscript && (
        <>
          <div className="transcript-quote">
            <span className="quote-mark" aria-hidden="true">“</span>
            <p>{result.transcript || "Prisma returned an empty transcript."}</p>
          </div>
          <div className="metrics-grid">
            <Metric label="Detected language" value={result.detected_language_code} />
            <Metric label="Model" value={result.model} />
            <Metric label="Processing" value={result.processing_time != null ? `${result.processing_time.toFixed(2)} s` : null} />
            <Metric label="End-to-end" value={result.end_to_end_latency != null ? `${result.end_to_end_latency.toFixed(2)} s` : null} />
          </div>
          <div className="request-reference">
            <span>REQUEST REFERENCE</span>
            <code>{result.request_id || "Not returned by Prisma"}</code>
          </div>
        </>
      )}
    </section>
  );
}
