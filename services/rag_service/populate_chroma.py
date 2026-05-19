import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
LISTINGS_FILE = os.path.join(os.path.dirname(__file__), "synthetic_listings.json")


def populate():
    with open(LISTINGS_FILE, "r", encoding="utf-8") as f:
        listings = json.load(f)

    print(f"Loading embedding model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name="property_listings")

    ids = []
    documents = []
    metadatas = []

    for listing in listings:
        if not listing.get("description"):
            print(f"Skipping {listing['id']} — empty description")
            continue
        ids.append(listing["id"])
        documents.append(listing["description"])
        metadatas.append({
            "title": listing["title"],
            "property_type": listing["property_type"],
            "location": listing["location"],
            "price": listing["price"],
            "num_rooms": listing["num_rooms"],
            "key_features": ", ".join(listing["key_features"]),
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
