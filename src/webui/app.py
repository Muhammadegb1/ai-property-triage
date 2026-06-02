"""
AI Property Triage — Streamlit WebUI (Layer 1).

Run: streamlit run app.py
"""

from __future__ import annotations

import json
import re

import streamlit as st

from config import (
    LOCAL_PIPELINE_URL,
    N8N_WEBHOOK_URL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_SYSTEM_PROMPT_FILE,
    SAMPLES_DIR,
    USE_LOCAL_PIPELINE,
)
from n8n_client import N8nError, submit_listing
from ollama_client import OllamaError, chat, health_check
from report_view import render_triage_report


def load_system_prompt() -> str:
    if OLLAMA_SYSTEM_PROMPT_FILE.is_file():
        return OLLAMA_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are a helpful real estate assistant."


def parse_image_urls(raw: str) -> list[str]:
    parts = re.split(r"[\n,]+", raw)
    return [p.strip() for p in parts if p.strip()]


def load_samples() -> list[dict]:
    path = SAMPLES_DIR / "listings.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def render_assistant_tab() -> None:
    st.subheader("Real estate assistant")
    st.caption(f"Powered by Ollama · `{OLLAMA_MODEL}` @ {OLLAMA_BASE_URL}")

    col_status, col_clear = st.columns([3, 1])
    with col_status:
        if health_check():
            st.success("Ollama is reachable.")
        else:
            st.warning(
                f"Ollama is not reachable or model `{OLLAMA_MODEL}` is missing. "
                f"Run `ollama pull {OLLAMA_MODEL}` (keep `ollama serve` running)."
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

    if prompt := st.chat_input("Ask about listings, property types, or market terms…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        api_messages = [{"role": "system", "content": load_system_prompt()}]
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


def render_report(
    result: dict,
    *,
    description: str = "",
    image_urls: list[str] | None = None,
    agent_name: str = "",
) -> None:
    """Display n8n response — supports common shapes from the pipeline."""
    if not result:
        st.info("Pipeline returned an empty response.")
        return

    if result.get("status") == "rejected" or result.get("rejected"):
        st.error(
            f"Listing rejected: {result.get('reason', 'Input guardrail failed.')}"
        )
        return

    if result.get("human_review_required"):
        st.warning(result.get("message", "Flagged for human review."))
        report = result.get("report")
        if report:
            st.markdown("### Report (pending review)")
            st.json(report)
        return

    if result.get("status") == "review":
        st.warning(
            result.get(
                "message",
                "Report flagged for human review (output guardrail).",
            )
        )

    if (
        result.get("success")
        or result.get("status") == "ok"
        or result.get("listing_brief")
        or result.get("report")
    ):
        render_triage_report(
            result,
            description=description,
            image_urls=image_urls,
            agent_name=agent_name,
        )
        return

    st.markdown("### Full response")
    st.json(result)


def render_submission_tab() -> None:
    st.subheader("Submit a property listing")
    if USE_LOCAL_PIPELINE:
        st.info(f"Mode: **local pipeline** → `{LOCAL_PIPELINE_URL}`")
    elif N8N_WEBHOOK_URL:
        path = N8N_WEBHOOK_URL.rstrip("/").split("/")[-1]
        mode = "n8n (property-triage)" if path == "property-triage" else "n8n (other webhook)"
        st.info(f"Mode: **n8n** — {mode}")
        st.text_input("Webhook URL", value=N8N_WEBHOOK_URL, disabled=True)
    else:
        st.error("Configure `.env`: set `USE_LOCAL_PIPELINE=true` or `N8N_WEBHOOK_URL`.")

    samples = load_samples()
    if samples:
        labels = [s["label"] for s in samples]
        pick = st.selectbox("Load demo listing", ["—"] + labels)
        chosen = next((s for s in samples if s["label"] == pick), None)
    else:
        chosen = None

    with st.form("listing_form", clear_on_submit=False):
        agent_name = st.text_input(
            "Listing agent name",
            value=chosen["agent_name"] if chosen else "",
            placeholder="Jane Cohen",
        )
        description = st.text_area(
            "Property description",
            height=200,
            value=chosen["description"] if chosen else "",
            placeholder="3-bedroom apartment in Tel Aviv, 95 sqm, renovated kitchen…",
        )
        image_urls_raw = st.text_area(
            "Image URLs (comma- or newline-separated)",
            height=80,
            value=chosen.get("image_urls", "") if chosen else "",
            placeholder="https://example.com/kitchen.jpg, https://example.com/living.jpg",
            help="Image service classifies by URL keywords in dev mock (kitchen, bath, bed, …).",
        )
        submitted = st.form_submit_button("Submit listing", type="primary")

    if submitted:
        if not description.strip():
            st.warning("Please enter a property description.")
            return
        if not agent_name.strip():
            st.warning("Please enter the agent name.")
            return

        urls = parse_image_urls(image_urls_raw)
        wait = (
            "Processing via n8n production flow (Gemini — may take 1–3 minutes)…"
            if "property-triage" in (N8N_WEBHOOK_URL or "")
            else "Processing via Layer 2 pipeline (may take 30–90 seconds)…"
        )
        with st.spinner(wait):
            try:
                result = submit_listing(
                    description=description,
                    image_urls=urls,
                    agent_name=agent_name,
                )
            except N8nError as exc:
                st.error(str(exc))
                return

        st.success("Pipeline finished.")
        render_report(
            result,
            description=description,
            image_urls=urls,
            agent_name=agent_name,
        )


def main() -> None:
    st.set_page_config(
        page_title="AI Property Triage",
        page_icon="🏠",
        layout="wide",
    )
    st.title("AI Property Triage")
    st.markdown(
        "Layer 1 — **Ollama** assistant (§5.1) and **listing submission** to n8n webhook (§5.2)."
    )

    tab_chat, tab_submit = st.tabs(["Assistant", "Submit listing"])

    with tab_chat:
        render_assistant_tab()

    with tab_submit:
        render_submission_tab()

    with st.sidebar:
        st.header("Configuration")
        st.code(
            json.dumps(
                {
                    "ollama_base_url": OLLAMA_BASE_URL,
                    "ollama_model": OLLAMA_MODEL,
                    "use_local_pipeline": USE_LOCAL_PIPELINE,
                    "local_pipeline_url": LOCAL_PIPELINE_URL,
                    "n8n_webhook_configured": bool(N8N_WEBHOOK_URL),
                },
                indent=2,
            ),
            language="json",
        )
        st.markdown("**Local demo (pipeline)**")
        st.markdown(
            "1. `verify-setup.ps1` — all green\n"
            "2. Submit tab → demo sample\n"
            "3. Success / spam / FAIL_OUTPUT"
        )
        st.markdown("**Next steps**")
        st.markdown(
            "- Run `test-ollama-prompt.ps1` for Surface 5 log\n"
            "- n8n: [SETUP.md](../n8n/SETUP.md)\n"
            "- Docs: [prompt log](../../docs/prompt-engineering-log.md)"
        )


if __name__ == "__main__":
    main()
