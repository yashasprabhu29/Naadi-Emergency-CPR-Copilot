import { useCallback, useEffect, useState } from "react";

import { LABEL_OPTIONS, NOISE_OPTIONS } from "../components/CallInfoPanel.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { Link } from "../router.jsx";
import { deleteAllCalls, deleteCall, downloadCallsCsv, listCalls, updateCall } from "../services/api.js";
import { languageName } from "../site.js";

const STATUS = {
  no_indicator: { label: "No indicator", tone: "success" },
  review_required: { label: "Review required", tone: "warning" },
  potential_emergency: { label: "Potential emergency", tone: "danger" },
};

const NOISE_LABEL = Object.fromEntries(NOISE_OPTIONS.filter((o) => o.value).map((o) => [o.value, o.label]));

function formatMs(value) {
  if (typeof value !== "number") return null;
  return value >= 10000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`;
}

function formatWhen(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
}

function Stat({ label, value, detail }) {
  return (
    <div className="stat">
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
      {detail && <span className="stat__detail">{detail}</span>}
    </div>
  );
}

export function CallLogPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [confirmingClear, setConfirmingClear] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await listCalls());
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const change = async (id, changes) => {
    setBusyId(id);
    try {
      await updateCall(id, changes);
      await load();
    } catch (updateError) {
      setError(updateError.message);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (id) => {
    setBusyId(id);
    try {
      await deleteCall(id);
      await load();
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setBusyId(null);
    }
  };

  const clearAll = async () => {
    try {
      await deleteAllCalls();
      setConfirmingClear(false);
      await load();
    } catch (clearError) {
      setError(clearError.message);
    }
  };

  const calls = data?.calls || [];
  const summary = data?.summary;

  return (
    <main className="console calls" id="main">
      <header className="page-header reveal" style={{ "--reveal-order": 0 }}>
        <div>
          <p className="eyebrow">Evaluation</p>
          <h1>Call log</h1>
          <p className="page-header__lede">
            Staged calls you chose to save. Label each one as an arrest scenario or not, and Naadi reports how the detector
            did on your own test set.
          </p>
        </div>
        <div className="page-header__actions">
          <button
            type="button"
            className="button button--secondary"
            disabled={!calls.length}
            onClick={() => downloadCallsCsv().catch((exportError) => setError(exportError.message))}
          >
            Export CSV
          </button>
          {confirmingClear ? (
            <span className="confirm-inline">
              <span>Delete all {calls.length} calls?</span>
              <button type="button" className="button button--danger" onClick={clearAll}>Delete all</button>
              <button type="button" className="button button--ghost" onClick={() => setConfirmingClear(false)}>Cancel</button>
            </span>
          ) : (
            <button type="button" className="button button--ghost" onClick={() => setConfirmingClear(true)} disabled={!calls.length}>
              Delete all
            </button>
          )}
        </div>
      </header>

      {error && <p className="inline-alert inline-alert--danger" role="alert">{error}</p>}

      {summary && (
        <section className="stats reveal" style={{ "--reveal-order": 1 }} aria-label="Detector results">
          <Stat
            label="Arrests flagged"
            value={summary.arrest_calls ? `${summary.arrest_flagged} of ${summary.arrest_calls}` : "None yet"}
            detail={summary.arrest_calls ? `${summary.arrest_review_required} more marked review required` : "Label calls as arrest scenarios"}
          />
          <Stat
            label="False flags"
            value={summary.not_arrest_calls ? `${summary.false_flags} of ${summary.not_arrest_calls}` : "None yet"}
            detail="Potential emergency on a non-arrest call"
          />
          <Stat
            label="Median time to flag"
            value={formatMs(summary.median_time_to_flag_ms) || "None yet"}
            detail="Live calls. AHA target under 90 s"
          />
          <Stat
            label="Saved calls"
            value={`${summary.total}`}
            detail={`${summary.labelled} labelled`}
          />
        </section>
      )}

      {summary && Object.keys(summary.by_noise_condition).length > 0 && (
        <section className="panel noise-table reveal" style={{ "--reveal-order": 2 }} aria-labelledby="noise-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">By condition</p>
              <h2 id="noise-title">Results by noise condition</h2>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr><th scope="col">Condition</th><th scope="col" className="num">Arrests flagged</th><th scope="col" className="num">False flags</th></tr>
            </thead>
            <tbody>
              {Object.entries(summary.by_noise_condition).map(([condition, row]) => (
                <tr key={condition}>
                  <td>{NOISE_LABEL[condition] || "Not set"}</td>
                  <td className="num">{row.arrest ? `${row.arrest_flagged} of ${row.arrest}` : "None"}</td>
                  <td className="num">{row.not_arrest ? `${row.false_flags} of ${row.not_arrest}` : "None"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="panel reveal" style={{ "--reveal-order": 3 }} aria-labelledby="calls-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Saved calls</p>
            <h2 id="calls-title">All calls</h2>
          </div>
        </div>

        {!data && !error && <p className="muted" role="status">Loading saved calls</p>}

        {data && calls.length === 0 && (
          <div className="empty-state">
            <h3>No saved calls yet</h3>
            <p>Transcribe a staged call on the console, then press Save call in the call record.</p>
            <Link to="/" className="button button--primary">Go to the console</Link>
          </div>
        )}

        {calls.length > 0 && (
          <div className="table-scroll">
            <table className="table table--calls">
              <thead>
                <tr>
                  <th scope="col">Saved</th>
                  <th scope="col">Transcript</th>
                  <th scope="col">Detector</th>
                  <th scope="col">Ground truth</th>
                  <th scope="col">Noise</th>
                  <th scope="col" className="num">Timing</th>
                  <th scope="col"><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {calls.map((call) => {
                  const status = STATUS[call.analysis_status];
                  return (
                    <tr key={call.id} className={busyId === call.id ? "is-busy" : undefined}>
                      <td className="nowrap">
                        <span className="cell-primary">{formatWhen(call.created_at)}</span>
                        <span className="cell-meta">{call.source === "live" ? "Live" : call.recording_name || "Recording"}</span>
                      </td>
                      <td className="cell-transcript">
                        <span className="cell-primary" title={call.transcript}>{call.transcript}</span>
                        <span className="cell-meta">{languageName(call.language_code) || "Language unknown"}</span>
                      </td>
                      <td>{status ? <StatusBadge tone={status.tone}>{status.label}</StatusBadge> : <span className="cell-meta">Not analysed</span>}</td>
                      <td>
                        <select
                          aria-label="Ground truth"
                          value={call.label || ""}
                          disabled={busyId === call.id}
                          onChange={(event) => change(call.id, { label: event.target.value || null })}
                        >
                          {LABEL_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </td>
                      <td>
                        <select
                          aria-label="Noise condition"
                          value={call.noise_condition || ""}
                          disabled={busyId === call.id}
                          onChange={(event) => change(call.id, { noise_condition: event.target.value || null })}
                        >
                          {NOISE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </td>
                      <td className="num nowrap">
                        <span className="cell-primary mono">{formatMs(call.time_to_flag_ms) || formatMs(call.transcription_ms) || "None"}</span>
                        <span className="cell-meta">{call.time_to_flag_ms != null ? "to flag" : call.source === "live" ? "median sentence" : "transcription"}</span>
                      </td>
                      <td>
                        <button type="button" className="button button--ghost button--small" onClick={() => remove(call.id)} disabled={busyId === call.id}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
