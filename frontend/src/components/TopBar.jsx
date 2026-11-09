import { Link } from "../router.jsx";
import { SITE } from "../site.js";
import { NaadiMark } from "./Icons.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

const NAV = [
  { to: "/", label: "Console" },
  { to: "/calls", label: "Call log" },
  { to: "/privacy", label: "Privacy" },
  { to: "/terms", label: "Terms" },
];

export function TopBar({ path, backendStatus, prismaConfigured, callState }) {
  const showStatus = backendStatus !== undefined;
  const backendTone = backendStatus === "online" ? "success" : backendStatus === "offline" ? "danger" : "warning";
  const backendLabel = backendStatus === "online" ? "Backend online" : backendStatus === "offline" ? "Backend offline" : "Checking backend";

  return (
    <header className="topbar">
      <div className="topbar__inner">
        <Link to="/" className="brand" aria-label={`${SITE.name} console home`}>
          <NaadiMark />
          <span className="brand__text">
            <span className="brand__name">
              {SITE.name} <span lang="kn" className="brand__kn">{SITE.nameKannada}</span>
            </span>
            <span className="brand__subtitle">Emergency call-taker copilot</span>
          </span>
        </Link>

        <nav className="topnav" aria-label="Primary">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`topnav__link${path === item.to ? " topnav__link--active" : ""}`}
              aria-current={path === item.to ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {showStatus && (
          <div className="topbar__status" aria-label="System status">
            <StatusBadge tone={backendTone}>{backendLabel}</StatusBadge>
            <StatusBadge tone={prismaConfigured ? "success" : "warning"}>
              Prisma {prismaConfigured ? "configured" : "not configured"}
            </StatusBadge>
            <span className="call-state">
              <span className="call-state__label">Call state</span>
              <span className="call-state__value">{callState}</span>
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
