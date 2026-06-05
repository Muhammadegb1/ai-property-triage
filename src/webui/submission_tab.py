from __future__ import annotations

import re

import streamlit as st

from config import N8N_WEBHOOK_URL
from n8n_client import N8nError, submit_listing
from report_view import render_report


def _parse_image_urls(raw: str) -> list[str]:
    parts = re.split(r"[\n,]+", raw)
    return [p.strip() for p in parts if p.strip()]


def render_submission_tab() -> None:
    st.subheader("Submit a property listing")

    if not N8N_WEBHOOK_URL:
        st.error("N8N_WEBHOOK_URL is not configured. Add it to your .env file.")

    with st.form("listing_form"):
        agent_name = st.text_input(
            "Listing agent name",
            placeholder="e.g. Jane Cohen",
        )
        description = st.text_area(
            "Property description",
            height=200,
            placeholder="3-bedroom apartment in Tel Aviv, 95 sqm, renovated kitchen…",
        )

        st.markdown("**Property images**")
        url_input = st.text_area(
            "Image URLs (comma- or newline-separated)",
            height=80,
            placeholder="https://example.com/kitchen.jpg, https://example.com/living.jpg",
        )
        uploaded_files = st.file_uploader(
            "Or upload images",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png", "webp"],
        )

        submitted = st.form_submit_button("Submit listing", type="primary")

    if submitted:
        if not description.strip():
            st.warning("Please enter a property description.")
            return
        if not agent_name.strip():
            st.warning("Please enter the listing agent name.")
            return

        image_urls = _parse_image_urls(url_input)

        if uploaded_files:
            st.info(
                f"{len(uploaded_files)} file(s) uploaded. "
                "Note: uploaded files require a publicly accessible URL for the pipeline. "
                "Use image URLs for full processing."
            )

        with st.spinner("Submitting to pipeline… this may take 1–2 minutes."):
            try:
                result = submit_listing(
                    description=description.strip(),
                    image_urls=image_urls,
                    agent_name=agent_name.strip(),
                )
            except N8nError as exc:
                st.error(str(exc))
                return

        st.success("Pipeline finished.")
        render_report(result)
