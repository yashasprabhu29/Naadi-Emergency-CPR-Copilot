import { StatusBadge } from "./StatusBadge.jsx";

export function TopBar({ backendStatus, prismaConfigured, callState }) {
  const backendTone = backendStatus === "online" ? "success" : backendStatus === "offline" ? "danger" : "warning";
  const backendLabel = backendStatus === "online" ? "Backend online" : backendStatus === "offline" ? "Backend offline" : "Checking backend";

  return (
    <header className="topbar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true">N</div>
        <div>
          <div className="brand-name">Naadi <span lang="kn">ನಾಡಿ</span></div>
          <div className="brand-subtitle">AI-Powered Emergency Call-Taker Copilot</div>
        </div>
      </div>
      <div className="topbar-status" aria-label="System status">
        <StatusBadge tone={backendTone}>{backendLabel}</StatusBadge>
        <StatusBadge tone={prismaConfigured ? "success" : "warning"}>
          Prisma {prismaConfigured ? "configured" : "not configured"}
        </StatusBadge>
        <span className="call-state"><span className="call-state__label">CALL STATE</span>{callState}</span>
      </div>
    </header>
  );
}
