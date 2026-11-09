// A decorative ECG-style trace. A bright segment travels along a faint baseline.
const TRACE =
  "M0 30 H46 L52 26 L58 30 H70 L76 8 L84 44 L90 30 H104 L112 22 L122 30 H166 L172 26 L178 30 H190 L196 8 L204 44 L210 30 H224 L232 22 L240 30";

export function PulseTrace({ className = "" }) {
  return (
    <svg className={`pulse-trace ${className}`} viewBox="0 0 240 52" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path className="pulse-trace__base" d={TRACE} pathLength="300" />
      <path className="pulse-trace__head" d={TRACE} pathLength="300" />
    </svg>
  );
}
