import { useCallback, useEffect, useState } from "react";

import { getApiHealth } from "../services/api.js";

export function useSystemHealth() {
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState("checking");
  const [error, setError] = useState("");

  const refresh = useCallback(async (signal) => {
    setStatus("checking");
    setError("");
    try {
      const result = await getApiHealth({ signal });
      setHealth(result);
      setStatus("online");
    } catch (requestError) {
      if (requestError.name === "AbortError") {
        return;
      }
      setHealth(null);
      setStatus("offline");
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  return { health, status, error, refresh };
}
