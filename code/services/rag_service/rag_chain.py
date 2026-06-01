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
    template="""You are a real estate analyst. Write 2-3 sentences comparing the new listing to the retrieved listings.

Rules:
- Write at least 2 sentences. Each must cite at least one retrieved listing using its exact ID (e.g. [LST-001]).
- You MUST cite at least 2 different listing IDs from the retrieved listings. Do not cite the same listing twice.
- Do not just describe the new listing — explain how it compares to the retrieved ones.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- Use exact numbers as written in the listings.

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
    result = _trim_to_sentences(insight.strip(), max_sentences=4)
    logger.info("Insight generated: %d chars", len(result))
    return result



# RAG_PROMPT = PromptTemplate(
#     input_variables=["query", "listings"],
#     template="""You are a real estate analyst. A new property listing was submitted, and 3 similar listings were retrieved from the agency archive.

# Write a 3-sentence insight comparing the new listing to the retrieved listings.

# Rules:
# - Cite at least one retrieved listing using its exact ID in square brackets, e.g. [LST-004].
# - Use only facts present in the retrieved listings. Do not invent prices, sizes, features, or yields.
# - Do not speculate about market value, demand, pricing competitiveness, or buyers.
# - Stop after the third sentence.
# - Only compare numeric attributes if explicitly present

# New listing:
# {query}

# Retrieved listings:
# {listings}

# INSIGHT:"""
# )




# RAG_PROMPT = PromptTemplate(
#     input_variables=["query", "listings"],
#     template="""You are a strict real estate analysis system.

# You MUST follow all rules exactly. Do not add any extra commentary.

# TASK:
# Write EXACTLY 3 sentences only.

# Each sentence must be one of the following:
# 1. Comparison to [one retrieved listing]
# 2. Comparison to another retrieved listing
# 3. Neutral summary based ONLY on retrieved listings

# STRICT RULES:
# - Do NOT use marketing language (e.g. "attractive", "ideal", "best option")
# - Do NOT evaluate value or desirability
# - Do NOT speculate or infer missing attributes
# - If a fact is not explicitly in the listings, treat it as UNKNOWN
# - Only compare numeric attributes if explicitly present
# - Do NOT add conclusion sentences like "overall", "in summary", etc.

# OUTPUT FORMAT:
# Sentence 1:
# Sentence 2:
# Sentence 3:

# New listing:
# {query}

# Retrieved listings:
# {listings}

# INSIGHT:"""
# )