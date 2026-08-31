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

_PROVIDER_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}


def _render_with_openai_compatible_api(*, endpoint: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int) -> str:
    payload = {"model": model, "stream": False, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}
    response = None
    for attempt in range(4):
        response = requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, timeout=timeout)
        if response.status_code != 429 or attempt == 3:
            response.raise_for_status()
            break
        retry_after = response.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else 2 * (2 ** attempt)
        except ValueError:
            delay = 2 * (2 ** attempt)
        time.sleep(delay)
    data = response.json()
    rendered = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(rendered, str) or not rendered.strip():
        raise RuntimeError("Renderer returned an empty response")
    return rendered.strip()


def render_analysis(phase: str, analysis: str, provider: str = "openrouter", model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 300) -> str:
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
    return _render_with_openai_compatible_api(endpoint=_PROVIDER_ENDPOINTS[provider_name], api_key=api_key, model=model, system_prompt=system_prompt, user_prompt=user_prompt, timeout=timeout)
