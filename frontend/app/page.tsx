"use client";

import { FormEvent, useEffect, useId, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function MermaidDiagram({ chart }: { chart: string }) {
  const id = useId().replace(/:/g, "");
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    async function renderDiagram() {
      try {
        const { default: mermaid } = await import("mermaid");
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "default" });
        const cleaned = chart.trim().replace(/^```mermaid\s*/i, "").replace(/```$/i, "").trim();
        const parsed = await mermaid.parse(cleaned);
        if (!parsed) throw new Error("Mermaid could not parse the diagram.");
        const { svg: renderedSvg } = await mermaid.render(`mermaid-${id}`, cleaned);
        if (!cancelled) { setSvg(renderedSvg); setError(""); }
      } catch (err) {
        if (!cancelled) { setSvg(""); setError(err instanceof Error ? err.message : "Unable to render Mermaid diagram."); }
      }
    }
    renderDiagram();
    return () => { cancelled = true; };
  }, [chart, id]);
  if (error) return <div className="mermaid-error"><div>Diagram could not be rendered. Mermaid source is shown below.</div><pre className="markdown-code-block"><code>{chart}</code></pre></div>;
  if (!svg) return <div className="mermaid-loading">Rendering diagram...</div>;
  return <div className="mermaid-diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}

type Phase = { id: string; label: string; shortLabel: string };
type AnalysisResult = {
  repo_url: string; business_purpose: string; business_requirements: string; features: string;
  software_requirements: string; technology_architecture: string; design_pattern: string;
  high_level_design: string; low_level_design: string; implementation_detail: string;
  testing_harness: string; future_directions: string;
};
type Failure = { phase: string; phase_name: string; error_type: string; error: string };
type AnalysisEvent =
  | { type: "phase_completed"; phase: string; phase_name: string; raw_analysis: string; raw_path: string; run_id: string; provenance?: { model: string } }
  | { type: "analysis_completed"; repo_url: string; run_id: string; completed_phases: string[]; failed_phases?: Failure[] }
  | { type: "analysis_cancelled"; repo_url: string; run_id: string; completed_phases: string[]; failed_phases?: Failure[] }
  | { type: "analysis_failed"; repo_url: string; run_id?: string; error: string };
type RunStatus = { run_id: string; status: string; repo_url: string; selected_phases: string[]; completed_phases: string[]; failures: Failure[]; active_phase: string | null; results: Record<string, string> };
type StoredWorkspace = { runId: string; repoUrl: string; selectedPhases: string[]; completedPhases: string[]; activePhase: string; status: string; provenance: { model: string } | null };

const phases: Phase[] = [
  { id: "business-purpose", label: "Business Purpose", shortLabel: "Purpose" },
  { id: "business-requirements", label: "Business Requirements", shortLabel: "Business Requirements" },
  { id: "features", label: "Features", shortLabel: "Features" },
  { id: "software-requirements", label: "Software Requirements", shortLabel: "Software Requirements" },
  { id: "technology-architecture", label: "Technology Architecture", shortLabel: "Architecture" },
  { id: "design-pattern", label: "Design Pattern", shortLabel: "Design Pattern" },
  { id: "high-level-design", label: "High-Level Design", shortLabel: "HLD" },
  { id: "low-level-design", label: "Low-Level Design", shortLabel: "LLD" },
  { id: "implementation-detail", label: "Implementation Detail", shortLabel: "Implementation" },
  { id: "testing-harness", label: "Testing Harness", shortLabel: "Testing" },
  { id: "future-directions", label: "Future Directions", shortLabel: "Future" },
];
const defaultSelectedPhases = ["software-requirements", "technology-architecture", "future-directions"];
const phaseResultMap: Record<Phase["id"], keyof AnalysisResult> = {
  "business-purpose": "business_purpose", "business-requirements": "business_requirements", features: "features",
  "software-requirements": "software_requirements", "technology-architecture": "technology_architecture",
  "design-pattern": "design_pattern", "high-level-design": "high_level_design", "low-level-design": "low_level_design",
  "implementation-detail": "implementation_detail", "testing-harness": "testing_harness", "future-directions": "future_directions",
};
const API_BASE_URL = "http://localhost:8000";
const DEMO_REPO_URL = "https://github.com/vercel/commerce";
const DEMO_RUN_ID = "vercel-demo";
const providers = [
  { id: "openrouter", label: "OpenRouter", placeholder: "e.g. openai/gpt-5, anthropic/claude-sonnet-4" },
  { id: "openai", label: "OpenAI", placeholder: "e.g. gpt-5" },
];
const STORAGE_KEY = "reverse-engineer-sdlc:v1-workspace";

