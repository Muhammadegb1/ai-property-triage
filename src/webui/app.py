from __future__ import annotations

from config import N8N_WEBHOOK_URL, OLLAMA_BASE_URL, OLLAMA_MODEL

import streamlit as st
from assistant_tab import render_assistant_tab
from submission_tab import render_submission_tab

_CSS = """
<style>
/* ── Chat bubbles ─────────────────────────────────────────── */
.bubble-user {
    display: flex;
    justify-content: flex-end;
    margin: 6px 4px;
}
.bubble-user > div {
    background: #2563EB;
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px;
    max-width: 75%;
    font-size: .9rem;
    line-height: 1.6;
    word-wrap: break-word;
}
.bubble-bot {
    display: flex;
    justify-content: flex-start;
    margin: 6px 4px;
}
.bubble-bot > div {
    background: #374151;
    color: #F3F4F6;
    border: 1px solid #4B5563;
    border-radius: 18px 18px 18px 4px;
    padding: 10px 16px;
    max-width: 75%;
    font-size: .9rem;
    line-height: 1.6;
    word-wrap: break-word;
}

/* ── Report styles ────────────────────────────────────────── */
.chip { display:inline-block; background:#1E3A5F; color:#93C5FD;
        border:1px solid #2563EB; border-radius:20px;
        padding:3px 12px; font-size:.8rem; margin:3px; }
.img-card { background:#1F2937; border:1px solid #374151;
            border-radius:10px; padding:14px 16px; }
.img-room { font-size:.7rem; font-weight:700; color:#9CA3AF;
            text-transform:uppercase; letter-spacing:.06em; }
.img-url  { font-size:.73rem; color:#6B7280; margin:3px 0 8px;
            white-space:nowrap; overflow:hidden;
            text-overflow:ellipsis; max-width:280px; }
.lst-card { background:#1F2937; border-left:4px solid #D4A843;
            border-radius:0 8px 8px 0; padding:12px 16px;
            margin-bottom:10px; }
.lst-title { font-weight:700; color:#F9FAFB; font-size:.93rem; }
.lst-desc  { font-size:.84rem; color:#D1D5DB; margin-top:6px; line-height:1.5; }
.rag-box  { border-left:4px solid #D4A843; background:#1C1A0A;
            border-radius:0 8px 8px 0; padding:14px 18px;
            font-size:.88rem; color:#FDE68A; line-height:1.65; }
</style>
"""


def main() -> None:
    st.set_page_config(
        page_title="AI Property Triage",
        page_icon="🏠",
        layout="wide",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title("AI Property Triage")

    tab_assistant, tab_submit = st.tabs(["💬 Assistant", "📋 Submit listing"])

    with tab_assistant:
        render_assistant_tab()

    with tab_submit:
        render_submission_tab()

    with st.sidebar:
        st.header("Configuration")
        st.json({
            "ollama_base_url": OLLAMA_BASE_URL,
            "ollama_model": OLLAMA_MODEL,
            "n8n_webhook_configured": bool(N8N_WEBHOOK_URL),
        })


if __name__ == "__main__":
    main()
