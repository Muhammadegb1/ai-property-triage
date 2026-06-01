# Project Understanding — AI-Powered Real Estate Property Triage System

> This document captures a complete understanding of the project: what it is, how it is structured,
> who owns what, what has been built, and what remains to be done.

---

## 1. What This Project Is

A production-style, end-to-end AI system that automates the intake and initial evaluation of
real estate property listings for a fictional agency.

When a listing agent submits a property description and photographs, the system must:

1. Validate the submission is a genuine property listing (not spam or off-topic)
2. Extract structured fields from the text (type, location, price, rooms, features, certifications)
3. Classify each image by room type and assign a condition score (1–5)
4. Retrieve similar past listings from an internal knowledge base
5. Route the listing to the correct team (residential vs. commercial)
6. Produce a structured, publishable listing brief

---

## 2. System Architecture — Four Layers

The system has exactly four layers. Each layer talks to the next over HTTP only.

```
LAYER 1 — WebUI (Gradio or Streamlit)          [Localhost]
    ↓ webhook POST
LAYER 2 — n8n Orchestration                    [n8n cloud or self-hosted]
    ↕ HTTP calls to EC2
LAYER 3 — AWS EC2 Python Microservices (4x)    [AWS EC2 + Docker]
    ↑ used by layers above
LAYER 4 — External LLM APIs                    [External API / Localhost]
```

---

## 3. Team Split

This codebase is owned by one engineer of a 2-person team.

| Layer | Component | This Engineer | Other Engineer |
|---|---|---|---|
| Layer 1 | WebUI (Gradio/Streamlit) | | ✓ |
| Layer 1 | Ollama conversational assistant | | ✓ |
| Layer 2 | n8n flow (all 8 nodes) | | ✓ |
| Layer 2 | Gemini / GPT-4o LM nodes | | ✓ |
| Layer 3 | RAG Service | ✓ | |
| Layer 3 | Image Analyser | ✓ | |
| Layer 3 | Guardrails Service | ✓ | |
| Layer 3 | LangGraph Agent | ✓ | |
| Layer 4 | Llama.cpp GGUF (used by RAG) | ✓ | |
| Layer 4 | LLM backend for LangGraph | ✓ | |
| Layer 4 | Ollama (WebUI assistant) | | ✓ |

Interface contract: this engineer exposes 4 HTTP endpoints with locked JSON schemas.
The other engineer points their n8n HTTP nodes at those endpoints. Nothing else is shared.
The schema is documented in `docs/service_contracts.md`.

---

## 4. Layer 1 — User Interface (not this engineer's scope)

Technology: Gradio or Streamlit (either is acceptable).

Must have two tabs/sections:

### Tab A — Conversational Assistant
- Chat interface connected to a locally running Ollama server
- Model: Llama 3 or Mistral, running at localhost:11434
- System prompt must ground the model as a real estate assistant
- Must refuse off-topic queries politely, not invent prices or legal advice
- This system prompt is Prompt Engineering Surface #5 (5 iterations required)

### Tab B — Listing Submission Form
- Fields: listing description text, image URLs (comma-separated or file upload), listing agent name
- On submit: sends POST to the n8n webhook
- Must display the structured report returned by n8n including image condition scores and similar-listing recommendations

---

## 5. Layer 2 — n8n Orchestration (not this engineer's scope)

Technology: n8n (self-hosted or cloud)

Eight nodes that must be built:

| Node | Purpose | Key Detail |
|---|---|---|
| 1 — Webhook Trigger | Receives form POST from WebUI | Parses JSON: description + image URLs |
| 2 — Guardrails Input Check | HTTP POST to EC2 :8003/check/input | Branches on pass/fail |
| 3 — IF Branch | Routes fail to rejection, pass to extractor | Standard n8n IF node |
| 4 — Information Extractor | Gemini LM node, extracts structured fields | Prompt Engineering Surface #1 |
| 5 — AI Agent Node | GPT-4o or Gemini, dispatches to EC2 tools | Prompt Engineering Surface #2 |
| 6 — LLM Chain | Produces final listing brief | Prompt Engineering Surface |
| 7 — Guardrails Output Check | HTTP POST to EC2 :8003/check/output | Flags failures for human review |
| 8 — Router | Routes by property_type field | Residential vs Commercial |