function emptyResult(repoUrl = ""): AnalysisResult {
  return { repo_url: repoUrl, business_purpose: "", business_requirements: "", features: "", software_requirements: "", technology_architecture: "", design_pattern: "", high_level_design: "", low_level_design: "", implementation_detail: "", testing_harness: "", future_directions: "" };
}
function makeRunId() { return (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`).replace(/[^a-zA-Z0-9]/g, ""); }

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [provider, setProvider] = useState("openrouter");
  const [model, setModel] = useState("openrouter/free");
  const [apiKey, setApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState("business-purpose");
  const [completedPhases, setCompletedPhases] = useState<string[]>([]);
  const [completionMessages, setCompletionMessages] = useState<string[]>([]);
  const [selectedPhases, setSelectedPhases] = useState<string[]>(defaultSelectedPhases);
  const [selectionView, setSelectionView] = useState<"setup" | null>(null);
  const [isDemo, setIsDemo] = useState(true);
  const [loading, setLoading] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [error, setError] = useState("");
  const [failedPhases, setFailedPhases] = useState<string[]>([]);
  const [provenance, setProvenance] = useState<{ model: string } | null>(null);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function restoreWorkspace() {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        if (!raw) { setRestored(true); return; }
        const stored = JSON.parse(raw) as StoredWorkspace;
        if (!stored.runId || stored.runId === DEMO_RUN_ID) { window.sessionStorage.removeItem(STORAGE_KEY); setRestored(true); return; }
        setRepoUrl(stored.repoUrl); setRunId(stored.runId); setSelectedPhases(stored.selectedPhases?.length ? stored.selectedPhases : defaultSelectedPhases);
        setCompletedPhases(stored.completedPhases ?? []); setActivePhase(stored.activePhase || stored.completedPhases?.[stored.completedPhases.length - 1] || stored.selectedPhases?.[0] || phases[0].id);
        setAnalysisStarted(true); setIsDemo(false); setProvenance(stored.provenance ?? null);
        const response = await fetch(`${API_BASE_URL}/api/analysis/${stored.runId}/status`, { cache: "no-store" });
        if (!response.ok) throw new Error("Saved analysis state is no longer available on the backend.");
        const status = await response.json() as RunStatus;
        if (cancelled) return;
        applyStatus(status);
      } catch (err) {
        if (!cancelled) { window.sessionStorage.removeItem(STORAGE_KEY); setError(err instanceof Error ? err.message : "Unable to restore the previous analysis."); }
      } finally { if (!cancelled) setRestored(true); }
    }
    restoreWorkspace();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!analysisStarted || isDemo || !runId || !restored || analysisComplete || stopped) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/analysis/${runId}/status`, { cache: "no-store" });
        if (!response.ok) return;
        const status = await response.json() as RunStatus;
        if (!cancelled) applyStatus(status);
      } catch { /* SSE is primary during the original request; polling is the refresh fallback. */ }
    };
    poll();
    const timer = window.setInterval(poll, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [analysisStarted, isDemo, runId, restored, analysisComplete, stopped]);

  useEffect(() => {
    if (!analysisStarted || isDemo || !runId) return;
    const snapshot: StoredWorkspace = { runId, repoUrl, selectedPhases, completedPhases, activePhase, status: stopped ? "cancelled" : analysisComplete ? "completed" : stopping ? "cancelling" : "running", provenance };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  }, [analysisStarted, isDemo, runId, repoUrl, selectedPhases, completedPhases, activePhase, stopped, analysisComplete, stopping, provenance]);

  function applyStatus(status: RunStatus) {
    setRunId(status.run_id); setRepoUrl(status.repo_url); setSelectedPhases(status.selected_phases?.length ? status.selected_phases : defaultSelectedPhases);
    setCompletedPhases(status.completed_phases ?? []); setActivePhase(status.active_phase || status.completed_phases?.[status.completed_phases.length - 1] || status.selected_phases?.[0] || phases[0].id);
    setFailedPhases((status.failures ?? []).map((failure) => failure.phase));
    setAnalysisResult((previous) => {
      const next = { ...(previous ?? emptyResult(status.repo_url)), repo_url: status.repo_url };
      for (const [phase, content] of Object.entries(status.results ?? {})) { const key = phaseResultMap[phase as Phase["id"]]; if (key) next[key] = content; }
      return next;
    });
    if (status.status === "completed") { setAnalysisComplete(true); setLoading(false); setStopping(false); setStopped(false); }
    else if (status.status === "cancelled") { setAnalysisComplete(false); setLoading(false); setStopping(false); setStopped(true); }
    else if (status.status === "failed") { setAnalysisComplete(false); setLoading(false); setStopping(false); setError("The analysis could not continue."); }
    else { setAnalysisComplete(false); setLoading(true); if (status.status === "cancelling") setStopping(true); }
  }

  async function loadDemoDocumentation() {
    try {
      const documents = await Promise.all(phases.map(async (phase) => { const response = await fetch(`/vercel-demo/${phase.id}.md`); if (!response.ok) throw new Error(`Unable to load demo document: ${phase.id}.md (${response.status})`); return [phase.id, await response.text()] as const; }));
      const result = emptyResult(DEMO_REPO_URL); for (const [phaseId, content] of documents) result[phaseResultMap[phaseId as Phase["id"]]] = content; setAnalysisResult(result);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load the Vercel Commerce demo documentation."); }
  }
  useEffect(() => { if (restored && !window.sessionStorage.getItem(STORAGE_KEY)) loadDemoDocumentation(); }, [restored]);

  function viewDemo() {
    if (!analysisResult) return;
    setError(""); setRepoUrl(DEMO_REPO_URL); setRunId(DEMO_RUN_ID); setIsDemo(true); setAnalysisStarted(true); setAnalysisComplete(true); setStopped(false);
    setCompletedPhases(phases.map((phase) => phase.id)); setActivePhase(phases[0].id); setSelectionView(null); setFailedPhases([]); setProvenance(null);
  }

  async function analyze(event: FormEvent) {
    event.preventDefault();
    const phasesToRun = selectedPhases;
    if (!provider || !model.trim() || !apiKey.trim()) { setError("Enter an AI provider, model, and API key before starting."); return; }
    if (!repoUrl.trim() || phasesToRun.length === 0) { setError("Enter a repository URL and select at least one SDLC phase before starting."); return; }
    const nextRunId = runId && !isDemo ? runId : makeRunId();
    setRunId(nextRunId); setLoading(true); setStopping(false); setStopped(false); setIsDemo(false); setAnalysisStarted(true); setSelectionView(null); setAnalysisComplete(false); setError(""); setFailedPhases([]);
    setCompletionMessages([]); setActivePhase(phasesToRun[0]);
    setCompletedPhases((previous) => isDemo ? [] : previous.filter((phase) => phasesToRun.includes(phase)));
    setAnalysisResult(isDemo ? emptyResult(repoUrl) : (analysisResult ?? emptyResult(repoUrl)));
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, { method: "POST", headers: { Accept: "text/event-stream", "Content-Type": "application/json" }, body: JSON.stringify({ repo_url: repoUrl, selected_phases: phasesToRun, work_id: nextRunId, provider, model, api_key: apiKey }) });
      if (!response.ok) { let message = "Analysis failed."; try { const data = await response.json(); if (typeof data?.detail === "string") message = data.detail; } catch {} throw new Error(message); }
      if (!response.body) throw new Error("The analysis stream was not available.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true }); const events = buffer.split("\n\n"); buffer = events.pop() ?? "";
        for (const eventBlock of events) {
          const dataLines = eventBlock.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()); if (!dataLines.length) continue;
          let eventData: AnalysisEvent; try { eventData = JSON.parse(dataLines.join("\n")) as AnalysisEvent; } catch { continue; }
          if (eventData.type === "phase_completed") {
            setRunId(eventData.run_id); setProvenance(eventData.provenance ? { model: eventData.provenance.model } : { model }); setCompletionMessages((previous) => previous.includes(eventData.phase_name) ? previous : [...previous, `${eventData.phase_name} phase completed`]);
            const resultKey = phaseResultMap[eventData.phase as Phase["id"]];
            if (resultKey) { setAnalysisResult((previous) => ({ ...(previous ?? emptyResult(repoUrl)), repo_url: repoUrl, [resultKey]: eventData.raw_analysis })); setCompletedPhases((previous) => previous.includes(eventData.phase) ? previous : [...previous, eventData.phase]); setActivePhase(eventData.phase); }
          } else if (eventData.type === "analysis_completed") {
            setRunId(eventData.run_id); setAnalysisComplete(true); setLoading(false); setStopping(false); setStopped(false); setFailedPhases((eventData.failed_phases ?? []).map((failure) => failure.phase)); if ((eventData.failed_phases ?? []).length) setError(`${eventData.failed_phases.length} selected phase${eventData.failed_phases.length === 1 ? "" : "s"} could not be completed.`);
          } else if (eventData.type === "analysis_cancelled") {
            setRunId(eventData.run_id); setAnalysisComplete(false); setLoading(false); setStopping(false); setStopped(true); setCompletedPhases(eventData.completed_phases ?? []); setFailedPhases((eventData.failed_phases ?? []).map((failure) => failure.phase));
          } else if (eventData.type === "analysis_failed") { setError(eventData.error); setAnalysisComplete(false); setLoading(false); setStopping(false); }
        }
      }
    } catch (err) { if (!stopped) { setError(err instanceof Error ? err.message : "Analysis failed."); setAnalysisComplete(false); setLoading(false); } }
  }

  async function stopAnalysis() {
    if (!runId || stopping || !loading) return;
    if (!window.confirm("Stop this analysis? No further phases will be started. Completed results will remain available.")) return;
    setStopping(true); setError("");
    try { const response = await fetch(`${API_BASE_URL}/api/analysis/${runId}/stop`, { method: "POST" }); if (!response.ok) throw new Error("The backend did not accept the stop request."); const status = await response.json() as RunStatus; applyStatus(status); }
    catch (err) { setStopping(false); setError(err instanceof Error ? err.message : "Unable to stop the analysis."); }
  }

  function resetAnalysis() {
    window.sessionStorage.removeItem(STORAGE_KEY); setAnalysisStarted(false); setIsDemo(false); setAnalysisComplete(false); setCompletedPhases([]); setCompletionMessages([]); setRepoUrl(""); setRunId(null); setProvider("openrouter"); setModel("openrouter/free"); setApiKey(""); setShowApiKey(false); setSelectedPhases(defaultSelectedPhases); setSelectionView(null); setActivePhase(phases[0].id); setAnalysisResult(null); setError(""); setLoading(false); setStopping(false); setStopped(false); setFailedPhases([]); setProvenance(null);
  }

  const activePhaseDefinition = phases.find((phase) => phase.id === activePhase) ?? phases[0];
  const activeResultKey = phaseResultMap[activePhaseDefinition.id];
  const activeResult = analysisResult && activeResultKey ? analysisResult[activeResultKey] : "";
  const denominator = selectedPhases.length || phases.length;
  const progressText = `${completedPhases.length} of ${denominator} phases have completed. You can read completed phases while the remaining phases continue running.`;

  return <div className="app-shell">
    <header className="topbar"><div><div className="brand">ReverseEngineer-SDLC</div><div className="tagline">Repository → Software Engineering Dossier</div></div>{analysisStarted && repoUrl && <div className="repo-pill" title={repoUrl}>{repoUrl.replace(/^https?:\/\//, "")}</div>}</header>
    {!analysisStarted ? <main className="landing"><div className="landing-card"><div className="eyebrow">AI SOFTWARE REVERSE ENGINEERING</div><h1>Turn a GitHub repository into an SDLC dossier.</h1><p className="landing-copy">Submit a repository URL to progressively reconstruct its business purpose, business requirements, features, software requirements, architecture, design, implementation, testing strategy, and future directions.</p>
      <fieldset className="phase-selection" style={{ marginTop: 28 }}><legend>AI model</legend><div style={{ display: "grid", gap: 14 }}><label style={{ display: "grid", gap: 7 }}><span style={{ fontSize: 13, fontWeight: 700 }}>Provider</span><select value={provider} onChange={(event) => setProvider(event.target.value)} disabled={loading} aria-label="AI provider">{providers.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label style={{ display: "grid", gap: 7 }}><span style={{ fontSize: 13, fontWeight: 700 }}>Model</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder={providers.find((item) => item.id === provider)?.placeholder} disabled={loading} required aria-label="AI model" autoComplete="off" /></label><label style={{ display: "grid", gap: 7 }}><span style={{ fontSize: 13, fontWeight: 700 }}>API key</span><div style={{ display: "flex", gap: 8 }}><input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type={showApiKey ? "text" : "password"} placeholder="Enter your API key" disabled={loading} required aria-label="AI provider API key" autoComplete="off" /><button type="button" onClick={() => setShowApiKey((value) => !value)} disabled={loading}>{showApiKey ? "Hide" : "Show"}</button></div></label><p style={{ margin: 0, color: "var(--muted)", fontSize: 12 }}>Your API key is used for this analysis request and is not saved by this frontend.</p></div></fieldset>
      <form onSubmit={analyze} className="repo-form"><input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repository" type="url" required aria-label="GitHub repository URL" /><button type="submit" disabled={loading}>{loading ? "Reverse engineering..." : "Reverse engineer"}</button></form>
      <fieldset className="phase-selection"><legend>Select SDLC phases</legend><div className="phase-selection-grid">{phases.map((phase) => <label key={phase.id} className="phase-option"><input type="checkbox" checked={selectedPhases.includes(phase.id)} onChange={() => setSelectedPhases((previous) => previous.includes(phase.id) ? previous.filter((id) => id !== phase.id) : [...previous, phase.id])} disabled={loading} /><span>{phase.label}</span></label>)}</div></fieldset>
      {error && <div className="error-banner" role="alert">{error}</div>}<button type="button" onClick={viewDemo} disabled={loading || !analysisResult} style={{ width: "100%", marginTop: 14, minHeight: 44, border: "1px solid var(--accent)", borderRadius: 9, background: "var(--accent)", color: "white", fontWeight: 700 }}>View Vercel Commerce example</button><div className="landing-note">Analysis is performed by the backend coding-agent pipeline.</div>
    </div></main> : <div className="workspace">
      <aside className="sidebar"><div className="sidebar-heading">SDLC Dossier</div><div className="progress-label">{loading ? progressText : analysisComplete ? "Analysis complete" : stopped ? `${completedPhases.length} of ${denominator} phases completed before stop` : error ? "Analysis failed" : "Analysis"}</div><nav className="phase-nav" aria-label="SDLC phases"><button className={`phase-tab selection-tab ${selectionView === "setup" ? "active" : ""}`} onClick={() => setSelectionView("setup")}><span className="phase-number">00</span><span className="phase-name">Repository & phases</span><span className="phase-status">•</span></button>{phases.map((phase, index) => { const complete = completedPhases.includes(phase.id); return <button key={phase.id} className={`phase-tab ${activePhase === phase.id ? "active" : ""} ${!complete ? "locked" : ""}`} onClick={() => { if (complete) { setSelectionView(null); setActivePhase(phase.id); } }} disabled={!complete}><span className="phase-number">{String(index + 1).padStart(2, "0")}</span><span className="phase-name">{phase.label}</span><span className={`phase-status ${complete ? "done" : ""}`}>{complete ? "✓" : "•"}</span></button>; })}</nav><button className="new-analysis" onClick={resetAnalysis} disabled={loading || stopping}>+ New repository</button></aside>
      <main className="content">
        {selectionView === "setup" ? <section className="selection-panel"><div className="eyebrow">ANALYSIS SETUP</div><h1>Continue or rerun phases</h1><p className="section-intro">Select the phases you want to run. Completed phases remain readable and can be rerun using the same work ID after the current run has stopped or completed.</p><fieldset className="phase-selection"><legend>Run phases</legend><div className="phase-selection-grid">{phases.map((phase) => <label key={phase.id} className="phase-option"><input type="checkbox" checked={selectedPhases.includes(phase.id)} onChange={() => setSelectedPhases((previous) => previous.includes(phase.id) ? previous.filter((id) => id !== phase.id) : [...previous, phase.id])} disabled={loading || stopping} /><span>{phase.label}{completedPhases.includes(phase.id) ? " (completed, rerunnable)" : ""}</span></label>)}</div></fieldset><form onSubmit={analyze} className="repo-form"><input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repository" type="url" required aria-label="GitHub repository URL" disabled={loading || stopping} /><button type="submit" disabled={loading || stopping}>{loading ? "Running..." : "Run selected phases"}</button></form>{error && <div className="error-banner" role="alert">{error}</div>}</section>
        : isDemo ? <><section className="completion-banner"><div><div className="eyebrow">EXAMPLE DOCUMENTATION</div><h1>Vercel Commerce software dossier</h1><p>Browse the pre-generated eleven-phase reverse-engineering documentation.</p></div><div className="completion-mark">✓</div></section><section className="dossier-content"><div className="eyebrow">STAGE {String(phases.findIndex((phase) => phase.id === activePhase) + 1).padStart(2, "0")}</div><h2>{activePhaseDefinition.label}</h2><p className="section-intro">Pre-generated reverse-engineering documentation for the Vercel Commerce repository.</p><article className="evidence-card markdown-content">{activeResult ? <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code({ className, children, ...props }) { if (/language-mermaid/.test(className || "")) return <MermaidDiagram chart={String(children).replace(/\n$/, "")} />; return <code className={className} {...props}>{children}</code>; } }}>{activeResult}</ReactMarkdown> : <div className="mermaid-loading">Loading Vercel Commerce documentation...</div>}</article></section></>
        : <>{loading && <section className="progress-screen"><div className="spinner"/><div><div className="eyebrow">ANALYSIS IN PROGRESS</div><h1>Results are arriving progressively</h1><p>{progressText}</p>{stopping ? <p style={{ fontWeight: 700 }}>Stop requested. Waiting for the current backend work to unwind safely.</p> : <button type="button" onClick={stopAnalysis} disabled={stopping} style={{ minHeight: 42, padding: "0 16px", border: "1px solid #b42318", borderRadius: 8, background: "white", color: "#b42318", fontWeight: 700 }}>{stopping ? "Stopping analysis..." : "Stop analysis"}</button>}{completionMessages.length > 0 && <div className="completion-messages" aria-live="polite">{completionMessages.map((message) => <div key={message}>{message}</div>)}</div>}</div></section>}
          {stopped && <section className="completion-banner" style={{ borderColor: "#ead9c5", background: "#fffaf3" }}><div><div className="eyebrow">ANALYSIS STOPPED</div><h1>The analysis was stopped by the user.</h1><p>{completedPhases.length} of {denominator} phases completed before stop.</p><button type="button" onClick={resetAnalysis} style={{ marginTop: 14, minHeight: 42, padding: "0 16px", border: 0, borderRadius: 8, background: "var(--accent)", color: "white", fontWeight: 700 }}>Back to Main Page</button></div></section>}
          {analysisComplete && <section className="completion-banner"><div><div className="eyebrow">REVERSE ENGINEERING COMPLETE</div><h1>Your software dossier is ready.</h1><p>Visit the individual SDLC tabs on the left to explore the reconstructed system.</p></div><div className="completion-mark">✓</div>{runId && <a className="download-button" href={`${API_BASE_URL}/api/analysis/${runId}/download`} download="sdlc-documentation.zip">Download ZIP</a>}</section>}
          {activeResult && <section className="dossier-content"><div className="eyebrow">STAGE {String(phases.findIndex((phase) => phase.id === activePhase) + 1).padStart(2, "0")}</div><h2>{activePhaseDefinition.label}</h2><p className="section-intro">Analysis returned by the backend coding-agent pipeline for this SDLC phase.{provenance ? ` Model: ${provenance.model}` : ""}</p><article className="evidence-card markdown-content"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code({ className, children, ...props }) { if (/language-mermaid/.test(className || "")) return <MermaidDiagram chart={String(children).replace(/\n$/, "")} />; return <code className={className} {...props}>{children}</code>; } }}>{activeResult}</ReactMarkdown></article></section>}
          {!loading && !stopped && !analysisComplete && !activeResult && error && <section className="progress-screen"><div><div className="eyebrow">ANALYSIS FAILED</div><h1>The analysis could not continue.</h1><p>{error}</p></div></section>}
        </>}
      </main>
    </div>}
  </div>;
}
