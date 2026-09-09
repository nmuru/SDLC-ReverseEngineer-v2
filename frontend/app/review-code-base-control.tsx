"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEY = "reverse-engineer-sdlc:v1-workspace";

function readInputValue(selector: string): string {
  const element = document.querySelector(selector) as HTMLInputElement | HTMLSelectElement | null;
  return element?.value?.trim() ?? "";
}

export default function ReviewCodeBaseControl() {
  const [runId, setRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const refresh = () => {
      try {
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        if (!raw) { setRunId(null); return; }
        const stored = JSON.parse(raw) as { runId?: string; isDemo?: boolean };
        setRunId(stored.runId && stored.runId !== "vercel-demo" ? stored.runId : null);
      } catch { setRunId(null); }
    };
    refresh();
    const timer = window.setInterval(refresh, 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function review() {
    if (!runId || running) return;
    setMessage("");
    const repoUrl = readInputValue('input[placeholder*="github.com"], input[type="url"]');
    const model = readInputValue('input[placeholder*="e.g."]') || "openrouter/free";
    const provider = readInputValue("select") || "openrouter";
    const apiKey = readInputValue('input[type="password"]');
    if (!repoUrl || !apiKey) {
      setMessage("Enter the repository and API key before reviewing.");
      return;
    }
    setRunning(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, selected_phases: ["review-code-base"], work_id: runId, provider, model, api_key: apiKey }),
      });
      if (!response.ok) {
        let detail = "Review Code Base failed.";
        try { const data = await response.json(); if (typeof data?.detail === "string") detail = data.detail; } catch {}
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
          const data = block.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
          if (!data) continue;
          const event = JSON.parse(data) as { type?: string; error?: string };
          if (event.type === "analysis_failed") throw new Error(event.error || "Review Code Base failed.");
          if (event.type === "analysis_completed") {
            window.location.href = `/review?runId=${encodeURIComponent(runId)}`;
            return;
          }
        }
      }
      window.location.href = `/review?runId=${encodeURIComponent(runId)}`;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review Code Base failed.");
    } finally {
      setRunning(false);
    }
  }

  if (!runId) return null;

  return <div style={{ position: "fixed", left: 24, bottom: 92, zIndex: 40 }}>
    <button type="button" onClick={review} disabled={running} style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #d1d5db", background: "white", color: "#111827", fontWeight: 600, cursor: running ? "wait" : "pointer", boxShadow: "0 2px 8px rgba(0,0,0,.12)" }}>
      {running ? "Reviewing Code Base..." : "Review Code Base"}
    </button>
    {message && <div style={{ marginTop: 8, maxWidth: 280, padding: 8, borderRadius: 6, background: "#fff", border: "1px solid #fecaca", color: "#991b1b", fontSize: 12 }}>{message}</div>}
  </div>;
}
