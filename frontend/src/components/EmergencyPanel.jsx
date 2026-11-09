import { AlertIcon, CheckIcon, LungsIcon, PersonDownIcon, ShieldIcon } from "./Icons.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

const STATUS = {
  no_indicator: { label: "No emergency indicator", tone: "success", title: "No cardiac arrest indicators found" },
  review_required: { label: "Review required", tone: "warning", title: "Some indicators found, ask the caller" },
  potential_emergency: { label: "Potential emergency", tone: "danger", title: "Possible cardiac arrest" },
};

const CATEGORY = {
  unresponsive: { label: "Unresponsive", Icon: PersonDownIcon },
  abnormal_breathing: { label: "Abnormal breathing", Icon: LungsIcon },
};

function formatTime(date) {
  return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function Shell({ tone = "neutral", badge, children }) {
  return (
    <section
      className={`panel intelligence-panel intelligence-panel--${tone} reveal`}
      style={{ "--reveal-order": 3 }}
      aria-labelledby="intelligence-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">03</span>Operator decision support</p>
          <h2 id="intelligence-title">Emergency detection</h2>
        </div>
        {badge}
      </div>
      {children}
    </section>
  );
}

function List({ title, items, className = "" }) {
  if (!items?.length) return null;
  return (
    <div className={`analysis-block ${className}`}>
      <h3>{title}</h3>
      <ul className="plain-list">
        {items.map((item, index) => <li key={index}>{item}</li>)}
      </ul>
    </div>
  );
}

export function EmergencyPanel({ analysis, onConfirm, acknowledgedAt, isAnalyzing, error }) {
  if (isAnalyzing) {
    return (
      <Shell badge={<StatusBadge tone="warning" pulse>Analysing</StatusBadge>}>
        <div className="placeholder" role="status" aria-live="polite">
          <div className="scan-line" aria-hidden="true" />
          <p>Checking the transcript for cardiac arrest indicators…</p>
        </div>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell tone="danger" badge={<StatusBadge tone="danger">Error</StatusBadge>}>
        <div className="placeholder placeholder--error">
          <span className="placeholder__icon"><AlertIcon /></span>
          <div>
            <h3>Analysis failed</h3>
            <p>{error}</p>
          </div>
        </div>
      </Shell>
    );
  }

  if (!analysis) {
    return (
      <Shell badge={<StatusBadge tone="neutral">Ready</StatusBadge>}>
        <div className="placeholder">
          <span className="placeholder__icon"><ShieldIcon /></span>
          <div>
            <h3>Detection engine ready</h3>
            <p>
              Naadi checks the last three caller sentences for two signs together: the patient is unresponsive and is not
              breathing normally. Any indicator it finds needs your review, and a reviewed flag opens CPR coaching.
            </p>
          </div>
        </div>
      </Shell>
    );
  }

  const status = STATUS[analysis.status] || { label: analysis.status, tone: "neutral", title: analysis.status };
  const indicators = analysis.matched_indicators || [];
  const isAlert = status.tone === "danger";

  return (
    <Shell tone={status.tone} badge={<StatusBadge tone={status.tone}>{status.label}</StatusBadge>}>
      <div className={`verdict verdict--${status.tone}`}>
        <span className={`verdict__mark verdict__mark--${status.tone}`} aria-hidden="true" />
        <div>
          <p className="verdict__title">{status.title}</p>
          <p className="verdict__explanation">{analysis.explanation}</p>
        </div>
      </div>

      {indicators.length > 0 && (
        <div className="analysis-block">
          <h3>Evidence from the transcript ({indicators.length})</h3>
          <ul className="evidence-list">
            {indicators.map((indicator, index) => {
              const category = CATEGORY[indicator.category] || { label: indicator.category, Icon: AlertIcon };
              const { Icon } = category;
              return (
                <li
                  key={`${indicator.utterance_id}-${index}`}
                  className={`evidence evidence--${indicator.category}`}
                  style={{ "--item": index }}
                >
                  <span className="evidence__icon"><Icon size={16} /></span>
                  <div className="evidence__body">
                    <span className="evidence__category">{category.label}</span>
                    <span className="evidence__phrase">&ldquo;{indicator.phrase}&rdquo;</span>
                    <span className="evidence__context">Sentence {indicator.utterance_index + 1}: {indicator.utterance_text}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <List title="Contradictory evidence" items={analysis.contradictory_evidence} className="analysis-block--warning" />
      <List title="Uncertainty notes" items={analysis.uncertainty_notes} />

      {analysis.rule_identifiers?.length > 0 && (
        <details className="technical">
          <summary>Rules applied</summary>
          <p><span>Rules</span><code>{analysis.rule_identifiers.join(", ")}</code></p>
          <p><span>Detector version</span><code>{analysis.detector_version}</code></p>
        </details>
      )}

      {analysis.requires_operator_confirmation && (
        <div className="confirmation">
          <p className="confirmation__notice">
            Decision support only. Confirm with the caller before acting, and do not dispatch based on this result alone.
            {!acknowledgedAt && " Marking it as reviewed opens CPR coaching."}
          </p>
          {acknowledgedAt ? (
            <p className="confirmation__done" role="status">
              <CheckIcon size={16} /> Reviewed by operator at {formatTime(acknowledgedAt)}
            </p>
          ) : (
            onConfirm && (
              <button type="button" className={`button ${isAlert ? "button--danger" : "button--primary"}`} onClick={onConfirm}>
                Mark as reviewed
              </button>
            )
          )}
        </div>
      )}
    </Shell>
  );
}
