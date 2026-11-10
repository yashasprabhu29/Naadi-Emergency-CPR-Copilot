import { useEffect, useState } from "react";

import { Footer } from "./components/Footer.jsx";
import { TopBar } from "./components/TopBar.jsx";
import { useSystemHealth } from "./hooks/useSystemHealth.js";
import { CallLogPage } from "./pages/CallLogPage.jsx";
import { ConsolePage } from "./pages/ConsolePage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";
import { PrivacyPage } from "./pages/PrivacyPage.jsx";
import { TermsPage } from "./pages/TermsPage.jsx";
import { usePath } from "./router.jsx";

const TITLES = {
  "/": "Naadi | Emergency call-taker copilot",
  "/calls": "Call log | Naadi",
  "/privacy": "Privacy policy | Naadi",
  "/terms": "Terms and conditions | Naadi",
};

export default function App() {
  const path = usePath();
  const { health, status: healthStatus, error: healthError, refresh } = useSystemHealth();
  const [callState, setCallState] = useState("Ready for intake");

  const isConsole = path === "/";

  useEffect(() => {
    document.title = TITLES[path] || "Page not found | Naadi";
  }, [path]);

  let page;
  if (isConsole) {
    page = (
      <ConsolePage
        health={health}
        healthStatus={healthStatus}
        healthError={healthError}
        onRefreshHealth={refresh}
        onCallStateChange={setCallState}
      />
    );
  } else if (path === "/calls") {
    page = <CallLogPage />;
  } else if (path === "/privacy") {
    page = <PrivacyPage />;
  } else if (path === "/terms") {
    page = <TermsPage />;
  } else {
    page = <NotFoundPage />;
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <TopBar
        path={path}
        backendStatus={isConsole ? healthStatus : undefined}
        prismaConfigured={Boolean(health?.gnani_api_key_configured)}
        callState={callState}
      />
      <div key={path} className="page">{page}</div>
      <Footer />
    </div>
  );
}