Node 5 dispatches parallel HTTP calls to three EC2 services:
- RAG Service (:8001/query)
- Image Analyser (:8002/analyse)
- LangGraph Agent (:8004/agent/run)

Routing logic in Node 8:
- Residential: apartment, house, villa
- Commercial: office, retail, industrial

---

## 6. Layer 3 — EC2 Microservices (this engineer's scope)

Four independent Python FastAPI services. Each is containerised with Docker and deployed on EC2.

Ports:
- RAG Service: 8001
- Image Analyser: 8002
- Guardrails Service: 8003
- LangGraph Agent: 8004

---

### Service 1 — RAG Service

Endpoint: POST /query
Input:  { "description": "<listing text>" }
Output: { "similar_listings": [...], "insight": "<generated text>" }

What it does:
1. Embeds the incoming description with sentence-transformer (all-MiniLM-L6-v2)
2. Queries ChromaDB vector store → top-3 most similar past listings
3. Injects retrieved context into a LangChain prompt
4. Generates a short insight using Llama.cpp (GGUF model file)
5. Returns similar listings + insight

Hard requirements:
- ChromaDB must be pre-populated with at least 20 synthetic listings before deployment
- Insight must cite which similar listing it draws from using [listing_id] notation
- Must not fabricate details not present in retrieved documents
- Prompt Engineering Surface #3: 5 iterations required, tested on 10-case test suite

---

### Service 2 — Image Analyser

Endpoint: POST /analyse
Input:  { "image_url": "<url>" }
Output: { "room_type": "kitchen", "condition_score": 4, "confidence": 0.91 }

What it does:
1. Downloads the image from the URL
2. Preprocesses (resize, normalize)
3. Runs through a fine-tuned CNN
4. Returns room type + condition score + confidence

Hard requirements:
- Base model: pretrained ResNet-50 or EfficientNet-B0
- Transfer learning: freeze backbone, replace classifier head, fine-tune
- Two output heads: room type (6 classes) + condition score (5 classes, 1–5)
- Room type classes: kitchen, bathroom, living room, bedroom, exterior, other
- Below confidence threshold: return room_type "uncertain"
- Training dataset: at least 200 labelled images
- Must document data augmentation strategy
- Must report final test set accuracy
- Grading target: >75% room type accuracy for excellent grade

---

### Service 3 — Guardrails Service

Endpoints:
- POST /check/input
- POST /check/output

Input:  { "text": "<text to check>" }
Output: { "pass": true/false, "reason": "<if fail>", "safe_text": "<if output>" }

Input endpoint: rejects spam, offensive content, off-topic, unexpected languages.
Output endpoint: rejects false legal claims, invented prices, fabricated certifications.

Hard requirements:
- Uses NeMo Guardrails with YAML/Colang rail configs
- Output failures are flagged for human review, not returned to WebUI
- False positive rate on valid listings must be < 5%
- Prompt Engineering Surface #4 — two sub-surfaces:
  - Topic detection prompt (input rail): 5 iterations
  - Output auditor prompt (output rail): 5 iterations
  - Each tested on a 10-case test suite

---

### Service 4 — LangGraph Agent

Endpoint: POST /agent/run
Input:  { "query": "<complex question about the listing>" }
Output: { "answer": "...", "tools_used": [...], "reasoning_steps": [...] }

What it does:
- Stateful LangGraph agent with exactly 3 nodes:
  1. Planner node: decides which tools to call
  2. Tool executor node: calls RAG Service and/or Image Analyser
  3. Synthesiser node: combines tool outputs into a final answer

