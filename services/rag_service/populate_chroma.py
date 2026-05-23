import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
LISTINGS_FILE = os.path.join(os.path.dirname(__file__), "synthetic_listings.json")


def populate():
    with open(LISTINGS_FILE, "r", encoding="utf-8") as f:
        listings = json.load(f)

    print("Loading embedding model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection(name="property_listings")
        print("Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(name="property_listings")

    ids = []
    documents = []
    metadatas = []

    for listing in listings:
        if not listing.get("text"):
            print(f"Skipping {listing['listing_id']} — empty text")
            continue
        ids.append(listing["listing_id"])
        documents.append(listing["text"])
        metadatas.append({
            "title": listing["title"],
            "property_type": listing["property_type"],
        })

    embeddings = embedder.encode(documents).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"ChromaDB populated with {collection.count()} listings.")
    assert collection.count() >= 20, "Expected at least 20 listings in ChromaDB"
    print("populate_chroma: PASSED")


if __name__ == "__main__":
    populate()
