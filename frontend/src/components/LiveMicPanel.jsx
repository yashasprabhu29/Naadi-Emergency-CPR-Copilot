import { languageName } from "../site.js";
import { PhoneIcon } from "./Icons.jsx";

const BARS = 28;

function clock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

const STATUS_TEXT = {
  idle: "Not listening",
  connecting: "Connecting to Gnani",
  live: "Listening",
  stopping: "Finishing the last sentence",
  ended: "Call ended",
  error: "Stopped",
};

export function LiveMicPanel({ live, modeSwitch }) {
  const { status, error, level, elapsed, speaking, config, utterances } = live;
  const listening = status === "live";
  const busy = status === "connecting" || status === "stopping";
  // Light up bars from the centre outwards in proportion to the real input level.
  const lit = Math.round(level * BARS);

  return (
    <section className="panel upload-panel live-panel reveal" style={{ "--reveal-order": 1 }} aria-labelledby="live-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">01</span>Live audio</p>
          <h2 id="live-title">Listen to a call</h2>
        </div>
        {modeSwitch}
      </div>

      <div className={`live-meter${listening ? " live-meter--on" : ""}`}>
        <div className="live-meter__head">
          <span className={`live-dot${listening ? " live-dot--on" : ""}`} aria-hidden="true" />
          <span className="live-meter__status" role="status" aria-live="polite">
            {STATUS_TEXT[status]}
            {listening && speaking ? ", caller speaking" : ""}
          </span>
          <span className="live-meter__clock">{clock(elapsed)}</span>
        </div>
        <div className="live-meter__bars" aria-hidden="true">
          {Array.from({ length: BARS }, (_, index) => {
            const distance = Math.abs(index - (BARS - 1) / 2);
            const on = listening && distance < lit / 2;
            return <i key={index} className={on ? "is-on" : undefined} />;
          })}
        </div>
        <dl className="live-meter__facts">
          <div><dt>Language</dt><dd>{config ? `${languageName(config.language_code)} (${config.language_code})` : "Set by the backend"}</dd></div>
          <div><dt>Sentences</dt><dd className="mono">{utterances.length}</dd></div>
        </dl>
      </div>

      {error && <div className="inline-alert inline-alert--danger" role="alert">{error}</div>}

      <p className="live-panel__hint">
        <PhoneIcon size={16} />
        Put a staged call on speaker next to this computer. Prisma returns each sentence when the speaker pauses.
      </p>

      {listening || status === "stopping" ? (
        <button type="button" className="button button--danger button--full" onClick={live.stop} disabled={status === "stopping"}>
          {status === "stopping" ? "Stopping" : "Stop listening"}
        </button>
      ) : (
        <button type="button" className="button button--primary button--full" onClick={live.start} disabled={busy}>
          {status === "connecting" ? "Connecting" : status === "ended" || status === "error" ? "Start a new live call" : "Start listening"}
        </button>
      )}
    </section>
  );
}
