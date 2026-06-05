from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
OLLAMA_SYSTEM_PROMPT_FILE = PROMPTS_DIR / "ollama_system.txt"
