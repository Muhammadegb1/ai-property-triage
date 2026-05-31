import logging
import os

import httpx

logger = logging.getLogger(__name__)

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
IMAGE_ANALYSER_URL = os.getenv("IMAGE_ANALYSER_URL", "http://localhost:8002")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))

TOOL_DESCRIPTIONS = {
    "query_similar_listings": (
        "Retrieve the 3 most similar past property listings from the agency archive "
        "and return a short comparative insight. "
        "Use when the query asks about comparable properties, similar past listings, "
        "or comparisons based on a property description in text. "
        "Input: a property description string."
    ),
    "analyse_property_image": (
        "Classify a property image by room type (kitchen, bathroom, bedroom, "
        "living room, exterior, other) and assign a condition score from 1 to 5. "
        "Use ONLY when the query contains a direct image URL starting with http:// or https://. "
        "Input: a URL string."
    ),
}


async def query_similar_listings(description: str) -> dict:
    logger.info("Calling RAG service: description=%r", description[:80])
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                f"{RAG_SERVICE_URL}/query",
                json={"description": description},
            )
            r.raise_for_status()
            result = r.json()
            logger.info("RAG service returned %d listings", len(result.get("similar_listings", [])))
            return result
    except httpx.TimeoutException:
        logger.warning("RAG service timed out")
        return {"error": "RAG service timed out", "similar_listings": [], "insight": ""}
    except httpx.HTTPStatusError as e:
        logger.error("RAG service HTTP error: %s", e.response.status_code)
        return {"error": f"RAG service returned {e.response.status_code}", "similar_listings": [], "insight": ""}
    except httpx.ConnectError:
        logger.error("RAG service unreachable at %s", RAG_SERVICE_URL)
        return {"error": "RAG service unreachable", "similar_listings": [], "insight": ""}


async def analyse_property_image(image_url: str) -> dict:
    logger.info("Calling Image Analyser: url=%r", image_url)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                f"{IMAGE_ANALYSER_URL}/analyse",
                json={"image_url": image_url},
            )
            r.raise_for_status()
            result = r.json()
            logger.info("Image Analyser: room=%s score=%s", result.get("room_type"), result.get("condition_score"))
            return result
    except httpx.TimeoutException:
        logger.warning("Image Analyser timed out")
        return {"error": "Image Analyser timed out", "room_type": "uncertain", "condition_score": None, "confidence": 0.0}
    except httpx.HTTPStatusError as e:
        logger.error("Image Analyser HTTP error: %s", e.response.status_code)
        return {"error": f"Image Analyser returned {e.response.status_code}", "room_type": "uncertain", "condition_score": None, "confidence": 0.0}
    except httpx.ConnectError:
        logger.error("Image Analyser unreachable at %s", IMAGE_ANALYSER_URL)
        return {"error": "Image Analyser unreachable", "room_type": "uncertain", "condition_score": None, "confidence": 0.0}
