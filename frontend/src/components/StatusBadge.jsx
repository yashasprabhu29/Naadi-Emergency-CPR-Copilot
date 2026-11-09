const TONES = new Set(["neutral", "success", "warning", "danger"]);

export function StatusBadge({ tone = "neutral", children, dot = true, pulse = false }) {
  const safeTone = TONES.has(tone) ? tone : "neutral";
  return (
    <span className={`status-badge status-badge--${safeTone}`}>
      {dot && <span className={`status-badge__dot${pulse ? " status-badge__dot--pulse" : ""}`} aria-hidden="true" />}
      {children}
    </span>
  );
}
