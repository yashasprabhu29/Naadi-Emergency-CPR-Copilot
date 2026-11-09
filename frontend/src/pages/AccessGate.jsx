import { useState } from "react";

import { PulseTrace } from "../components/PulseTrace.jsx";
import { Link } from "../router.jsx";
import { setAccessCode, verifyAccessCode } from "../services/api.js";
import { SITE } from "../site.js";

/** Shown on public deployments until the visitor enters the access code. */
export function AccessGate({ onUnlocked }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!code.trim() || checking) return;
    setChecking(true);
    setError("");
    try {
      await verifyAccessCode(code.trim());
      setAccessCode(code.trim());
      onUnlocked();
    } catch (verifyError) {
      setError(verifyError.message);
    } finally {
      setChecking(false);
    }
  }

  return (
    <main className="gate" id="main">
      <form className="gate__card panel reveal" onSubmit={submit} aria-labelledby="gate-title">
        <PulseTrace className="pulse-trace--run" />
        <p className="eyebrow">Demo access</p>
        <h1 id="gate-title">Enter the access code</h1>
        <p className="gate__copy">
          Naadi runs on a limited pool of Gnani AI credits, so the console is open to judges and testers with a code.
          Ask the team at <a href={`mailto:${SITE.contactEmail}`}>{SITE.contactEmail}</a> for one.
        </p>
        <label className="gate__label" htmlFor="access-code">Access code</label>
        <input
          id="access-code"
          className="gate__input"
          type="password"
          autoComplete="off"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          autoFocus
        />
        {error && <p className="inline-alert inline-alert--danger" role="alert">{error}</p>}
        <button type="submit" className="button button--primary button--full" disabled={!code.trim() || checking}>
          {checking ? "Checking" : "Open the console"}
        </button>
        <p className="gate__foot">
          The code is kept only in this browser tab. <Link to="/privacy">Privacy policy</Link>
        </p>
      </form>
    </main>
  );
}
