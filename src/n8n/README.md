# Layer 2 — n8n Orchestration

Central pipeline per project specification §3.

## Workflow file (use this)

| Item | Value |
|------|--------|
| **File to import** | [`AI_Property_Triage_n8n.json`](./AI_Property_Triage_n8n.json) |
| **Workflow name in n8n** | `AI_Property_Triage` |
| **Webhook path** | `property-triage` |
| **Production URL (local Docker)** | `http://localhost:5678/webhook/property-triage` |

All nodes you edit in n8n should be exported back to this JSON file for version control.

## Other files in this folder

| File | Purpose |
|------|---------|
| `NODE_MAP.md` | Spec node ↔ workflow node names |
| `env.template.txt` | Environment variables (n8n.cloud / Docker) |
| `prompts/` | System prompts for Gemini / LLM nodes |
| `SETUP-n8n-docker.md` | Docker networking (`host.docker.internal`) |
| `SETUP.md` | n8n.cloud deployment |

## Setup checklist

1. Start Layer 3: `..\..\scripts\start-services.ps1`
2. **Workflows** → **Import** → `AI_Property_Triage_n8n.json`
3. Connect **Google Gemini** credentials on all Gemini nodes
4. Verify HTTP/tool URLs reach `host.docker.internal:8001–8004` (Docker) or EC2/ngrok (cloud)
5. **Activate** workflow
6. Copy Production webhook URL → `code/webui/.env` → `N8N_WEBHOOK_URL`

## Flow

```
Node 1 Webhook
  → Node 2 Guardrails Input → Node 3 Router
  → Node 4 Extract (Gemini) → Node 5 AI Agent (tools: RAG, Image, LangGraph)
  → Node 6 Report (Gemini) → Node 7 Guardrails Output → Node 8 Property Router
  → Response to WebUI
```

## Guides

| Environment | Guide |
|-------------|--------|
| **Full run guide** | [docs/GETTING_STARTED.md](../../docs/GETTING_STARTED.md) |
| n8n in Docker | [SETUP-n8n-docker.md](./SETUP-n8n-docker.md) |
| n8n.cloud | [SETUP.md](./SETUP.md) |
