import { useState } from "react";

import { Link } from "../router.jsx";
import { languageName } from "../site.js";

const INCIDENT_STATUS = {
  no_indicator: "No indicator",
  review_required: "Review required",
  potential_emergency: "Potential emergency",
};

export const LABEL_OPTIONS = [
  { value: "", label: "Not labelled" },
  { value: "arrest", label: "Arrest scenario" },
  { value: "not_arrest", label: "Not an arrest" },
];

export const NOISE_OPTIONS = [
  { value: "", label: "Not set" },
  { value: "quiet", label: "Quiet room" },
  { value: "kitchen", label: "Kitchen" },
  { value: "street", label: "Street" },
  { value: "market", label: "Market" },
  { value: "other", label: "Other" },
];

function Duration({ value }) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Not measured";
  return <span className="mono">{value >= 10000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`}</span>;
}

export function CallInfoPanel({
  mode = "upload",
  fileName,
  languageCode,
  analysis,
  acknowledgedAt,
  timings,
  notes,
  onNotesChange,
  canSave = false,
  onSave,
  saveState,
}) {
  const [label, setLabel] = useState("");
  const [noise, setNoise] = useState("");
  const incident = analysis ? INCIDENT_STATUS[analysis.status] || analysis.status : "Not analysed";
  const tone = analysis?.status === "potential_emergency" ? "danger" : analysis?.status === "review_required" ? "warning" : analysis ? "success" : "neutral";
  const isLive = mode === "live";

  return (
    <section className="panel call-info-panel reveal" style={{ "--reveal-order": 4 }} aria-labelledby="call-info-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">04</span>Case record</p>
          <h2 id="call-info-title">Call record</h2>
        </div>
      </div>
      <dl className="facts">
        <div><dt>{isLive ? "Source" : "Recording"}</dt><dd title={fileName || undefined}>{isLive ? "Live microphone" : fileName || "None loaded"}</dd></div>
        <div><dt>Caller language</dt><dd>{languageName(languageCode) || "Awaiting transcription"}</dd></div>
        <div><dt>Incident status</dt><dd><span className={`fact-status fact-status--${tone}`}>{incident}</span></dd></div>
        <div><dt>Operator review</dt><dd>{acknowledgedAt ? "Reviewed" : analysis?.requires_operator_confirmation ? "Pending" : "Not required yet"}</dd></div>
        {isLive ? (
          <>
            <div><dt>Time to flag</dt><dd><Duration value={timings?.timeToFlag} /></dd></div>
            <div><dt>Median sentence latency</dt><dd><Duration value={timings?.medianLatency} /></dd></div>
          </>
        ) : (
          <>
            <div><dt>Transcription round trip</dt><dd><Duration value={timings?.transcription} /></dd></div>
            <div><dt>Detection round trip</dt><dd><Duration value={timings?.analysis} /></dd></div>
          </>
        )}
      </dl>

      <div className="save-box">
        <p className="save-box__title">Save to the call log</p>
        <div className="save-box__fields">
          <label>
            <span>Ground truth</span>
            <select value={label} onChange={(event) => setLabel(event.target.value)} disabled={!canSave || saveState?.status === "saving"}>
              {LABEL_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            <span>Noise</span>
            <select value={noise} onChange={(event) => setNoise(event.target.value)} disabled={!canSave || saveState?.status === "saving"}>
              {NOISE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
        </div>
        {saveState?.status === "saved" ? (
          <p className="save-box__done" role="status">Saved. <Link to="/calls">Open the call log</Link></p>
        ) : (
          <button
            type="button"
            className="button button--secondary button--full"
            disabled={!canSave || saveState?.status === "saving"}
            onClick={() => onSave?.({ label: label || null, noise_condition: noise || null })}
          >
            {saveState?.status === "saving" ? "Saving" : "Save call"}
          </button>
        )}
        {saveState?.status === "error" && <p className="inline-alert inline-alert--danger" role="alert">{saveState.message}</p>}
        <p className="save-box__note">Saves the transcript, detection result and timings on the Naadi server. Notes are not saved.</p>
      </div>

      <label className="notes-label" htmlFor="operator-notes">Operator notes</label>
      <textarea
        id="operator-notes"
        value={notes}
        onChange={(event) => onNotesChange(event.target.value)}
        placeholder="Notes stay in this browser tab and are never sent to the server."
        rows={3}
      />
    </section>
  );
}
