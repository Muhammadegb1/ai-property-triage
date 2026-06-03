from __future__ import annotations

import streamlit as st


def render_report(result: dict) -> None:
    if not result:
        st.info("Pipeline returned an empty response.")
        return

    # --- Input guardrail rejected the listing (Node 3b, HTTP 422) ---
    if result.get("rejected"):
        st.error(f"Listing rejected: {result.get('reason', 'Input guardrail failed.')}")
        return

    # --- Output guardrail flagged for human review (Node 7d) ---
    if result.get("human_review_required"):
        st.warning(
            result.get("message", "Report flagged for human review (output guardrail).")
        )
        report = result.get("report", {})
        if report:
            st.markdown("### Report (pending review)")
            _render_report_body(report, flag_reason=result.get("flag_reason"))
        return

    # --- Success (Node 8a residential / Node 8b commercial) ---
    if result.get("success"):
        channel = result.get("channel", "")
        if channel == "residential":
            st.success("Routed to: Residential team")
        elif channel == "commercial":
            st.success("Routed to: Commercial team")

        report = result.get("report", {})
        _render_report_body(report)
        return

    # --- Fallback: show raw response ---
    st.markdown("### Response")
    st.json(result)


def _render_report_body(report: dict, flag_reason: str | None = None) -> None:
    st.markdown("---")
    st.subheader("Triage Report")

    if flag_reason:
        st.warning(f"Flag reason: {flag_reason}")

    # Key fields
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Type", report.get("property_type", "—"))
    col2.metric("Location", report.get("location", "—"))
    price = report.get("price_ils")
    col3.metric("Price (ILS)", f"{price:,}" if price else "—")
    col4.metric("Rooms", report.get("num_rooms", "—"))
    confidence = report.get("confidence")
    col5.metric("Report confidence", f"{int(confidence * 100)}%" if confidence else "—")

    features = report.get("key_features") or []
    if features:
        st.markdown("**Key features:** " + " · ".join(features))

    certs = report.get("certifications", "")
    if certs:
        st.markdown(f"**Certifications:** {certs}")

    notes = report.get("enrichment_notes", "")
    if notes:
        st.info(notes)

    # Image condition scores (§5.2 required element)
    image_scores = report.get("image_scores") or []
    image_analysis = report.get("image_analysis", "")
    if image_scores:
        st.markdown("### Image Analysis")
        rows = []
        for img in image_scores:
            try:
                rows.append({
                    "URL": img.get("url", "—"),
                    "Room type": img.get("room_type", "—"),
                    "Condition score": img.get("condition_score", "—"),
                    "Confidence": f"{img.get('confidence', 0):.0%}" if img.get("confidence") else "—",
                })
            except AttributeError:
                rows.append({"Analysis": str(img), "Room type": "—", "Condition score": "—", "Confidence": "—"})
        st.table(rows)
    elif image_analysis:
        st.markdown("### Image Analysis")
        st.info(image_analysis)

    # Similar-listing recommendations (§5.2 required element)
    similar = report.get("similar_listings") or []
    if similar:
        st.markdown("### Similar past listings")
        for item in similar:
            if isinstance(item, dict):
                title = item.get("title") or item.get("id", "Listing")
                price = item.get("price_ils") or item.get("price")
                description = item.get("description", "")
                location = item.get("location", "")
                st.markdown(f"- **{title}** {location}".strip())
                if description:
                    # append price if not already in description
                    if price and "Asking price" not in description and str(price) not in description:
                        st.markdown(f"  {description} Asking price: {price:,} ILS.")
                    else:
                        st.markdown(f"  {description}")
            else:
                st.markdown(f"- {item}")

    rag_insight = report.get("rag_insight", "")
    if rag_insight:
        st.markdown("### RAG Insight")
        st.info(rag_insight)
