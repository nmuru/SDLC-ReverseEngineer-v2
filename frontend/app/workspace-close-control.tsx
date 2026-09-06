"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEY = "reverse-engineer-sdlc:v1-workspace";

export default function WorkspaceCloseControl() {
  const [runId, setRunId] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => {
      try {
        // Legacy localStorage was shared by every localhost tab. Remove it so
        // older V1 workspaces can never be restored by the new UI.
        window.localStorage.removeItem(STORAGE_KEY);
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        const stored = raw ? JSON.parse(raw) as { runId?: string } : null;
        setRunId(stored?.runId && stored.runId !== "vercel-demo" ? stored.runId : null);
      } catch {
        setRunId(null);
      }
    };
    refresh();
    window.addEventListener("storage", refresh);
    const timer = window.setInterval(refresh, 1000);
    return () => {
      window.removeEventListener("storage", refresh);
      window.clearInterval(timer);
    };
  }, []);

  async function closeWorkspace() {
    if (!runId) return;
    if (!window.confirm("Close this workspace? In production mode its server-side output will be removed. Refreshing the page does not close the workspace.")) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/analysis/${runId}/close`, { method: "POST", keepalive: true });
      if (!response.ok) throw new Error("The backend did not accept the workspace close request.");
      window.sessionStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(STORAGE_KEY);
      window.location.reload();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Unable to close the workspace.");
    }
  }

  if (!runId) return null;

  return <button type="button" onClick={closeWorkspace} style={{ position: "fixed", top: 14, right: 14, zIndex: 50, minHeight: 34, padding: "0 12px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--text)", fontSize: 12, fontWeight: 700 }}>Close workspace</button>;
}
