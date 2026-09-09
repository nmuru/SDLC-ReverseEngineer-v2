"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEY = "reverse-engineer-sdlc:v1-workspace";

type ReviewState = {
  repoUrl: string;
  provider: string;
  model: string;
  apiKey: string;
  runId: string | null;
  completedPhases: string[];
  isDemo: boolean;
};

const EMPTY_STATE: ReviewState = {
  repoUrl: "",
  provider: "",
  model: "",
  apiKey: "",
  runId: null,
  completedPhases: [],
  isDemo: true,
};

export default function ReviewCodeBaseControl() {
  const [state, setState] = useState<ReviewState>(EMPTY_STATE);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const receiveState = (event: Event) => {
      const detail = (event as CustomEvent<ReviewState>).detail;
      if (detail) setState(detail);
    };

    window.addEventListener("reverse-engineer:workspace-state", receiveState);

    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const stored = JSON.parse(raw) as { runId?: string; repoUrl?: string; completedPhases?: string[] };
        setState((current) => ({
          ...current,
          runId: stored.runId && stored.runId !== "vercel-demo" ? stored.runId : null,
          repoUrl: stored.repoUrl ?? "",
          completedPhases: stored.completedPhases ?? [],
          isDemo: false,
        }));
      }
    } catch {
      // The landing page state event is authoritative once it is mounted.
    }

    return () => window.removeEventListener("reverse-engineer:workspace-state", receiveState);
  }, []);

  async function review() {
    if (!state.runId || running) return;
    setMessage("");

    if (!state.repoUrl.trim() || !state.apiKey.trim()) {
      setMessage("The repository or API key is not available. Return to the setup area and try again.");
      return;
    }

    if (state.isDemo) {
      setMessage("Review is available after running an SDLC analysis on a repository.");
      return;
    }

    setRunning(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: state.repoUrl,
          selected_phases: ["review-code-base"],
          work_id: state.runId,
          provider: state.provider,
          model: state.model,
          api_key: state.apiKey,
        }),
      });
      if (!response.ok) {
        let detail = "Review Code Base failed.";
        try {
          const data = await response.json();
          if (typeof data?.detail === "string") detail = data.detail;
        } catch {}
        throw new Error(detail);
      }
      if (!response.body) throw new Error("The review stream was not available.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const block of events) {
          const data = block
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).trim())
            .join("\n");
          if (!data) continue;
          const event = JSON.parse(data) as { type?: string; error?: string };
          if (event.type === "analysis_failed") throw new Error(event.error || "Review Code Base failed.");
          if (event.type === "analysis_completed") {
            window.location.href = `/review?runId=${encodeURIComponent(state.runId)}`;
            return;
          }
        }
      }
      window.location.href = `/review?runId=${encodeURIComponent(state.runId)}`;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review Code Base failed.");
    } finally {
      setRunning(false);
    }
  }

  if (!state.runId || state.isDemo || state.completedPhases.length === 0) return null;

  return (
    <div style={{ position: "fixed", left: 24, bottom: 92, zIndex: 40 }}>
      <button
        type="button"
        onClick={review}
        disabled={running}
        style={{
          padding: "10px 14px",
          borderRadius: 8,
          border: "1px solid #d1d5db",
          background: "white",
          color: "#111827",
          fontWeight: 600,
          cursor: running ? "wait" : "pointer",
          boxShadow: "0 2px 8px rgba(0,0,0,.12)",
        }}
      >
        {running ? "Reviewing SDLC..." : "Review SDLC"}
      </button>
      {message && (
        <div style={{ marginTop: 8, maxWidth: 280, padding: 8, borderRadius: 6, background: "#fff", border: "1px solid #fecaca", color: "#991b1b", fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
}
