"""
Ollama client: thin wrapper around the Ollama HTTP API.
"""
from __future__ import annotations

import json
from collections.abc import Generator

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


def chat_stream(messages: list[dict]) -> Generator[str, None, None]:
    """Yield text chunks as they stream from Ollama."""
    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": True},
            timeout=REQUEST_TIMEOUT,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if not data.get("done"):
                        yield data["message"]["content"]
    except requests.RequestException as exc:
        raise OllamaError(f"Ollama request failed: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise OllamaError(f"Unexpected Ollama response: {exc}") from exc
