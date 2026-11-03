export function CallInfoPanel({ notes, onNotesChange }) {
  return (
    <section className="panel call-info-panel" aria-labelledby="call-info-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">CASE CONTEXT</p>
          <h2 id="call-info-title">Call information</h2>
        </div>
        <span className="panel-index">03</span>
      </div>
      <dl className="call-facts">
        <div><dt>Incident location</dt><dd>Not captured</dd></div>
        <div><dt>Caller language</dt><dd>Awaiting transcription</dd></div>
        <div><dt>Call duration</dt><dd>Staged recording</dd></div>
        <div><dt>Incident status</dt><dd><span className="fact-status">Unclassified</span></dd></div>
      </dl>
      <label className="notes-label" htmlFor="operator-notes">Operator notes</label>
      <textarea
        id="operator-notes"
        value={notes}
        onChange={(event) => onNotesChange(event.target.value)}
        placeholder="Add notes for the human review record…"
        rows={4}
      />
    </section>
  );
}
