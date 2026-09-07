"use client";

import { useEffect } from "react";

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEY = "reverse-engineer-sdlc:v1-workspace";
const TOTAL_PHASES = 11;

function readWorkspace() {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) as { runId?: string; completedPhases?: string[] } : null;
  } catch {
    return null;
  }
}

export default function V1WorkspaceDisplayControl() {
  useEffect(() => {
    let cancelled = false;

    const update = async () => {
      const stored = readWorkspace();
      if (!stored?.runId || stored.runId === "vercel-demo") return;

      let completed = stored.completedPhases?.length ?? 0;
      try {
        const response = await fetch(`${API_BASE_URL}/api/analysis/${stored.runId}/status`, { cache: "no-store" });
        if (response.ok) {
          const status = await response.json() as { completed_phases?: string[] };
          completed = status.completed_phases?.length ?? completed;
        }
      } catch {
        // Keep the last locally persisted count if the backend is temporarily unavailable.
      }

      if (cancelled) return;
      const progress = `${completed} of ${TOTAL_PHASES} phases have completed. You can read completed phases while the remaining phases continue running.`;
      document.querySelector<HTMLElement>(".progress-screen > div > p")?.replaceChildren(progress);

      const sidebarProgress = document.querySelector<HTMLElement>(".progress-label");
      if (sidebarProgress) {
        const text = sidebarProgress.textContent ?? "";
        if (text.includes("phases") || text === "Analysis") sidebarProgress.textContent =
          text === "Analysis failed" ? "Analysis failed" : `${completed} of ${TOTAL_PHASES} phases completed`;
      }

      document.querySelectorAll<HTMLElement>(".completion-banner").forEach((banner) => {
        if (banner.textContent?.includes("ANALYSIS STOPPED")) {
          const paragraph = banner.querySelector("p");
          if (paragraph) paragraph.textContent = `${completed} of ${TOTAL_PHASES} phases completed before stop.`;
        }
      });

      const sidebar = document.querySelector<HTMLElement>(".sidebar");
      const newAnalysis = sidebar?.querySelector<HTMLButtonElement>(".new-analysis");
      if (sidebar && newAnalysis && completed > 0 && !sidebar.querySelector(".v1-completed-download")) {
        const download = document.createElement("a");
        download.className = "download-button v1-completed-download";
        download.href = `${API_BASE_URL}/api/analysis/${stored.runId}/download`;
        download.download = "sdlc-documentation.zip";
        download.textContent = "Download ZIP of completed work";
        sidebar.insertBefore(download, newAnalysis);
      }
    };

    update();
    const timer = window.setInterval(update, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return null;
}
