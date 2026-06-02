"""
Assistant tab: a simple chat interface to ask questions about real estate, powered by Ollama.
"""


from __future__ import annotations

import streamlit as st

from config import OLLAMA_MODEL, OLLAMA_SYSTEM_PROMPT_FILE
from ollama_client import OllamaError, chat, health_check


def _load_system_prompt() -> str:
    if OLLAMA_SYSTEM_PROMPT_FILE.is_file():
        return OLLAMA_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are a helpful real estate assistant."


def render_assistant_tab() -> None:
    st.subheader("Real estate assistant")
    st.caption(f"Powered by Ollama · model `{OLLAMA_MODEL}`")

    col_status, col_clear = st.columns([4, 1])
    with col_status:
        if health_check():
            st.success("Ollama is reachable.")
        else:
            st.warning(
                f"Ollama is not reachable. Run `ollama serve` and "
                f"`ollama pull {OLLAMA_MODEL}`, then refresh."
            )

    with col_clear:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about property types, market terms, listings…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        api_messages = [{"role": "system", "content": _load_system_prompt()}]
        api_messages.extend(st.session_state.messages)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    reply = chat(api_messages)
                except OllamaError as exc:
                    st.error(str(exc))
                    return
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
