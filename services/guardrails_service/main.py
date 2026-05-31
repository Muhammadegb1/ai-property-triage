import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import RailStatus, RailType

RAILS_PATH = os.path.join(os.path.dirname(__file__), "rails")
BLOCKED = "BLOCKED"

_rails: LLMRails | None = None


def get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        config = RailsConfig.from_path(RAILS_PATH)
        _rails = LLMRails(config)
    return _rails


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_rails()
    print("Guardrails loaded.")
    yield


app = FastAPI(lifespan=lifespan)


class CheckRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/check/input")
async def check_input(req: CheckRequest):
    if not req.text.strip():
        return {"pass": False, "reason": "Empty input", "safe_text": None}
    response = await get_rails().generate_async(
        messages=[{"role": "user", "content": req.text}]
    )
    text = response.get("content", "") if isinstance(response, dict) else response
    if BLOCKED in text:
        reason = text.split(":", 1)[1].strip() if ":" in text else "Input failed guardrail check"
        return {"pass": False, "reason": reason, "safe_text": None}
    return {"pass": True, "reason": None, "safe_text": None}


@app.post("/check/output")
async def check_output(req: CheckRequest):
    if not req.text.strip():
        return {"pass": False, "reason": "Empty text", "safe_text": None}
    rails = get_rails()
    result = await rails.check_async(
        messages=[
            {"role": "user", "content": "Provide a property analysis report."},
            {"role": "assistant", "content": req.text},
        ],
        rail_types=[RailType.OUTPUT],
    )
    if result.status == RailStatus.BLOCKED:
        return {"pass": False, "reason": result.rail or "Output failed guardrail check", "safe_text": None}
    return {"pass": True, "reason": None, "safe_text": req.text}
