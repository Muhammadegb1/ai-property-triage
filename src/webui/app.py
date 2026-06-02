from __future__ import annotations

from config import N8N_WEBHOOK_URL, OLLAMA_BASE_URL, OLLAMA_MODEL

import streamlit as st
from assistant_tab import render_assistant_tab
from submission_tab import render_submission_tab

def main() -> None:
    st.set_page_config(
        page_title="AI Property Triage",
        page_icon="🏠",
        layout="wide",
    )
    st.title("AI Property Triage")

    tab_assistant, tab_submit = st.tabs(["Assistant", "Submit listing"])

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
