export function EmergencyPlaceholder() {
  return (
    <section className="panel intelligence-panel" aria-labelledby="intelligence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">OPERATOR DECISION SUPPORT</p>
          <h2 id="intelligence-title">Emergency intelligence</h2>
        </div>
        <span className="future-chip">NEXT LAYER</span>
      </div>
      <div className="placeholder-content">
        <div className="placeholder-icon" aria-hidden="true">⌁</div>
        <div>
          <h3>Emergency detection engine not yet connected.</h3>
          <p>
            Deterministic, explainable rules and human confirmation will be added in a later milestone.
            No emergency alert is being inferred from this transcript.
          </p>
        </div>
      </div>
    </section>
  );
}
