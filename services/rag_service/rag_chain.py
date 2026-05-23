import huggingface_hub
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import LlamaCpp

_llm = None


def get_llm() -> LlamaCpp:
    global _llm
    if _llm is None:
        print("Loading Llama model...")
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
            stop=["Note:", "Best regards", "Here is", "I hope","Lastly","Finally", "\n\n\n", "\n\n"],
        )
        print("Llama model loaded.")
    return _llm


PROMPT_VERSION = "v4"

RAG_PROMPT = PromptTemplate(
    input_variables=["query", "listings"],
    template="""You are a real estate analyst. A new property listing was submitted, and 3 similar listings were retrieved from the agency archive.

Write a 3-sentence insight comparing the new listing to the retrieved listings.

Rules:
- Cite at least one retrieved listing using its exact ID in square brackets, e.g. [LST-004].
- Use only facts present in the retrieved listings. Do not invent prices, sizes, features, or yields.
- Do not speculate about market value, demand, pricing competitiveness, or buyers.
- Stop after the third sentence.

New listing:
{query}

Retrieved listings:
{listings}

INSIGHT:"""
)


def generate_insight(query: str, retrieved_listings: list[dict]) -> str:
    listings_text = ""
    for item in retrieved_listings:
        meta = item["metadata"]
        listings_text += (
            f"[{item['id']}] {meta['title']}\n"
            f"Type: {meta['property_type']}\n"
            f"Details: {item['document']}\n\n"
        )

    chain = RAG_PROMPT | get_llm()
    insight = chain.invoke({"query": query, "listings": listings_text})
    return insight.strip()
