"""Thin client for the local Ollama chat API."""

from __future__ import annotations

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaError(Exception):
    """Raised when Ollama returns an error or is unreachable."""


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    timeout: float = 120.0,
) -> str:
    """Send a chat completion request to Ollama and return the assistant reply."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    url = f"{OLLAMA_BASE_URL}/api/chat"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.ConnectError as exc:
        raise OllamaError(
            "Cannot reach Ollama. Run `ollama serve` and `ollama pull llama3`."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaError(f"Ollama HTTP {exc.response.status_code}: {exc.response.text}") from exc

    data = response.json()
    message = data.get("message") or {}
    content = message.get("content", "").strip()
    if not content:
        raise OllamaError("Ollama returned an empty response.")
    return content


def health_check(*, model: str | None = None) -> bool:
    """Return True if Ollama is up and the configured model is available."""
    target = model or OLLAMA_MODEL
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
        names = {m.get("name", "").split(":")[0] for m in response.json().get("models", [])}
        return target.split(":")[0] in names or any(n.startswith(target) for n in names)
    except (httpx.HTTPError, OllamaError):
        return False
