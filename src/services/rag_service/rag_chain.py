import logging
import threading

import huggingface_hub

from langchain_core.prompts import PromptTemplate
from langchain_community.llms import LlamaCpp
import re


logger = logging.getLogger(__name__)


_llm = None
_llm_lock = threading.Lock()


def get_llm() -> LlamaCpp:
    global _llm
    if _llm is None:
        logger.info("Loading Llama model...")
        model_path = huggingface_hub.hf_hub_download(
            repo_id="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
            filename="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        )
        _llm = LlamaCpp(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            temperature=0.2,
            max_tokens=200,
            verbose=False,
            stop=["Note:", "Best regards", "Here is", "I hope", "Lastly", "Finally", "\n\n\n", "\n\n"],
        )
        logger.info("Llama model loaded.")
    return _llm


PROMPT_VERSION = "v5"

RAG_PROMPT = PromptTemplate(
    input_variables=["query", "listings"],
    template="""You are a senior real estate analyst. 
A new property listing has been submitted, and 3 similar listings were retrieved from the agency archive.

Task: Compare the new listing to the retrieved listings using only the facts shown below.

Rules:
- Write 3–5 sentences.
- You MUST cite at least 2 different listing IDs. Even if a second listing is less comparable, cite it and briefly state how it differs.
- Always use the [LST-XXX] bracket format — never refer to a listing by its title alone.
- Compare specific facts: size, price, location, or features.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- If the new listing query does not mention a fact (size in sqm, plot size, year, etc.), do NOT claim that fact for the new listing.
- When comparing two prices or sizes, state the direction correctly: 4.2M is lower than 9.5M, not higher.

New listing:
{query}

Retrieved listings:
{listings}

Insight:"""
)


def _trim_to_sentences(text: str, max_sentences: int = 5) -> str:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(parts[:max_sentences])


def generate_insight(query: str, retrieved_listings: list[dict]) -> str:
    listings_text = ""
    for item in retrieved_listings:
        meta = item["metadata"]
        listings_text += (
            f"[{item['id']}] {meta['title']}\n"
            f"Type: {meta['property_type']}\n"
            f"Details: {item['document']}\n\n"
        )

    logger.info("Generating insight for query: %r", query[:80])
    chain = RAG_PROMPT | get_llm()
    with _llm_lock:
        insight = chain.invoke({"query": query, "listings": listings_text})
    result = _trim_to_sentences(insight.strip(), max_sentences=5)
    logger.info("Insight generated: %d chars", len(result))
    return result