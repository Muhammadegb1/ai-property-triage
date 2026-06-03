from __future__ import annotations

import streamlit as st

from config import OLLAMA_MODEL, OLLAMA_SYSTEM_PROMPT_FILE
from ollama_client import OllamaError, chat_stream, health_check


def _load_system_prompt() -> str:
    if OLLAMA_SYSTEM_PROMPT_FILE.is_file():
        return OLLAMA_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are a helpful real estate assistant."


def _user_bubble(text: str) -> str:
    return "<div class='bubble-user'><div>" + text + "</div></div>"


def _bot_bubble(text: str) -> str:
    return "<div class='bubble-bot'><div>" + text + "</div></div>"


def render_assistant_tab() -> None:
    # ── Header ────────────────────────────────────────────────────────
    col_info, col_btn = st.columns([5, 1])
    with col_info:
        online = health_check()
        st.markdown(
            f"**Real Estate Assistant** &nbsp; {'🟢 Online' if online else '🔴 Offline'}"
        )
        st.caption(f"Ollama · `{OLLAMA_MODEL}`")
    with col_btn:
        st.write("")
        if st.button("Clear", use_container_width=True):
            st.session_state.messages    = []
            st.session_state.pending_msg = None
            st.rerun()

    if "messages"    not in st.session_state: st.session_state.messages    = []
    if "pending_msg" not in st.session_state: st.session_state.pending_msg = None

    # ── Chat box ──────────────────────────────────────────────────────
    with st.container(height=450, border=True):

        # Empty state
        if not st.session_state.messages and not st.session_state.pending_msg:
            st.markdown(
                "<div style='text-align:center;padding:120px 0;"
                "color:#6B7280;font-size:.95rem'>"
                "💬 Ask me anything about real estate</div>",
                unsafe_allow_html=True,
            )

        # Render history
        for msg in st.session_state.messages:
            fn = _user_bubble if msg["role"] == "user" else _bot_bubble
            st.markdown(fn(msg["content"]), unsafe_allow_html=True)

        # Phase 2 — pending message: draw + stream
        if st.session_state.pending_msg:
            pending = st.session_state.pending_msg

            st.markdown(_user_bubble(pending), unsafe_allow_html=True)

            reply_slot = st.empty()
            reply_slot.markdown(
                _bot_bubble("⏳ &nbsp;<em>Typing…</em>"),
                unsafe_allow_html=True,
            )

            api_messages = [{"role": "system", "content": _load_system_prompt()}]
            api_messages += [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            api_messages.append({"role": "user", "content": pending})

            full_reply = ""
            try:
                for chunk in chat_stream(api_messages):
                    full_reply += chunk
                    reply_slot.markdown(
                        _bot_bubble(full_reply + " ▌"),
                        unsafe_allow_html=True,
                    )
            except OllamaError as exc:
                st.error(str(exc))
                st.session_state.pending_msg = None
                return

            # Final bubble — remove cursor
            reply_slot.markdown(_bot_bubble(full_reply), unsafe_allow_html=True)

            st.session_state.messages.append({"role": "user",      "content": pending})
            st.session_state.messages.append({"role": "assistant",  "content": full_reply})
            st.session_state.pending_msg = None
            st.rerun()

    # ── Input form (below chat box) ───────────────────────────────────
    waiting = bool(st.session_state.pending_msg)
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Ask about property types, market terms, listings…",
            height=90,
            label_visibility="collapsed",
            disabled=waiting,
        )
        c1, c2 = st.columns(2)
        send  = c1.form_submit_button(
            "Send ➤", type="primary", use_container_width=True, disabled=waiting
        )
        clear = c2.form_submit_button("Clear chat", use_container_width=True)

    if clear:
        st.session_state.messages    = []
        st.session_state.pending_msg = None
        st.rerun()

    # Phase 1 — store message and trigger Phase 2
    if send and user_input.strip():
        st.session_state.pending_msg = user_input.strip()
        st.rerun()
