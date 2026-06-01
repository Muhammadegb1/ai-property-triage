"""Format n8n pipeline responses into the triage report layout."""

from __future__ import annotations

import re
from typing import Any

import httpx

SECTION_STYLE = (
    "background:#1e3a5f;color:white;padding:8px 12px;"
    "font-weight:600;margin:16px 0 8px 0;border-radius:4px;"
)
BANNER_STYLE = (
    "background:#1e3a5f;color:white;padding:16px;border-radius:6px;margin:12px 0;"
)


def _first_sentence(text: str, max_len: int = 220) -> str:
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    cut = t[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def _parse_description(description: str) -> dict[str, Any]:
    lower = description.lower()
    rooms = None
    m = re.search(r"(\d+)\s*[- ]?\s*(?:bed(?:room)?s?|br|room)", lower)
    if m:
        rooms = int(m.group(1))
    price = None
    pm = re.search(r"([\d,]+)\s*(?:ils|nis|₪|usd|\$)?", description, re.I)
    if pm:
        try:
            price = int(pm.group(1).replace(",", ""))
        except ValueError:
            price = None
    ptype = "Apartment"
    if "villa" in lower:
        ptype = "Villa"
    elif "house" in lower:
        ptype = "House"
    elif "office" in lower:
        ptype = "Office"
    location = None
    for pat in (
        r"(?:in|at)\s+([A-Za-z\u0590-\u05FF][A-Za-z\u0590-\u05FF\s,'-]{2,50})",
        r"([A-Za-z\u0590-\u05FF][A-Za-z\u0590-\u05FF\s,'-]{2,40}),\s*([A-Za-z\u0590-\u05FF\s'-]{2,30})",
    ):
        lm = re.search(pat, description, re.I)
        if lm:
            location = ", ".join(g.strip() for g in lm.groups() if g).strip(" ,")
            if len(location) > 3:
                break
    features: list[str] = []
    for kw in (
        "renovated",
        "parking",
        "balcony",
        "elevator",
        "furnished",
        "sea view",
        "sqm",
        "m²",
        "bathroom",
        "kitchen",
    ):
        if kw in lower and kw not in " ".join(features).lower():
            m2 = re.search(rf"(\d+\s*(?:sqm|m²|sq\s*m))", lower) if kw == "sqm" else None
            features.append(m2.group(1) if m2 else kw.replace("sqm", "size noted in listing"))
    if not features:
        features = [s.strip() for s in re.split(r"[.\n]", description) if 5 < len(s.strip()) < 80][:4]
    return {
        "property_type": ptype,
        "location": location,
        "price_ils": price,
        "num_rooms": rooms,
        "key_features": features[:6],
    }


def fetch_image_scores(urls: list[str]) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for url in urls:
        try:
            with httpx.Client(timeout=12.0) as client:
                r = client.post(
                    "http://127.0.0.1:8003/analyse",
                    json={"image_url": url},
                )
                r.raise_for_status()
                data = r.json()
            scores.append(
                {
                    "url": url,
                    "room_type": data.get("room_type", "other"),
                    "condition_score": data.get("condition_score", 3),
                    "confidence": data.get("confidence", 0.8),
                }
            )
        except Exception:
            scores.append(
                {
                    "url": url,
                    "room_type": "other",
                    "condition_score": 3,
                    "confidence": 0.5,
                }
            )
    return scores


def _format_price(price: Any) -> str:
    if price is None:
        return "—"
    try:
        n = int(price)
        return f"₪{n:,}"
    except (TypeError, ValueError):
        return str(price)


def _stars(score: float) -> str:
    full = int(score)
    half = 1 if score - full >= 0.25 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty + f"  ({score:.1f}/5)"


def _format_similar(item: Any) -> str:
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item)
    title = item.get("title") or item.get("id") or "Listing"
    rooms = item.get("rooms")
    price = item.get("price")
    sqm = item.get("sqm")
    desc = item.get("description") or title
    parts = [desc if len(str(desc)) > 40 else f"Comparable: {title}"]
    if rooms:
        parts.append(f"{rooms} bedrooms")
    if sqm:
        parts.append(f"{sqm} sqm")
    if price:
        parts.append(f"Asking price: {int(price):,} ILS")
    return ". ".join(parts) + "."


