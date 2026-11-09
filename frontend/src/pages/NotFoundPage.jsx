import { PulseTrace } from "../components/PulseTrace.jsx";
import { Link } from "../router.jsx";

export function NotFoundPage() {
  return (
    <main className="not-found" id="main">
      <div className="not-found__card reveal" style={{ "--reveal-order": 1 }}>
        <PulseTrace className="pulse-trace--flat" />
        <p className="eyebrow">Error 404</p>
        <h1>This page does not exist</h1>
        <p>The address may be mistyped, or the page may have moved.</p>
        <Link to="/" className="button button--primary">Go to the console</Link>
      </div>
    </main>
  );
}
