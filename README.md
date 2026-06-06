# AI-Powered Real Estate Property Triage System

A production-grade, multi-layer AI system that automates the intake and evaluation of real estate property listings. The system validates submissions, classifies images, retrieves similar past listings, and produces structured triage reports — all orchestrated through a stateful AI pipeline.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Layer 1 — WebUI](#layer-1--webui)
- [Layer 2 — n8n Orchestration](#layer-2--n8n-orchestration)
- [Layer 3 — EC2 Microservices](#layer-3--ec2-microservices)
- [Layer 4 — External LLM APIs](#layer-4--external-llm-apis)
- [Data Flow](#data-flow)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Docker Deployment](#docker-deployment)
- [EC2 Deployment](#ec2-deployment)
- [API Contracts](#api-contracts)
- [Prompt Engineering Surfaces](#prompt-engineering-surfaces)
- [Optional Extensions Implemented](#optional-extensions-implemented)
- [Screenshots](#screenshots)

---

## System Overview

The system processes property listing submissions through a four-layer pipeline:

1. A listing agent submits a description and property images via the **WebUI**
2. **n8n** orchestrates the flow — validating input, extracting structured fields, and calling AI services
3. Four **FastAPI microservices on AWS EC2** handle RAG retrieval, image analysis, guardrails, and agent reasoning
4. **External LLMs** (OpenAI GPT-4o-min) power the extraction and synthesis nodes

The result is a structured triage report with property type, condition scores, similar listings, and a market insight — routed to the correct team (residential or commercial).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — WebUI (Streamlit · localhost:8501)                       │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐   │
│  │  Assistant Chat Tab │    │  Listing Submission Tab          │   │
│  │  Ollama + Tavily    │    │  Form → POST → n8n Webhook       │   │
│  └─────────────────────┘    └──────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ webhook POST
┌────────────────────────────────▼────────────────────────────────────┐
│  LAYER 2 — n8n Orchestration                                        │
│  Webhook → Guardrails Input → Info Extractor → AI Agent →          │
│  Guardrails Output → Report Normaliser → Router                     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP calls
┌────────────────────────────────▼────────────────────────────────────┐
│  LAYER 3 — AWS EC2 Microservices (Docker · FastAPI)                 │
│  ┌────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │RAG Service │ │Image Analyser│ │ Guardrails  │ │  LangGraph  │ │
│  │  :8001     │ │    :8002     │ │    :8003    │ │   Agent     │ │
│  │LangChain   │ │EfficientNet  │ │    NeMo     │ │   :8004     │ │
│  │Llama.cpp   │ │    B0 CNN    │ │  Guardrails │ │  GPT-4o     │ │
│  │Pinecone    │ │Room+Condition│ │Input+Output │ │  mini       │ │
│  └────────────┘ └──────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — WebUI

**Technology:** Streamlit · Ollama · OpenAI · Tavily Search API

The web application provides two tabs:

### Assistant Tab

A real-time chat interface with a **model selector** that lets the user choose between three LLM backends at runtime:

| Model | Backend | Description |
|-------|---------|-------------|
| 🦙 Llama 3.1 | Local · Ollama | Fast, private, no API cost |
| 🦙 Llama 3.2 | Local · Ollama | Smaller and faster local model |
| ✨ GPT-4o mini | OpenAI API | Most accurate, handles complex financial data |

The selected model is **persisted in the URL** (`?model=llama31`) so it survives page refreshes. Switching models automatically clears the chat history.

When the user asks a property-related question (price, market trends, rentals), the assistant automatically calls the Tavily web search API to inject current market data before generating a response.

**Key behaviour:**
- Model selector with horizontal pill UI — switches backend instantly
- Detects real estate questions via keyword matching (English + Hebrew)
- Shows `🔍 Searching web for latest data…` while Tavily fetches results
- Tavily failures are handled silently — the selected model responds from its own knowledge
- Streams responses token-by-token with a live cursor
- Sidebar reflects the currently active model in real time

### Submission Tab

A form where listing agents submit property descriptions and image URLs. On submission, the form POSTs to the n8n webhook and waits for the triage report. The returned report is rendered with:

- **Metrics row:** Property type, location, price (ILS), rooms, confidence score
- **Key features:** Tag chips (blue/gold)
- **Image analysis cards:** Room type classification, condition score (1–5), confidence progress bar
- **Similar listings:** Three comparable past listings from the agency archive
- **RAG insight:** A market comparison paragraph citing specific listing IDs

**Source:** `src/webui/`

---

## Layer 2 — n8n Orchestration

**Technology:** n8n · OpenAI GPT-4o-mini

The n8n workflow (`src/n8n/AI_Property_Triage_n8n.json`) is the central pipeline coordinator.

| Node | Role |
|------|------|
| 1 — Webhook Trigger | Receives `{description, image_urls, agent_name}` from WebUI |
| 2 — Guardrails Input Check | POSTs to EC2 guardrails service; blocks spam and off-topic input |
| 3 — IF Router | Branches: rejection path or processing path |
| 4 — Information Extractor | LLM node extracts structured fields from listing text |
| 5 — AI Agent | Calls LangGraph Agent service; orchestrates RAG + image analysis |
| 6 — Guardrails Output Check | Validates generated report for false claims |
| 7 — Output Router | Routes to human review if flagged |
| 8 — Send Response | Returns structured JSON report to WebUI |

**Workflow file:** `src/n8n/AI_Property_Triage_n8n.json`

![n8n Workflow](https://github.com/user-attachments/assets/06a53f9d-53cf-411a-a861-c36aa469ed5f)

---

## Layer 3 — EC2 Microservices

All four services run as Docker containers on a single AWS EC2 t3.large instance. Each is a FastAPI application exposing a single primary endpoint.

### Service 1 — RAG Service (Port 8001)

Receives a property description, embeds it using `sentence-transformers/all-MiniLM-L6-v2`, retrieves the top 3 semantically similar past listings from the vector store, and generates a market insight using a local LLM.

**Vector store options:**
- **ChromaDB** (default) — Local SQLite-backed, persisted to a mounted volume
- **Pinecone** (production) — Cloud-managed, pre-populated with 20+ synthetic listings

**LLM backends:**
- **Llama.cpp** — Local GGUF model (`Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`)
- **Ollama** — Connects to a running Ollama server via HTTP

**Source:** `src/services/rag_service/`

---

### Service 2 — Image Analyser (Port 8002)

Downloads a property image from a URL and classifies it using a fine-tuned EfficientNet-B0 with two output heads:

- **Room type classification** — 8 classes: `bathroom`, `bedroom`, `building_exterior`, `garden`, `kitchen_dining`, `living_room`, `balcony`, `not_real_estate`
- **Condition scoring** — Integer 1–5 (1 = poor, 5 = excellent)

The backbone is frozen (ImageNet pretrained). Only the two classifier heads were trained on a labelled dataset of 3,840 property images.

| Metric | Result |
|--------|--------|
| Room type accuracy | 89.4% |
| Condition score accuracy | 49.7% |
| Training dataset | 3,840 images (8 classes, balanced) |
| Confidence threshold | 0.6 (configurable) |

**Source:** `src/services/image_analyser/`

![Image Analyser Results](https://github.com/user-attachments/assets/5409570d-b9ad-4cca-abfd-40f04e61e8e4)

---

### Service 3 — Guardrails Service (Port 8003)

A dual-endpoint NeMo Guardrails service that validates both incoming listings and outgoing AI reports.

**Input guardrail (`/check/input`):**
- Accepts genuine property listings in English or Hebrew
- Blocks: spam, cryptocurrency, cooking content, prompt injection attempts, off-topic submissions

**Output guardrail (`/check/output`):**
- Accepts factual, verifiable property reports
- Blocks: financial guarantees, invented property details, false legal certifications, definitive valuations

**Source:** `src/services/guardrails_service/`

---

### Service 4 — LangGraph Agent (Port 8004)

A stateful multi-step reasoning agent built with LangGraph. The graph has three nodes:

```
Planner → Tool Executor → Synthesiser → END
```

| Node | Role |
|------|------|
| **Planner** | Analyses the query and generates a JSON plan of tool calls |
| **Tool Executor** | Executes HTTP calls to RAG Service and Image Analyser asynchronously |
| **Synthesiser** | Combines all tool results into a comprehensive structured answer |

**Available tools:**
- `query_similar_listings(description)` — Calls RAG Service to retrieve 3 comparable listings + market insight
- `analyse_property_image(image_url)` — Calls Image Analyser to classify room type and assign condition score

**LLM:** OpenAI GPT-4o-mini (temperature 0.0)

**Source:** `src/services/langgraph_agent/`

---

## Layer 4 — External LLM APIs

| Purpose | Model | Used By |
|---------|-------|---------|
| Information extraction | OpenAI GPT-4o-mini | n8n Node 4 |
| Agent orchestration | OpenAI GPT-4o-mini | n8n Node 5 |
| Guardrail evaluation | OpenAI GPT-4o-mini | Guardrails Service |
| Agent synthesis | OpenAI GPT-4o-mini | LangGraph Agent |
| Conversational assistant | Ollama (Llama 3.1 / 3.2) or OpenAI GPT-4o mini | WebUI (user-selectable) |
| RAG inference | Llama.cpp (Llama 3.1 GGUF) | RAG Service |

---

## Data Flow

```
User fills form
     │
     ▼
WebUI POSTs {description, image_urls, agent_name}
     │
     ▼
n8n Node 2: Guardrails Input Check
     │ BLOCKED → Return 422 rejection to WebUI
     │ PASS ↓
n8n Node 4: Information Extractor (openai)
     │ → property_type, location, price_ils, num_rooms, key_features
     ▼
n8n Node 5: AI Agent calls LangGraph Agent (EC2 :8004)
     │
     ├── LangGraph Planner decides tool calls
     │
     ├── Tool Executor → RAG Service (EC2 :8001)
     │                    → Embed description → Pinecone search → top 3 listings
     │                    → Llama.cpp generates market insight
     │
     └── Tool Executor → Image Analyser (EC2 :8002) × N images
                          → EfficientNet-B0 inference
                          → room_type + condition_score per image
     │
     ▼
LangGraph Synthesiser combines results
     │
     ▼
n8n Node 6: Guardrails Output Check
     │ BLOCKED → Flag for human review
     │ PASS ↓
n8n Node 8: Return JSON report
     │
     ▼
WebUI renders triage report
```

---

## Prerequisites

- Python 3.10+
- Docker Desktop (for local container testing)
- [Ollama](https://ollama.ai) installed locally with `llama3.1` pulled
- n8n account (cloud or self-hosted)
- OpenAI API key
- Tavily API key (optional, for web search in chat)
- Pinecone account (optional, for cloud vector store)
- AWS account with EC2 access (for production deployment)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Yes | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:latest` | Yes | Ollama model name |
| `TAVILY_API_KEY` | — | No | Tavily web search API key |
| `N8N_WEBHOOK_URL` | — | Yes | n8n webhook endpoint URL |
| `REQUEST_TIMEOUT` | `300` | No | HTTP timeout in seconds |
| `OPENAI_API_KEY` | — | Yes | OpenAI API key |
| `LLM_BACKEND` | `ollama` (local) / `llamacpp` (EC2) | Yes | `llamacpp` or `ollama` |
| `GGUF_MODEL_PATH` | — | No | Path to GGUF file (auto-downloads if empty) |
| `VECTOR_STORE` | `pinecone` | Yes | `chroma` or `pinecone` |
| `PINECONE_API_KEY` | — | If Pinecone | Pinecone API key |
| `PINECONE_INDEX_NAME` | — | If Pinecone | Pinecone index name |
| `IMAGE_CONFIDENCE_THRESHOLD` | `0.6` | No | Confidence cutoff for room classification |
| `RAG_SERVICE_URL` | `http://localhost:8001` | Yes | RAG service URL |
| `IMAGE_ANALYSER_URL` | `http://localhost:8002` | Yes | Image Analyser URL |
| `HTTP_TIMEOUT` | `300` | No | Timeout for inter-service calls |

---

## Local Development Setup

**1. Install Ollama and pull the model:**
```bash
ollama pull llama3.1:latest
```

**2. Create and activate virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r src/webui/requirements.txt
```

**3. Configure environment:**
```bash
cp .env.example .env
# Fill in your API keys in .env
```

**4. Populate the vector store:**
```bash
cd src/services/rag_service
python populate_pinecone.py   # for Pinecone
# or
python populate_chroma.py     # for ChromaDB
```

**5. Start the WebUI:**
```bash
cd src/webui
streamlit run app.py
```

**6. Import n8n workflow:**
- Open your n8n instance
- Import `src/n8n/AI_Property_Triage_n8n.json`
- Configure the HTTP nodes with the correct EC2 service URLs

---

## Docker Deployment

**Build and start all services locally:**
```bash
docker compose up -d
```

**Check all services are running:**
```bash
docker compose ps
```

**View logs:**
```bash
docker compose logs -f rag_service
docker compose logs -f image_analyser
docker compose logs -f guardrails_service
docker compose logs -f langgraph_agent
```

**Verify health endpoints:**
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

---

## EC2 Deployment

**Instance requirements:**
- Type: `t3.large` (2 vCPU, 8 GB RAM)
- OS: Ubuntu 22.04 LTS
- Storage: 50 GB EBS gp3
- Security group: TCP inbound on ports 8001, 8002, 8003, 8004

**1. Install Docker on EC2:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
```

**2. Download the GGUF model:**
```bash
mkdir -p ~/models
wget -O ~/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf \
  https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
```

**3. Build the RAG service directly on EC2** (required for CPU compatibility):
```bash
scp -i your-key.pem -r src/services/rag_service ubuntu@<EC2-IP>:~/rag_service
# On EC2:
sudo docker build -t rag_service_local ~/rag_service
```
> The RAG service must be built on EC2 because `llama-cpp-python` compiles against the native CPU. A pre-built image from another machine will crash with SIGILL on EC2.

**4. Copy docker-compose.yml and .env to EC2:**
```bash
scp -i your-key.pem docker-compose.yml ubuntu@<EC2-IP>:~/
scp -i your-key.pem .env ubuntu@<EC2-IP>:~/
```

**5. Use pre-built images on EC2 docker-compose.yml:**

The EC2 `docker-compose.yml` references pre-built Docker Hub images and uses absolute volume paths:
```yaml
services:
  rag_service:
    image: rag_service_local        # built directly on EC2
    ports: ["8001:8001"]
    volumes:
      - /home/ubuntu/models:/models  # use absolute path, not ~/models
    env_file: .env

  image_analyser:
    image: muhammad9eg/image_analyser:latest
    ports: ["8002:8002"]
    env_file: .env

  guardrails_service:
    image: muhammad9eg/guardrails_service:latest
    ports: ["8003:8003"]
    env_file: .env

  langgraph_agent:
    image: muhammad9eg/langgraph_agent:latest
    ports: ["8004:8004"]
    env_file: .env
    environment:
      - RAG_SERVICE_URL=http://rag_service:8001
      - IMAGE_ANALYSER_URL=http://image_analyser:8002
    depends_on:
      - rag_service
      - image_analyser
```

**6. Set GGUF model path in .env:**
```
LLM_BACKEND=llamacpp
GGUF_MODEL_PATH=/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
```

**7. Start all services:**
```bash
sudo docker compose up -d
```

**6. Update n8n HTTP node URLs** to use the EC2 public IP:
```
http://<EC2-PUBLIC-IP>:8001/query
http://<EC2-PUBLIC-IP>:8002/analyse
http://<EC2-PUBLIC-IP>:8003/check/input
http://<EC2-PUBLIC-IP>:8004/agent/run
```

> **Security note:** Restrict EC2 security group inbound rules to your n8n instance IP and your development machine only. Never commit API keys to the repository.

---

## API Contracts

### RAG Service — `POST /query`

```json
// Request
{ "description": "3-bedroom apartment in Tel Aviv, 95sqm, renovated kitchen" }

// Response
{
  "similar_listings": [
    {
      "id": "LST-001",
      "title": "Modern 3BR in Florentin",
      "description": "...",
      "property_type": "apartment",
      "location": "Tel Aviv",
      "price": 3200000
    }
  ],
  "insight": "The submitted listing compares favourably to [LST-001]..."
}
```

### Image Analyser — `POST /analyse`

```json
// Request
{ "image_url": "https://example.com/kitchen.jpg" }

// Response
{ "room_type": "kitchen_dining", "condition_score": 4, "confidence": 0.87 }
```

### Guardrails — `POST /check/input` and `POST /check/output`

```json
// Request
{ "text": "<listing text or generated report>" }

// Response (pass)
{ "pass": true, "reason": null, "safe_text": null }

// Response (fail)
{ "pass": false, "reason": "Submission does not appear to be a property listing", "safe_text": null }
```

### LangGraph Agent — `POST /agent/run`

```json
// Request
{ "query": "Analyse this apartment: 3BR in Ramat Gan, 85sqm. Image: https://..." }

// Response
{
  "answer": "Based on RAG retrieval, this listing is comparable to...",
  "tools_used": ["query_similar_listings", "analyse_property_image"],
  "reasoning_steps": ["Calling RAG service...", "Calling Image Analyser..."]
}
```

---

## Prompt Engineering Surfaces

The project includes 5 documented prompt engineering surfaces, each iterated at least 5 times with a 10-case test suite.

| # | Surface | Location | Status |
|---|---------|----------|--------|
| 1 | n8n Information Extractor | `src/n8n/prompts/extractor_v*.txt` | v5 active |
| 2 | n8n AI Agent System Prompt | `src/n8n/prompts/agent_system_v*.txt` | v5 active |
| 3 | LangChain RAG Retrieval Prompt | `src/services/rag_service/rag_chain.py` | v5 active |
| 4 | NeMo Guardrails Rail Prompts | `src/services/guardrails_service/rails/config.yml` | v5 active (20/20 test cases) |
| 5 | Ollama System Prompt | `src/webui/prompts/ollama_system.txt` | v5 active |

---

## Optional Extensions Implemented

The following optional extensions from the project specification were implemented:

### Managed Vector Store (Pinecone)
Replaced the default local ChromaDB instance with Pinecone cloud vector store. Pre-populated with 20 synthetic property listings. Switchable via the `VECTOR_STORE` environment variable without code changes.

### Web Search Enrichment (Tavily)
Added Tavily AI web search to the WebUI assistant tab. Real estate questions automatically trigger a live web search to inject current market data (prices, trends, news) as context before the model generates a response. Configurable via `TAVILY_API_KEY`.

### Multi-Model Chat Selector
Added a runtime model selector to the assistant tab. Users can switch between Llama 3.1, Llama 3.2 (both via local Ollama), and GPT-4o mini (OpenAI API) without restarting the app. The selection persists across page refreshes via URL query parameters.

---

## Project Structure

```
ai-property-triage/
├── src/
│   ├── webui/                          # Layer 1 — Streamlit frontend
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── assistant_tab.py
│   │   ├── submission_tab.py
│   │   ├── report_view.py
│   │   ├── n8n_client.py
│   │   ├── ollama_client.py
│   │   └── prompts/
│   │       └── ollama_system.txt
│   │
│   ├── services/
│   │   ├── rag_service/                # EC2 :8001 — RAG + LLM
│   │   │   ├── main.py
│   │   │   ├── rag_chain.py
│   │   │   ├── populate_pinecone.py
│   │   │   ├── populate_chroma.py
│   │   │   └── Dockerfile
│   │   │
│   │   ├── image_analyser/             # EC2 :8002 — CNN image analysis
│   │   │   ├── main.py
│   │   │   ├── model.py
│   │   │   ├── train.py
│   │   │   ├── dataset.py
│   │   │   └── Dockerfile
│   │   │
│   │   ├── guardrails_service/         # EC2 :8003 — NeMo input/output safety
│   │   │   ├── main.py
│   │   │   ├── rails/
│   │   │   │   ├── config.yml
│   │   │   │   ├── input_rails.co
│   │   │   │   └── output_rails.co
│   │   │   └── Dockerfile
│   │   │
│   │   └── langgraph_agent/            # EC2 :8004 — Multi-step agent
│   │       ├── main.py
│   │       ├── agent_graph.py
│   │       ├── tools.py
│   │       └── Dockerfile
│   │
│   └── n8n/                            # Layer 2 — Workflow definition
│       ├── AI_Property_Triage_n8n.json
│       └── prompts/
│
├── docs/                               # Prompt engineering logs + contracts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Screenshots

### WebUI — Assistant Tab
![Assistant Tab](docs/screenshots/assistant_tab.png)

### WebUI — Submission Form
![Submission Tab](https://github.com/user-attachments/assets/385473ff-9a10-43b8-b6bb-320c8b39b27f")
![Submission Tab](https://github.com/user-attachments/assets/01c1b456-b9ec-4855-acd3-fc6237c1bafd")



### WebUI — Triage Report (Successful Submission)
![Triage Report](docs/screenshots/triage_report_success.png)

### WebUI — Triage Report (Input Guardrail Rejection)
![Guardrail Rejection](docs/screenshots/triage_report_rejected.png)

### WebUI — Triage Report (Output Guardrail Human Review)
![Human Review](docs/screenshots/triage_report_human_review.png)

### n8n Workflow
![n8n Flow](docs/screenshots/n8n_workflow.png)

### EC2 Services Running
![Docker PS](docs/screenshots/ec2_docker_ps.png)

### Image Analysis Cards
![Image Analysis](docs/screenshots/image_analysis_cards.png)

### Similar Listings Section
![Similar Listings](docs/screenshots/similar_listings.png)