Hard requirements:
- Can invoke both RAG Service and Image Analyser as tools
- Tool descriptions are the key lever controlling which tool gets called
- Prompt Engineering Surface — LangGraph Tool Descriptions:
  - 5 iterations on tool descriptions
  - Same 10 benchmark queries used across all 5 versions

---

## 7. Layer 4 — LLM Backends

| Backend | Used By | Where |
|---|---|---|
| Llama.cpp GGUF (Meta-Llama-3.1-8B-Instruct-Q4_K_M) | RAG Service insight generation | EC2 local file |
| GPT-4o-mini | LangGraph Agent planner + synthesiser | External API |
| Google Gemini Flash | Guardrails Service (NeMo backend) | External API |
| Google Gemini or GPT-4o | n8n LM nodes (Layer 2) | External API (other engineer) |
| Ollama + Llama 3 / Mistral | WebUI conversational assistant | Localhost (other engineer) |

---

## 8. Prompt Engineering Log — Full Overview

Graded deliverable worth 25% of the total score.

Five surfaces total. Three are this engineer's responsibility:

| # | Surface | Owner | Status |
|---|---|---|---|
| 1 | n8n Info Extractor — systemPromptTemplate | Other engineer | Not this scope |
| 2 | n8n AI Agent — system prompt + tool descriptions | Other engineer | Not this scope |
| 3 | LangChain RAG Retrieval — context injection + citation | This engineer | Iterations in code, log doc MISSING |
| 4 | Guardrails Rail Prompts — topic detection + output auditor | This engineer | COMPLETE — docs/prompt_engineering_log_guardrails.md |
| 5 | Local Ollama System Prompt — real estate assistant grounding | Other engineer | Not this scope |

Required format for each surface log:
- Version 1: baseline attempt, run on test cases, record outputs
- Versions 2–3: one failure identified per version, prompt modified, re-run, regressions checked
- Versions 4–5: refinement with articulated learnings
- Final entry: full final prompt, justification per design decision, pass rate on test suite
- Minimum: 10 test cases per surface, pass rate reported per version

---

## 9. Deliverables Summary

### Code
- [ ] n8n flow exported as importable JSON (other engineer)
- [x] RAG Service: services/rag_service/ with Dockerfile + requirements.txt
- [x] Image Analyser: services/image_analyser/ with Dockerfile + requirements.txt
- [x] Guardrails Service: services/guardrails_service/ with Dockerfile + requirements.txt
- [x] LangGraph Agent: services/langgraph_agent/ with Dockerfile + requirements.txt
- [ ] WebUI: app.py or equivalent with README (other engineer)
- [x] ChromaDB pre-population script (populate_chroma.py) — 20 listings
- [x] PyTorch model checkpoint best_model.pth — exists in checkpoints/

### Documentation
- [ ] Prompt Engineering Log — Surface #3 (RAG) document MISSING
- [x] Prompt Engineering Log — Surface #4 (Guardrails) complete
- [ ] Architecture diagram — student's own version with annotated design decisions
- [ ] Deployment notes — EC2 instance types, ports, deviations from spec
- [ ] Augmentation strategy document — services/image_analyser/data/augmentation_strategy.md

### Demo
- [ ] 5–8 minute video:
  - [ ] Successful end-to-end listing submission
  - [ ] Listing that fails the input guardrail
  - [ ] Listing that fails the output guardrail
  - [ ] Conversational exchange with Ollama assistant

---

## 10. Current Codebase State

### What Is Built and Working

**RAG Service** — functionally complete
- FastAPI POST /query with correct schema
- Sentence-transformer + ChromaDB + Pinecone dual support (optional extension already done)
- Llama.cpp with GGUF model downloaded at startup from HuggingFace
- 20 synthetic listings (synthetic_listings.json) + populate_chroma.py
- RAG prompt at v4 (active), with older versions as commented-out code in rag_chain.py
- benchmark_precision.py exists for the optional Pinecone extension
- docs/vector_store_comparison.md exists

