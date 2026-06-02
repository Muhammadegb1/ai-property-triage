from __future__ import annotations

import requests

from config import N8N_WEBHOOK_URL, REQUEST_TIMEOUT


class N8nError(Exception):
    pass


def submit_listing(
    description: str,
    image_urls: list[str],
    agent_name: str,
) -> dict:
    if not N8N_WEBHOOK_URL:
        raise N8nError(
            "N8N_WEBHOOK_URL is not set. Add it to your .env file."
        )

    payload = {
        "description": description,
        "image_urls": image_urls,
        "agent_name": agent_name,
    }

    try:
        resp = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        raise N8nError(
            "n8n did not respond in time. The pipeline may still be running — try again."
        )
    except requests.exceptions.ConnectionError:
        raise N8nError(
            f"Cannot reach n8n at {N8N_WEBHOOK_URL}. Check that n8n is running."
        )
    except requests.exceptions.HTTPError as exc:
        raise N8nError(
            f"n8n returned an error: {exc.response.status_code} — {exc.response.text[:300]}"
        ) from exc
    except ValueError as exc:
        raise N8nError(f"n8n response is not valid JSON: {exc}") from exc
