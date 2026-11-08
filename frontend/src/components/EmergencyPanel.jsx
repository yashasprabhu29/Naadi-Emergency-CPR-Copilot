import { StatusBadge } from "./StatusBadge.jsx";

const STATUS_LABELS = {
  no_indicator: "No Emergency Indicator",
  review_required: "Review Required",
  potential_emergency: "Potential Emergency",
};

const STATUS_VARIANTS = {
  no_indicator: "success",
  review_required: "warning",
  potential_emergency: "critical",
};

export function EmergencyPanel({ analysis, onConfirm, isAnalyzing, error }) {
  if (isAnalyzing) {
    return (
      <section className="panel intelligence-panel" aria-labelledby="intelligence-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">OPERATOR DECISION SUPPORT</p>
            <h2 id="intelligence-title">Emergency intelligence</h2>
          </div>
        </div>
        <div className="placeholder-content">
          <p>Analyzing transcript...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel intelligence-panel" aria-labelledby="intelligence-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">OPERATOR DECISION SUPPORT</p>
            <h2 id="intelligence-title">Emergency intelligence</h2>
          </div>
        </div>
        <div className="placeholder-content">
          <div className="placeholder-icon" aria-hidden="true">⚠</div>
          <div>
            <h3>Analysis error</h3>
            <p>{error}</p>
          </div>
        </div>
      </section>
    );
  }

  if (!analysis) {
    return (
      <section className="panel intelligence-panel" aria-labelledby="intelligence-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">OPERATOR DECISION SUPPORT</p>
            <h2 id="intelligence-title">Emergency intelligence</h2>
          </div>
          <span className="status-chip status-chip--idle">READY</span>
        </div>
        <div className="placeholder-content">
          <div className="placeholder-icon" aria-hidden="true">⌁</div>
          <div>
            <h3>Emergency detection engine ready.</h3>
            <p>
              Upload and transcribe a call recording to analyze for cardiac-respiratory
              emergency indicators. All detections require operator confirmation.
            </p>
          </div>
        </div>
      </section>
    );
  }

  const statusLabel = STATUS_LABELS[analysis.status] || analysis.status;
  const statusVariant = STATUS_VARIANTS[analysis.status] || "default";

  return (
    <section className="panel intelligence-panel" aria-labelledby="intelligence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">OPERATOR DECISION SUPPORT</p>
          <h2 id="intelligence-title">Emergency intelligence</h2>
        </div>
        <StatusBadge variant={statusVariant}>{statusLabel}</StatusBadge>
      </div>

      <div className="emergency-analysis">
        <div className="analysis-section">
          <h3>Assessment</h3>
          <p className="analysis-explanation">{analysis.explanation}</p>
          
          {analysis.risk_category && analysis.risk_category !== "none" && (
            <p className="analysis-risk">
              <strong>Risk Category:</strong>{" "}
              {analysis.risk_category.replace(/_/g, " ").toUpperCase()}
            </p>
          )}
        </div>

        {analysis.matched_indicators && analysis.matched_indicators.length > 0 && (
          <div className="analysis-section">
            <h3>Detected Indicators ({analysis.matched_indicators.length})</h3>
            <ul className="indicator-list">
              {analysis.matched_indicators.map((indicator, idx) => (
                <li key={idx} className="indicator-item">
                  <span className="indicator-category">
                    {indicator.category === "unresponsive" ? "🔴 Unresponsive" : "🔵 Abnormal Breathing"}
                  </span>
                  <span className="indicator-phrase">"{indicator.phrase}"</span>
                  <span className="indicator-context">in: {indicator.utterance_text}</span>
                  {indicator.utterance_id && (
                    <span className="indicator-id" title={indicator.utterance_id}>
                      ID: {indicator.utterance_id.substring(0, 8)}...
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {analysis.contradictory_evidence && analysis.contradictory_evidence.length > 0 && (
          <div className="analysis-section analysis-section--warning">
            <h3>⚠ Contradictory Evidence</h3>
            <ul className="contradiction-list">
              {analysis.contradictory_evidence.map((contradiction, idx) => (
                <li key={idx}>{contradiction}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.uncertainty_notes && analysis.uncertainty_notes.length > 0 && (
          <div className="analysis-section">
            <h3>Uncertainty Notes</h3>
            <ul className="uncertainty-list">
              {analysis.uncertainty_notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.rule_identifiers && analysis.rule_identifiers.length > 0 && (
          <div className="analysis-section analysis-section--technical">
            <details>
              <summary>Technical Details</summary>
              <p className="analysis-technical">
                <strong>Rules Applied:</strong> {analysis.rule_identifiers.join(", ")}
              </p>
              <p className="analysis-technical">
                <strong>Detector Version:</strong> {analysis.detector_version}
              </p>
            </details>
          </div>
        )}

        {analysis.requires_operator_confirmation && (
          <div className="analysis-confirmation">
            <div className="confirmation-notice">
              <strong>⚠ Operator Confirmation Required</strong>
              <p>
                This detection result requires human review and confirmation. Do not dispatch
                emergency services based solely on automated analysis.
              </p>
            </div>
            {onConfirm && (
              <button
                type="button"
                className="btn btn--primary btn--confirm"
                onClick={onConfirm}
              >
                Acknowledge and Review
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