**Image Analyser** — functionally complete
- FastAPI POST /analyse with correct schema
- EfficientNet-B0 with frozen backbone + dual head (room + condition)
- Confidence threshold = 0.6, returns "uncertain" below it
- Training complete: Room accuracy 89.4% (above 75% target), Condition accuracy 49.7%
- 3,840 labelled images in dataset (well above 200 minimum)
- best_model.pth checkpoint exists
- Note: implementation uses 8 room type classes (balcony, bathroom, bedroom, building_exterior,
  garden, kitchen_dining, living_room, not_real_estate) vs the spec's 6 — a reasonable deviation

**Guardrails Service** — complete including documentation
- FastAPI POST /check/input and POST /check/output both working
- NeMo Guardrails + YAML/Colang configs (config.yml, input_rails.co, output_rails.co)
- 5 prompt versions for both input and output rails (prompts/input_v1..v5, output_v1..v5)
- Structured prompt engineering log: docs/prompt_engineering_log_guardrails.md
- Final pass rate: 20/20 (100%) on 20-case test suite

**LangGraph Agent** — functionally complete
- FastAPI POST /agent/run with correct schema
- 3-node stateful graph: planner → tool_executor → synthesiser
- Both tools wired (RAG + Image Analyser via httpx)
- Uses GPT-4o-mini (allowed: "Llama.cpp or external LLM API")
- 5 planner prompt versions exist (planner_v1.txt through planner_v5.txt)
- Tool descriptions log file exists (tool_descriptions_log.md) — completeness needs verification
- 10-query benchmark test file exists (test_tool_descriptions.py) with expected tool outputs

---

### What Is Still Missing (this engineer's scope)

**1. RAG Prompt Engineering Log document**
No structured log document exists for Surface #3.
Iterations are only embedded as commented code in rag_chain.py.
Current active prompt is v4. Need: a log doc covering 5 versions with failure analysis,
test suite results (min 10 cases), and pass rates.
File that should exist: docs/prompt_engineering_log_rag.md (or equivalent)

**2. RAG prompt needs a v5**
PROMPT_VERSION = "v4" in rag_chain.py. The requirement is 5 iterations minimum.
Either write v5, or document v4 as final with justification — but the log must show 5 entries.

**3. LangGraph tool descriptions log completeness**
tool_descriptions_log.md shows v1 (score 1/10) with failure analysis.
Need to verify all 5 versions are documented with benchmark scores.

**4. Missing documentation files**
- docs/deployment_notes.md — required by Section 7.2 (EC2 types, ports, deviations)
- Architecture diagram — required by Section 7.2
- services/image_analyser/data/augmentation_strategy.md — required by Section 7.1

**5. Integration test**
No test_integration.py at project root running all 4 services together.

**6. Condition score accuracy is 49.7%**
The second output head (condition score) is weak. Not a hard blocker since grading
focuses on room type accuracy (89.4%), but worth noting in documentation.

---

## 11. Optional Extensions Status

| Extension | Status |
|---|---|
| Managed Vector Store (Pinecone) | Partially done — populate_pinecone.py, benchmark_precision.py, Pinecone wired in main.py via VECTOR_STORE env var, docs/vector_store_comparison.md exists |
| Feedback Loop and Active Learning | Not started |
| Multilingual Guardrail | Not started |
| Monitoring Dashboard | Not started |

---

## 12. Grading Risk Summary

| Criterion | Weight | Current Status | Risk |
|---|---|---|---|
| n8n Flow | 20% | Other engineer's scope | Unknown |
| EC2 Services | 25% | All 4 functionally complete | Low |
| Image Analyser | 10% | 89.4% room accuracy | Low |
| Guardrails | 10% | 0% false positive on test suite | Low |
| Prompt Engineering Log | 25% | Surface #4 complete, Surface #3 log missing | HIGH |
| WebUI + Ollama | 10% | Other engineer's scope | Unknown |

The biggest risk to grade is the Prompt Engineering Log (25% weight).
Surface #3 (RAG) has no log document.
Surface — LangGraph tool descriptions may be incomplete.
These must be completed before submission.
