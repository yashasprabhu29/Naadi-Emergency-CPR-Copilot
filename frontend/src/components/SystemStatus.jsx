import { StatusBadge } from "./StatusBadge.jsx";

export function SystemStatus({ healthStatus, health, error, onRefresh }) {
  const online = healthStatus === "online";
  const checking = healthStatus === "checking";

  return (
    <section className="panel system-panel" aria-labelledby="system-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">SYSTEM MONITOR</p>
          <h2 id="system-title">System status</h2>
        </div>
        <StatusBadge tone={online ? "success" : checking ? "warning" : "danger"}>
          {online ? "Operational" : checking ? "Checking" : "Attention"}
        </StatusBadge>
      </div>
      <div className="system-facts">
        <div><span>FastAPI backend</span><strong>{online ? "Connected" : checking ? "Checking" : "Offline"}</strong></div>
        <div><span>Prisma credentials</span><strong>{health?.gnani_api_key_configured ? "Configured" : "Not configured"}</strong></div>
        <div><span>Application version</span><strong>{health?.version || "—"}</strong></div>
        <div><span>Prisma model</span><strong>{health?.prisma_model || "—"}</strong></div>
      </div>
      {error && <p className="system-error">{error}</p>}
      <button type="button" className="button button--ghost" onClick={onRefresh} disabled={checking}>
        Refresh connection
      </button>
    </section>
  );
}
