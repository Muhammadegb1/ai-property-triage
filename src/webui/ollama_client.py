"""
Ollama client: a simple wrapper around the Ollama API for chatting with the language model.
"""

from __future__ import annotations

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, REQUEST_TIMEOUT


class OllamaError(Exception):
    pass


def health_check() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def chat(messages: list[dict]) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except requests.RequestException as exc:
        raise OllamaError(f"Ollama request failed: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise OllamaError(f"Unexpected Ollama response: {exc}") from exc
