from __future__ import annotations

import streamlit as st

from config import OLLAMA_SYSTEM_PROMPT_FILE
from ollama_client import (
    OllamaError,
    chat_stream,
    health_check,
    is_real_estate_question,
    openai_chat_stream,
    tavily_search,
)

# ── Model registry ────────────────────────────────────────────────────────────
MODEL_OPTIONS: dict[str, dict] = {
    "🦙 Llama 3.1":   {"backend": "ollama", "model": "llama3.1:latest",  "label": "Local · Ollama"},
    "🦙 Llama 3.2":   {"backend": "ollama", "model": "llama3.2:latest",  "label": "Local · Ollama"},
    "✨ GPT-4o mini": {"backend": "openai", "model": "gpt-4o-mini",      "label": "OpenAI API"},
}
DEFAULT_MODEL = "🦙 Llama 3.1"

# URL-safe keys for persisting selection across page refreshes
_MODEL_TO_KEY = {
    "🦙 Llama 3.1":   "llama31",
    "🦙 Llama 3.2":   "llama32",
    "✨ GPT-4o mini": "gpt4omini",
}
_KEY_TO_MODEL = {v: k for k, v in _MODEL_TO_KEY.items()}


def _load_system_prompt() -> str:
    if OLLAMA_SYSTEM_PROMPT_FILE.is_file():
        return OLLAMA_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are a helpful real estate assistant."


def _user_bubble(text: str) -> str:
    return "<div class='bubble-user'><div>" + text + "</div></div>"


def _bot_bubble(text: str) -> str:
    return "<div class='bubble-bot'><div>" + text + "</div></div>"


def _stream_response(messages: list[dict], backend: str, model: str):
    """Route to correct streaming backend."""
    if backend == "openai":
        return openai_chat_stream(messages)
    return chat_stream(messages, model=model)


def render_assistant_tab() -> None:
    # ── Session state init (restore from URL on refresh) ─────────────
    if "messages"    not in st.session_state: st.session_state.messages    = []
    if "pending_msg" not in st.session_state: st.session_state.pending_msg = None
    if "selected_model" not in st.session_state:
        url_key = st.query_params.get("model", "llama31")
        st.session_state.selected_model = _KEY_TO_MODEL.get(url_key, DEFAULT_MODEL)

    # ── Header row ────────────────────────────────────────────────────
    col_info, col_btn = st.columns([5, 1])
    with col_info:
        if st.session_state.selected_model == "✨ GPT-4o mini":
            status = "🟢 Online"
        else:
            status = "🟢 Online" if health_check() else "🔴 Offline"
        st.markdown(f"**Real Estate Assistant** &nbsp; {status}")
    with col_btn:
        st.write("")
        if st.button("Clear", use_container_width=True):
            st.session_state.messages    = []
            st.session_state.pending_msg = None
            st.rerun()

    # ── Model selector ────────────────────────────────────────────────
    st.markdown(
        "<p style='margin:4px 0 2px;font-size:0.78rem;color:#6B7280;font-weight:500;"
        "letter-spacing:.03em;text-transform:uppercase;'>Model</p>",
        unsafe_allow_html=True,
    )
    previous_model = st.session_state.selected_model
    selected = st.radio(
        label="model_selector",
        options=list(MODEL_OPTIONS.keys()),
        index=list(MODEL_OPTIONS.keys()).index(st.session_state.selected_model),
        horizontal=True,
        label_visibility="collapsed",
    )

    # Clear chat and persist selection in URL when model changes
    if selected != previous_model:
        st.session_state.selected_model = selected
        st.session_state.messages       = []
        st.session_state.pending_msg    = None
        st.query_params["model"] = _MODEL_TO_KEY[selected]
        st.rerun()

    cfg = MODEL_OPTIONS[selected]
    st.caption(f"`{cfg['model']}` &nbsp;·&nbsp; {cfg['label']}")

    st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)

    # ── Chat box ──────────────────────────────────────────────────────
    with st.container(height=420, border=True):

        if not st.session_state.messages and not st.session_state.pending_msg:
            st.markdown(
                "<div style='text-align:center;padding:110px 0;"
                "color:#6B7280;font-size:.95rem'>"
                "💬 Ask me anything about real estate</div>",
                unsafe_allow_html=True,
            )

        for msg in st.session_state.messages:
            fn = _user_bubble if msg["role"] == "user" else _bot_bubble
            st.markdown(fn(msg["content"]), unsafe_allow_html=True)

        if st.session_state.pending_msg:
            pending = st.session_state.pending_msg

            st.markdown(_user_bubble(pending), unsafe_allow_html=True)

            reply_slot = st.empty()
            reply_slot.markdown(
                _bot_bubble("⏳ &nbsp;<em>Typing…</em>"),
                unsafe_allow_html=True,
            )

            system_prompt = _load_system_prompt()
            if is_real_estate_question(pending):
                reply_slot.markdown(
                    _bot_bubble("🔍 &nbsp;<em>Searching web for latest data…</em>"),
                    unsafe_allow_html=True,
                )
                web_context = tavily_search(pending)
                if web_context:
                    system_prompt += (
                        f"\n\nCurrent web search results for the user's question:\n\n"
                        f"{web_context}\n\n"
                        f"Use the above results to provide accurate, up-to-date information."
                    )

            api_messages = [{"role": "system", "content": system_prompt}]
            api_messages += [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            api_messages.append({"role": "user", "content": pending})

            full_reply = ""
            try:
                for chunk in _stream_response(api_messages, cfg["backend"], cfg["model"]):
                    full_reply += chunk
                    reply_slot.markdown(
                        _bot_bubble(full_reply + " ▌"),
                        unsafe_allow_html=True,
                    )
            except OllamaError as exc:
                st.error(str(exc))
                st.session_state.pending_msg = None
                return

            reply_slot.markdown(_bot_bubble(full_reply), unsafe_allow_html=True)

            st.session_state.messages.append({"role": "user",     "content": pending})
            st.session_state.messages.append({"role": "assistant", "content": full_reply})
            st.session_state.pending_msg = None
            st.rerun()

    # ── Input form ────────────────────────────────────────────────────
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

    if send and user_input.strip():
        st.session_state.pending_msg = user_input.strip()
        st.rerun()
