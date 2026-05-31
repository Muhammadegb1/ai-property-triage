import json
import os

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

load_dotenv()

LISTINGS_FILE = os.path.join(os.path.dirname(__file__), "synthetic_listings.json")


def populate():
    with open(LISTINGS_FILE, "r", encoding="utf-8") as f:
        listings = json.load(f)

    print("Loading embedding model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

    vectors = []
    for listing in listings:
        if not listing.get("text"):
            print(f"Skipping {listing['listing_id']} — empty text")
            continue
        embedding = embedder.encode(listing["text"]).tolist()
        vectors.append({
            "id": listing["listing_id"],
            "values": embedding,
            "metadata": {
                "title": listing["title"],
                "property_type": listing["property_type"],
                "text": listing["text"],
            },
        })

    index.upsert(vectors=vectors)

    stats = index.describe_index_stats()
    count = stats["total_vector_count"]
    print(f"Pinecone populated with {count} listings.")
    assert count >= 20, f"Expected at least 20 listings, got {count}"
    print("populate_pinecone: PASSED")


if __name__ == "__main__":
    populate()
