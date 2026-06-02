"""Submit listing payloads to the n8n webhook."""

from __future__ import annotations

import httpx

from config import LOCAL_PIPELINE_URL, N8N_WEBHOOK_URL, USE_LOCAL_PIPELINE


class N8nError(Exception):
    """Raised when the n8n webhook call fails."""


def submit_listing(
    *,
    description: str,
    image_urls: list[str],
    agent_name: str,
    timeout: float = 300.0,
) -> dict:
    """POST listing data to the n8n webhook and return the JSON response."""
    payload = {
        "description": description.strip(),
        "image_urls": image_urls,
        "agent_name": agent_name.strip(),
    }

    if USE_LOCAL_PIPELINE:
        url = LOCAL_PIPELINE_URL
    elif N8N_WEBHOOK_URL.strip():
        url = N8N_WEBHOOK_URL
    else:
        raise N8nError(
            "Set N8N_WEBHOOK_URL or USE_LOCAL_PIPELINE=true in code/webui/.env"
        )

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.ConnectError as exc:
        raise N8nError("Cannot reach the n8n webhook URL.") from exc
    except httpx.HTTPStatusError as exc:
        raise N8nError(
            f"n8n webhook HTTP {exc.response.status_code}: {exc.response.text[:500]}"
        ) from exc

    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}