def normalize_result(
    result: dict,
    *,
    description: str = "",
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Map n8n workflow payloads to one report model."""
    parsed = _parse_description(description) if description else {}
    image_urls = image_urls or []

    if result.get("success") and isinstance(result.get("report"), dict):
        report = dict(result["report"])
        channel = result.get("channel") or report.get("routing_decision") or "residential"
    elif result.get("status") == "ok":
        report = {
            "property_type": (result.get("extracted_fields") or {}).get("property_type"),
            "location": (result.get("extracted_fields") or {}).get("location"),
            "price_ils": None,
            "num_rooms": (result.get("extracted_fields") or {}).get("rooms"),
            "key_features": (result.get("extracted_fields") or {}).get("key_features") or [],
            "image_scores": result.get("image_analysis") or [],
            "similar_listings": result.get("similar_listings") or [],
            "rag_insight": "",
            "enrichment_notes": result.get("listing_brief") or "",
            "routing_decision": result.get("routing") or "residential",
            "confidence": 0.9,
        }
        price_raw = (result.get("extracted_fields") or {}).get("price")
        if price_raw:
            pm = re.search(r"([\d,]+)", str(price_raw))
            if pm:
                try:
                    report["price_ils"] = int(pm.group(1).replace(",", ""))
                except ValueError:
                    pass
        channel = report.get("routing_decision") or "residential"
        rag = result.get("rag_insight")
        if not rag and isinstance(result.get("similar_listings"), list):
            pass
    else:
        report = dict(result.get("report") or result)
        channel = report.get("routing_decision") or result.get("routing") or "residential"

    loc = report.get("location") or parsed.get("location")
    if not loc or str(loc).lower() in ("see listing", "unknown", "not provided", ""):
        loc = parsed.get("location") or "—"

    ptype = report.get("property_type") or parsed.get("property_type") or "Property"
    if isinstance(ptype, str):
        ptype = ptype.strip().capitalize()

    rooms = report.get("num_rooms")
    if rooms is None:
        rooms = parsed.get("num_rooms")

    price = report.get("price_ils")
    if price is None:
        price = parsed.get("price_ils")

    features = report.get("key_features") or parsed.get("key_features") or []
    if isinstance(features, str):
        features = [features]

    scores = report.get("image_scores") or report.get("image_analysis") or []
    if not scores and image_urls:
        scores = fetch_image_scores(image_urls)

    conf = report.get("confidence")
    if conf is None:
        conf = 0.85
    try:
        conf_f = float(conf)
        confidence_pct = int(conf_f * 100) if conf_f <= 1 else int(conf_f)
    except (TypeError, ValueError):
        confidence_pct = 85

    similar = report.get("similar_listings") or []
    similar_text = [_format_similar(s) for s in similar]

    market = (report.get("rag_insight") or "").strip()
    notes = (report.get("enrichment_notes") or "").strip()
    if market.lower().startswith("mock langgraph"):
        market = ""
    brief = result.get("listing_brief")
    if isinstance(brief, str) and "market insight" in brief.lower():
        m = re.search(r"## Market insight\s*\n+([\s\S]*?)(?=\n## |\Z)", brief, re.I)
        if m and not market:
            market = m.group(1).strip()

    routing = str(channel or report.get("routing_decision") or "residential").capitalize()
    passed = not result.get("rejected") and result.get("status") != "review"
    title = f"{routing} - {'Passed' if passed else 'Review'}"

    summary = _first_sentence(description) if description else _first_sentence(
        f"{rooms or '—'}-bedroom {ptype} in {loc}. "
        f"{', '.join(features[:3]) if features else ''} "
        f"Asking {_format_price(price)}."
    )

    return {
        "title": title,
        "summary": summary,
        "property_type": ptype,
        "routing_label": f"{ptype} · {routing}",
        "location": loc,
        "price_display": _format_price(price),
        "rooms": rooms if rooms is not None else "—",
        "confidence_pct": confidence_pct,
        "key_features": features,
        "image_scores": scores,
        "similar_listings": similar_text,
        "market_insight": market,
        "analyst_notes": notes,
        "agent_name": result.get("agent_name"),
    }


def render_triage_report(
    result: dict,
    *,
    description: str = "",
    image_urls: list[str] | None = None,
    agent_name: str = "",
) -> None:
    import streamlit as st

    if agent_name:
        result = {**result, "agent_name": agent_name}
    view = normalize_result(result, description=description, image_urls=image_urls)

    st.markdown(f"## {view['title']}")
    st.markdown(view["summary"])
    st.markdown("✅ **Report received.**")

    st.markdown(
        f'<div style="{BANNER_STYLE}">'
        f'<div style="font-size:1.25em;font-weight:700;">🏠 {view["routing_label"]}</div>'
        f'<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:20px;">'
        f'<span><b>Location</b><br>{view["location"]}</span>'
        f'<span><b>Price</b><br>{view["price_display"]}</span>'
        f'<span><b>Rooms</b><br>{view["rooms"]}</span>'
        f'<span><b>Report confidence</b><br>{view["confidence_pct"]}%</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )

    if view["key_features"]:
        st.markdown(f'<div style="{SECTION_STYLE}">Key features:</div>', unsafe_allow_html=True)
        for feat in view["key_features"]:
            st.markdown(f"- {feat}")

    if view["image_scores"]:
        st.markdown(f'<div style="{SECTION_STYLE}">Image analysis:</div>', unsafe_allow_html=True)
        for img in view["image_scores"]:
            if not isinstance(img, dict):
                continue
            room = str(img.get("room_type", "other")).title()
            try:
                score = float(img.get("condition_score", 3))
            except (TypeError, ValueError):
                score = 3.0
            st.markdown(f"**{room}:** {_stars(score)}")

    if view["similar_listings"]:
        st.markdown(
            f'<div style="{SECTION_STYLE}">Similar past listings:</div>',
            unsafe_allow_html=True,
        )
        for line in view["similar_listings"]:
            st.markdown(f"- {line}")

    if view["market_insight"]:
        st.markdown(f'<div style="{SECTION_STYLE}">Market insight:</div>', unsafe_allow_html=True)
        st.markdown(view["market_insight"])

    if view["analyst_notes"]:
        st.markdown(f'<div style="{SECTION_STYLE}">Analyst notes:</div>', unsafe_allow_html=True)
        st.markdown(view["analyst_notes"])

    with st.expander("Raw pipeline JSON"):
        st.json(result)
