import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import chromadb
from fastapi import FastAPI, HTTPException
from pinecone import Pinecone
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from rag_chain import generate_insight, get_llm

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
VECTOR_STORE = os.getenv("VECTOR_STORE", "chroma")   # "chroma" or "pinecone"

_embedder: Optional[SentenceTransformer] = None
_collection = None      # ChromaDB collection
_pinecone_index = None  # Pinecone index


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _collection, _pinecone_index
    print("Loading embedding model...")
    _embedder = SentenceTransformer("all-MiniLM-L6-v2")

    if VECTOR_STORE == "pinecone":
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        _pinecone_index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
        stats = _pinecone_index.describe_index_stats()
        logger.info("Pinecone ready: %d listings", stats["total_vector_count"])
    else:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(name="property_listings")
        logger.info("ChromaDB ready: %d listings", _collection.count())

    logger.info("Vector store: %s", VECTOR_STORE)
    get_llm()
    yield


app = FastAPI(lifespan=lifespan)


class QueryRequest(BaseModel):
    description: str


class ListingResult(BaseModel):
    id: str
    title: str
    property_type: str
    description: str


class QueryResponse(BaseModel):
    similar_listings: list[ListingResult]
    insight: str


@app.get("/health")
def health():
    return {"status": "ok", "vector_store": VECTOR_STORE}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.description.strip():
        raise HTTPException(status_code=422, detail="description must not be empty")

    logger.info("Query received: %r", req.description[:80])
    embedding = _embedder.encode(req.description).tolist()

    if VECTOR_STORE == "pinecone":
        results = _pinecone_index.query(vector=embedding, top_k=3, include_metadata=True)
        retrieved = [
            {
                "id": m["id"],
                "document": m["metadata"]["text"],
                "metadata": {
                    "title": m["metadata"]["title"],
                    "property_type": m["metadata"]["property_type"],
                },
            }
            for m in results["matches"]
        ]
    else:
        results = _collection.query(query_embeddings=[embedding], n_results=3)
        retrieved = [
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    logger.info("Retrieved %d listings from %s", len(retrieved), VECTOR_STORE)
    insight = generate_insight(req.description, retrieved)

    similar_listings = [
        ListingResult(
            id=r["id"],
            title=r["metadata"]["title"],
            property_type=r["metadata"]["property_type"],
            description=r["document"],
        )
        for r in retrieved
    ]

    return QueryResponse(similar_listings=similar_listings, insight=insight)
