import logging
import os
import sys
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_graph import run_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("LangGraph Agent ready.")
    yield


app = FastAPI(lifespan=lifespan)


class AgentRequest(BaseModel):
    query: str


class AgentResponse(BaseModel):
    answer: str
    tools_used: list[str]
    reasoning_steps: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/run", response_model=AgentResponse)
async def agent_run(req: AgentRequest):
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")
    result = await run_agent(req.query)
    return AgentResponse(
        answer=result["answer"],
        tools_used=result["tools_used"],
        reasoning_steps=result["reasoning_steps"],
    )
