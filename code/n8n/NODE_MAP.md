# n8n workflow node map

**Workflow file:** [`AI_Property_Triage_n8n.json`](./AI_Property_Triage_n8n.json)  
**Workflow name in n8n:** `AI_Property_Triage`  
**Webhook:** `POST /webhook/property-triage`

## Spec §3 ↔ workflow nodes

| Spec # | Spec name | Node in `AI_Property_Triage_n8n.json` |
|--------|-----------|----------------------------------------|
| 1 | Webhook Trigger | `Node 1 — Webhook Trigger` |
| 2 | Guardrails input | `Node 2 — Guardrails Input Check` |
| 3 | IF pass/fail | `Node 3 — Pass / Reject Router` |
| — | Reject response | `Node 3b — Reject Response` |
| 4 | Information Extractor | `Node 4 — Extract listing (LLM)` + `Gemini Chat Model — Extractor` |
| — | Parse extraction | `Node 4b — Parse extracted JSON` |
| 5 | AI Agent + tools | `Node 5 — AI Agent` + `Gemini Chat Model — Agent` |
| — | RAG tool | `rag_query` → `:8002/query` |
| — | Image tool | `analyse_images` → `:8003/analyse` |
| — | LangGraph tool | `langgraph_agent` → `:8004/agent/run` |
| 6 | LLM Chain + parser | `Node 6 — Final Report LLM Chain` + `Gemini Chat Model — Report` |
| — | Parse report | `Node 6c — Parse report JSON` |
| 7 | Guardrails output | `Node 7 — Guardrails Output Check` |
| — | Output router | `Node 7b — Output Pass / Flag Router` |
| — | Human review | `Node 7c — Human Review Webhook`, `Node 7d — Respond human review pending` |
| 8 | Router | `Node 8 — Property Type Router` |
| — | Responses | `Node 8a — Residential Response`, commercial branch nodes |

## Request body (from WebUI)

```json
{
  "description": "Property text...",
  "image_urls": ["https://example.com/kitchen.jpg"],
  "agent_name": "Agent Name"
}
```

## Prompts

System prompts for LLM nodes: `code/n8n/prompts/`

## Import / export

1. **Import:** n8n UI → Workflows → Import → `AI_Property_Triage_n8n.json`
2. **Export:** after editing nodes, export workflow and overwrite `AI_Property_Triage_n8n.json` in the repo
