import { RefreshIcon } from "./Icons.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

export function SystemStatus({ healthStatus, health, error, onRefresh }) {
  const online = healthStatus === "online";
  const checking = healthStatus === "checking";

  return (
    <section className="panel system-panel reveal" style={{ "--reveal-order": 5 }} aria-labelledby="system-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow"><span className="eyebrow__index">05</span>Services</p>
          <h2 id="system-title">System status</h2>
        </div>
        <StatusBadge tone={online ? "success" : checking ? "warning" : "danger"} pulse={checking}>
          {online ? "Operational" : checking ? "Checking" : "Attention"}
        </StatusBadge>
      </div>
      <dl className="facts facts--compact">
        <div><dt>FastAPI backend</dt><dd>{online ? "Connected" : checking ? "Checking" : "Offline"}</dd></div>
        <div><dt>Gnani API key</dt><dd>{health?.gnani_api_key_configured ? "Configured" : "Not configured"}</dd></div>
        <div><dt>Prisma model</dt><dd>{health?.prisma_model ? <span className="mono">{health.prisma_model}</span> : "Unavailable"}</dd></div>
        <div><dt>App version</dt><dd>{health?.version ? <span className="mono">{health.version}</span> : "Unavailable"}</dd></div>
      </dl>
      {error && <p className="system-error">{error}</p>}
      <button type="button" className="button button--ghost" onClick={onRefresh} disabled={checking}>
        <RefreshIcon size={16} className={checking ? "icon--spin" : ""} />
        Check again
      </button>
    </section>
  );
}
