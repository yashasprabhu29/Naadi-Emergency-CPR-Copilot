export function StatusBadge({ tone = "neutral", children, dot = true }) {
  return (
    <span className={`status-badge status-badge--${tone}`}>
      {dot && <span className="status-badge__dot" aria-hidden="true" />}
      {children}
    </span>
  );
}
