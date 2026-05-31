"""
benchmark_precision.py
----------------------
Measures precision@3 for both ChromaDB and Pinecone vector stores.

precision@3 = number of relevant results in top-3 / 3

A result is considered RELEVANT if its property_type matches
the expected type for that query.

Usage:
    python services/rag_service/benchmark_precision.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ---------------------------------------------------------------------------
# 10 fixed benchmark queries (frozen — do not change between runs)
# Each query has an expected property_type for relevance judgement
# ---------------------------------------------------------------------------
QUERIES = [
    ("Modern apartment in Tel Aviv with sea view",           "apartment"),
    ("3-bedroom apartment near the beach with parking",      "apartment"),
    ("Luxury penthouse with rooftop terrace",                "apartment"),
    ("Commercial office space in Ramat Gan",                 "office"),
    ("Open-plan office floor in business district",          "office"),
    ("Villa with private pool and garden in Herzliya",       "villa"),
    ("5-bedroom villa with landscaped garden",               "villa"),
    ("Retail shop with street frontage high foot traffic",   "retail"),
    ("Studio apartment city center affordable",              "apartment"),
    ("Agricultural land registered Galilee region",         "land"),
]


def precision_at_3(retrieved_types: list[str], expected_type: str) -> float:
    relevant = sum(1 for t in retrieved_types[:3] if t == expected_type)
    return relevant / 3


def run_chroma(embedder, queries):
    import chromadb
    CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name="property_listings")

    scores = []
    for query_text, expected_type in queries:
        embedding = embedder.encode(query_text).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=3)
        retrieved_types = [m["property_type"] for m in results["metadatas"][0]]
        p3 = precision_at_3(retrieved_types, expected_type)
        scores.append((query_text, expected_type, retrieved_types, p3))
    return scores


def run_pinecone(embedder, queries):
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

    scores = []
    for query_text, expected_type in queries:
        embedding = embedder.encode(query_text).tolist()
        results = index.query(vector=embedding, top_k=3, include_metadata=True)
        retrieved_types = [m["metadata"]["property_type"] for m in results["matches"]]
        p3 = precision_at_3(retrieved_types, expected_type)
        scores.append((query_text, expected_type, retrieved_types, p3))
    return scores


def print_results(label: str, scores: list):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    for query_text, expected, retrieved, p3 in scores:
        mark = "OK  " if p3 == 1.0 else ("PART" if p3 > 0 else "FAIL")
        print(f"  [{mark}] p@3={p3:.2f} | expected={expected:<10} | got={retrieved}")
    avg = sum(s[3] for s in scores) / len(scores)
    print(f"\n  Average precision@3: {avg:.3f}  ({avg*100:.1f}%)")
    return avg


if __name__ == "__main__":
    print("Loading embedding model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print("\nRunning ChromaDB benchmark...")
    chroma_scores = run_chroma(embedder, QUERIES)
    chroma_avg = print_results("ChromaDB — precision@3", chroma_scores)

    print("\nRunning Pinecone benchmark...")
    pinecone_scores = run_pinecone(embedder, QUERIES)
    pinecone_avg = print_results("Pinecone — precision@3", pinecone_scores)

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  ChromaDB average precision@3 : {chroma_avg:.3f}")
    print(f"  Pinecone average precision@3 : {pinecone_avg:.3f}")
    diff = pinecone_avg - chroma_avg
    print(f"  Difference                   : {diff:+.3f}")
    print(f"{'='*60}\n")
