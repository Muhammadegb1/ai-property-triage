import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")


def test_chroma():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name="property_listings")

    assert collection.count() >= 20, f"Expected >= 20 listings, got {collection.count()}"
    print(f"Count check PASSED: {collection.count()} listings in store")

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    query = "spacious apartment with balcony near the sea"
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(query_embeddings=[query_embedding], n_results=3)

    assert len(results["ids"][0]) == 3, "Expected exactly 3 results"
    print("Result count check PASSED: 3 results returned")

    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        assert "title" in meta, f"Missing 'title' in metadata for {doc_id}"
        assert "property_type" in meta, f"Missing 'property_type' in metadata for {doc_id}"
        assert distance < 2.0, f"Distance too large: {distance}"

        print(f"  Result {i+1}: {doc_id} | {meta['title']} | distance={distance:.4f}")

    print("Schema check PASSED: title and property_type present")
    print("Distance check PASSED: all results within threshold")
    print("\ntest_chroma: ALL PASSED")


if __name__ == "__main__":
    test_chroma()
