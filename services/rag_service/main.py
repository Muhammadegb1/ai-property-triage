import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

import chromadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from rag_chain import generate_insight, get_llm

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

_embedder: Optional[SentenceTransformer] = None
_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _collection
    print("Loading embedding model...")
    _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = client.get_collection(name="property_listings")
    print(f"ChromaDB ready: {_collection.count()} listings")
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
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.description.strip():
        raise HTTPException(status_code=422, detail="description must not be empty")

    embedding = _embedder.encode(req.description).tolist()
    results = _collection.query(query_embeddings=[embedding], n_results=3)

    retrieved = []
    for i in range(len(results["ids"][0])):
        retrieved.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        })

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
