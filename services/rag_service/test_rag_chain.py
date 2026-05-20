import os
import chromadb
from sentence_transformers import SentenceTransformer
from rag_chain import generate_insight

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")


def test_rag_chain():
    # Retrieve 3 listings from ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name="property_listings")

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    query = "Well-maintained 4-bedroom villa with garden and pool"
    embedding = embedder.encode(query).tolist()

    results = collection.query(query_embeddings=[embedding], n_results=3)

    retrieved = []
    for i in range(len(results["ids"][0])):
        retrieved.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        })

    print(f"Retrieved listings: {[r['id'] for r in retrieved]}")

    # Generate insight
    insight = generate_insight(query, retrieved)

    print(f"\nGenerated insight:\n{insight}\n")

    # Assertions
    assert isinstance(insight, str), "Insight must be a string"
    assert len(insight) > 50, f"Insight too short: {len(insight)} chars"

    has_citation = any(r["id"] in insight for r in retrieved)
    assert has_citation, "Insight must cite at least one listing ID"

    print("test_rag_chain: ALL PASSED")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    test_rag_chain()
