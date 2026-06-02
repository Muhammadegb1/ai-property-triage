from __future__ import annotations

import streamlit as st


def render_report(result: dict) -> None:
    if not result:
        st.info("Pipeline returned an empty response.")
        return

    # --- Input guardrail rejected the listing ---
    if result.get("status") == "rejected" or result.get("rejected"):
        st.error(
            f"Listing rejected: {result.get('reason', 'Input guardrail failed.')}"
        )
        return

    # --- Output guardrail flagged for human review ---
    if result.get("status") == "review" or result.get("human_review_required"):
        st.warning(
            result.get("message", "Report flagged for human review (output guardrail).")
        )

    # --- Extract the report object (n8n may nest it or return it flat) ---
    report = result.get("report") or result

    st.markdown("---")
    st.subheader("Triage Report")

    # Routing team
    team = result.get("team") or report.get("team")
    if team:
        label = "🏠 Residential" if team == "residential" else "🏢 Commercial"
        st.markdown(f"**Routed to:** {label}")

    # Key extracted fields
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Type", report.get("property_type", "—"))
    col2.metric("Location", report.get("location", "—"))
    col3.metric("Price", f"{report.get('price', '—'):,}" if report.get("price") else "—")
    col4.metric("Rooms", report.get("num_rooms", "—"))

    features = report.get("key_features") or []
    if features:
        st.markdown("**Key features:** " + " · ".join(features))

    certs = report.get("certifications") or []
    if certs:
        st.markdown("**Certifications:** " + " · ".join(certs))

    # Listing brief
    brief = report.get("brief_markdown") or report.get("brief") or report.get("listing_brief")
    if brief:
        st.markdown("### Listing Brief")
        st.markdown(brief)

    # Image condition scores (§5.2 required element)
    images = report.get("image_analysis") or []
    if images:
        st.markdown("### Image Analysis")
        rows = []
        for img in images:
            rows.append({
                "URL": img.get("image_url", ""),
                "Room type": img.get("room_type", "—"),
                "Condition score": img.get("condition_score", "—"),
                "Confidence": f"{img.get('confidence', 0):.0%}" if img.get("confidence") else "—",
            })
        st.table(rows)

    # Similar-listing recommendations (§5.2 required element)
    similar = report.get("similar_listings") or []
    if similar:
        st.markdown("### Similar Listings")
        for listing in similar:
            title = listing.get("title") or listing.get("id") or "Listing"
            price = listing.get("price")
            price_str = f" — {price:,}" if price else ""
            location = listing.get("location", "")
            st.markdown(f"- **{title}** ({listing.get('property_type', '')}){price_str} {location}")

    insight = report.get("insight")
    if insight:
        st.markdown("### RAG Insight")
        st.info(insight)

    # Fallback: show raw response if none of the known fields matched
    known_keys = {
        "status", "team", "report", "property_type", "location", "price",
        "num_rooms", "key_features", "certifications", "brief_markdown",
        "brief", "listing_brief", "image_analysis", "similar_listings", "insight",
    }
    if not any(k in report for k in known_keys):
        st.markdown("### Full response")
        st.json(result)
