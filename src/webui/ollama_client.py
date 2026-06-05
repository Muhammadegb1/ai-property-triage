"""
Ollama client: thin wrapper around the Ollama HTTP API.
"""
from __future__ import annotations

import json
from collections.abc import Generator

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_API_KEY, REQUEST_TIMEOUT, TAVILY_API_KEY


class OllamaError(Exception):
    pass


_REAL_ESTATE_KEYWORDS = {
    "price", "apartment", "flat", "house", "villa", "rent", "buy", "sell",
    "market", "listing", "property", "real estate", "bedroom", "bathroom",
    "sqm", "square meter", "mortgage", "neighborhood", "location", "floor",
    "condo", "studio", "duplex", "penthouse", "balcony", "invest",
    "דירה", "בית", "נכס", "שכירות", "מחיר", "שוק", "חדר", "קומה", "שכונה",
}


def is_real_estate_question(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in _REAL_ESTATE_KEYWORDS)


def tavily_search(query: str) -> str:
    if not TAVILY_API_KEY:
        print("[Tavily] API key not set — skipping web search.")
        return ""
    try:
        print(f"[Tavily] Searching: {query!r}")
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 3,
                "include_answer": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer")
        results = data.get("results", [])
        if not results and not answer:
            print("[Tavily] No results returned.")
            return ""
        print(f"[Tavily] Got {len(results)} results, answer: {bool(answer)}")
        context = ""
        if answer:
            context += f"Web search summary: {answer}\n\n"
        parts = [
            f"Source {i+1} ({r['url']}):\n{r['content']}"
            for i, r in enumerate(results[:3])
        ]
        context += "\n\n".join(parts)
        return context
    except Exception as e:
        print(f"[Tavily] Error: {e}")
        return ""


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


def chat_stream(messages: list[dict], model: str | None = None) -> Generator[str, None, None]:
    """Yield text chunks as they stream from Ollama."""
    _model = model or OLLAMA_MODEL
    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": _model, "messages": messages, "stream": True},
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


def openai_chat_stream(messages: list[dict]) -> Generator[str, None, None]:
    """Yield text chunks as they stream from OpenAI."""
    try:
        from openai import OpenAI, OpenAIError
        client = OpenAI(api_key=OPENAI_API_KEY)
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            temperature=0.7,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        raise OllamaError(f"OpenAI request failed: {exc}") from exc
