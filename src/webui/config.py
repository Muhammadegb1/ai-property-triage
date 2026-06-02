"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
LOCAL_PIPELINE_URL = os.getenv(
    "LOCAL_PIPELINE_URL", "http://127.0.0.1:8090/run"
).rstrip("/")
USE_LOCAL_PIPELINE = os.getenv("USE_LOCAL_PIPELINE", "false").lower() in (
    "1",
    "true",
    "yes",
)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
OLLAMA_SYSTEM_PROMPT_FILE = PROMPTS_DIR / "ollama_system.txt"
