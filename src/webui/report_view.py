from __future__ import annotations

import streamlit as st

_CSS = ""  # styles are defined in app.py to match the dark theme


def render_report(result: dict) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    if not result:
        st.info("Pipeline returned an empty response.")
        return

    if result.get("rejected"):
        st.error(f"🚫 Listing rejected: {result.get('reason', 'Input guardrail failed.')}")
        return

    if result.get("human_review_required"):
        st.warning(result.get("message", "Report flagged for human review (output guardrail)."))
        if report := result.get("report", {}):
            st.markdown("### Report (pending review)")
            _render_report_body(report, flag_reason=result.get("flag_reason"))
        return

    if result.get("success"):
        channel = result.get("channel", "")
        label = {"residential": "🏡 Routed to Residential Team",
                 "commercial":  "🏢 Routed to Commercial Team"}.get(channel, "✅ Complete")
        st.success(label)
        _render_report_body(result.get("report", {}))
        return

    st.markdown("### Response")
    st.json(result)


def _render_report_body(report: dict, flag_reason: str | None = None) -> None:
    st.markdown("---")
    st.subheader("Triage Report")

    if flag_reason:
        st.warning(f"Flag reason: {flag_reason}")

    # ── Metrics ──────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Type",              report.get("property_type", "—"))
    col2.metric("Location",          report.get("location", "—"))
    price = report.get("price_ils")
    col3.metric("Price (ILS)",       f"{price:,}" if price else "—")
    col4.metric("Rooms",             report.get("num_rooms", "—"))
    confidence = report.get("confidence")
    col5.metric("Report confidence", f"{int(confidence * 100)}%" if confidence else "—")

    # ── Key features as chips ─────────────────────────────────────────
    features = report.get("key_features") or []
    if features:
        chips = "".join(f'<span class="chip">{f}</span>' for f in features)
        st.markdown(f"**Key features**<br>{chips}", unsafe_allow_html=True)

    if certs := report.get("certifications"):
        st.markdown(f"🏅 **Certifications:** {certs}")

    if notes := report.get("enrichment_notes"):
        st.info(notes)

    # ── Image analysis cards ──────────────────────────────────────────
    image_scores = report.get("image_scores") or []
    if image_scores:
        st.markdown("### Image Analysis")
        cols = st.columns(min(len(image_scores), 3))
        for i, img in enumerate(image_scores):
            with cols[i % len(cols)]:
                if not isinstance(img, dict):
                    st.text(str(img))
                    continue
                room  = (img.get("room_type") or "unknown").replace("_", " ").title()
                score = img.get("condition_score")
                conf  = img.get("confidence")
                url   = img.get("url") or ""
                pct   = int(float(score) / 5 * 100) if score is not None else 0
                short = ("…" + url[-36:]) if len(url) > 40 else url
                st.markdown(f"""
                <div class="img-card">
                  <div class="img-room">{room}</div>
                  <div class="img-url" title="{url}">{short}</div>
                  <div style="background:#E2E8F0;border-radius:4px;height:6px;overflow:hidden">
                    <div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#D4A843,#F7CA60)"></div>
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-top:5px;font-size:.76rem;color:#6C7A8A">
                    <span>Score {"—" if score is None else f"{score}/5"}</span>
                    <span>{"—" if conf is None else f"{conf:.0%} conf."}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
    elif image_analysis := report.get("image_analysis"):
        st.markdown("### Image Analysis")
        st.info(image_analysis)

    # ── Similar listings as cards ─────────────────────────────────────
    similar = report.get("similar_listings") or []
    if similar:
        st.markdown("### Similar past listings")
        for item in similar:
            if isinstance(item, dict):
                title = item.get("title") or item.get("id", "Listing")
                price = item.get("price_ils") or item.get("price")
                desc  = item.get("description", "")
                loc   = item.get("location", "")
                if desc and price and isinstance(price, (int, float)) \
                        and "Asking price" not in desc and str(price) not in desc:
                    desc += f" Asking price: {price:,} ILS."
                meta = f"<span style='font-size:.78rem;color:#8A9AB0'>{loc}</span>" if loc else ""
                st.markdown(f"""
                <div class="lst-card">
                  <div class="lst-title">{title}</div>{meta}
                  {"<div class='lst-desc'>" + desc + "</div>" if desc else ""}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"- {item}")

    # ── RAG Insight ───────────────────────────────────────────────────
    if rag_insight := report.get("rag_insight"):
        st.markdown("### RAG Insight")
        st.markdown(f'<div class="rag-box">💡 {rag_insight}</div>', unsafe_allow_html=True)
