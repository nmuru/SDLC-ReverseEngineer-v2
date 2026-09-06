"""
Presentation-stage renderer for reverse-engineering phase results.

The analysis stage is responsible for repository exploration and reasoning.
The rendering stage is repository-blind and receives the complete raw output.
"""

from typing import Optional
import time
import requests
from .config import settings
from .render_prompt import build_render_prompt
from .resource_diagnostics import ResourceDiagnostics
from .run_control import RunCancelled, RunControl

_PROVIDER_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}


def _render_with_openai_compatible_api(*, endpoint: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int, phase: str = "", diagnostics: Optional[ResourceDiagnostics] = None, run_control: Optional[RunControl] = None) -> str:
    payload = {"model": model, "stream": False, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}
    response = None
    for attempt in range(4):
        if run_control and run_control.is_cancelled():
            raise RunCancelled("Analysis stopped by the user.")
        started = time.monotonic()
        if diagnostics:
            diagnostics.run_event("renderer_started", phase=phase, model=model, attempt=attempt + 1)
        try:
            response = requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, timeout=timeout)
            elapsed = round(time.monotonic() - started, 3)
            if run_control and run_control.is_cancelled():
                if diagnostics:
                    diagnostics.run_event("renderer_cancelled", phase=phase, model=model, attempt=attempt + 1, elapsed_seconds=elapsed)
                raise RunCancelled("Analysis stopped by the user.")
            if response.status_code != 429 or attempt == 3:
                response.raise_for_status()
                if diagnostics:
                    diagnostics.run_event("renderer_finished", phase=phase, model=model, attempt=attempt + 1, elapsed_seconds=elapsed, status_code=response.status_code)
                break
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2 * (2 ** attempt)
            except ValueError:
                delay = 2 * (2 ** attempt)
            if diagnostics:
                diagnostics.run_event("renderer_retry", phase=phase, model=model, attempt=attempt + 1, elapsed_seconds=elapsed, delay_seconds=delay, status_code=429)
            if run_control and run_control.cancel_event.wait(delay):
                raise RunCancelled("Analysis stopped by the user.")
        except RunCancelled:
            raise
        except Exception as exc:
            elapsed = round(time.monotonic() - started, 3)
            if diagnostics:
                diagnostics.run_event("renderer_failed", phase=phase, model=model, attempt=attempt + 1, elapsed_seconds=elapsed, error_type=type(exc).__name__, error=str(exc))
            raise
    data = response.json()
    rendered = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(rendered, str) or not rendered.strip():
        if diagnostics:
            diagnostics.run_event("renderer_failed", phase=phase, model=model, error_type="EmptyResponse", error="Renderer returned an empty response")
        raise RuntimeError("Renderer returned an empty response")
    return rendered.strip()


def render_analysis(phase: str, analysis: str, provider: str = "openrouter", model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 300, diagnostics: Optional[ResourceDiagnostics] = None, run_control: Optional[RunControl] = None) -> str:
    if not analysis or not analysis.strip():
        raise ValueError("analysis cannot be empty")
    provider_name = (provider or "openrouter").strip().lower()
    if provider_name not in _PROVIDER_ENDPOINTS:
        raise ValueError(f"Unsupported renderer provider: {provider_name}. Supported providers are: openrouter, openai")
    if not model or not model.strip():
        model = settings.agent_model
    if not api_key or not api_key.strip():
        raise ValueError(f"An API key is required for renderer provider '{provider_name}'.")
    system_prompt, user_prompt = build_render_prompt(phase, analysis)
    return _render_with_openai_compatible_api(endpoint=_PROVIDER_ENDPOINTS[provider_name], api_key=api_key, model=model, system_prompt=system_prompt, user_prompt=user_prompt, timeout=timeout, phase=phase, diagnostics=diagnostics, run_control=run_control)
