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
            n_threads=6,
            temperature=0.2,
            max_tokens=200,
            verbose=False,
            stop=["Note:", "Best regards", "Here is", "I hope", "\n\n\n"],
        )
        print("Llama model loaded.")
    return _llm


RAG_PROMPT = PromptTemplate(
    input_variables=["query", "listings"],
    template="""You are a real estate analyst. Below are 3 similar past listings from our database.

RETRIEVED LISTINGS:
{listings}
NEW LISTING QUERY:
{query}

Write exactly 2 to 4 sentences. Cite at least one listing ID in square brackets like [listing_001]. Use only facts from the listings above. Do not add notes or sign-offs.

INSIGHT:"""
)


def generate_insight(query: str, retrieved_listings: list[dict]) -> str:
    listings_text = ""
    for item in retrieved_listings:
        meta = item["metadata"]
        listings_text += (
            f"[{item['id']}] {meta['title']}\n"
            f"Location: {meta['location']} | Type: {meta['property_type']} | "
            f"Price: {meta['price']} | Rooms: {meta['num_rooms']}\n"
            f"Features: {meta['key_features']}\n"
            f"Description: {item['document']}\n\n"
        )

    chain = RAG_PROMPT | get_llm()
    insight = chain.invoke({"query": query, "listings": listings_text})
    return insight.strip()
