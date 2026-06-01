# n8n.cloud setup — step by step (Partner A)

**Local Docker?** Start with **[docs/GETTING_STARTED.md](../../docs/GETTING_STARTED.md)** and **[SETUP-n8n-docker.md](./SETUP-n8n-docker.md)**.  
**Workflow file:** `AI_Property_Triage_n8n.json` · webhook path: `property-triage`

Do this after local E2E works (`.\scripts\verify-setup.ps1`).

## 1. Account and import

1. Open https://n8n.cloud and sign in.
2. **Workflows** → **Add workflow** → **Import from file**.
3. Select `code/n8n/AI_Property_Triage_n8n.json`.
4. Confirm node names match `NODE_MAP.md`.

## 2. Environment variables

**Settings** (gear) → **Variables** → add:

| Variable | Example (local + ngrok) |
|----------|-------------------------|
| `GUARDRAILS_URL` | `https://xxxx.ngrok-free.app` mapped to :8001 |
| `RAG_URL` | tunnel :8002 |
| `IMAGE_URL` | tunnel :8003 |
| `LANGGRAPH_URL` | tunnel :8004 |
| `RESIDENTIAL_TEAM_WEBHOOK_URL` | optional |
| `COMMERCIAL_TEAM_WEBHOOK_URL` | optional |

Copy template from `env.template.txt`.

### Expose local services to n8n.cloud

n8n.cloud cannot reach `127.0.0.1`. Options:

- **ngrok:** `ngrok http 8001` (repeat or config file for 8001–8004)
- **Partner EC2:** use public IPs after deploy

Start services first:

```powershell
.\scripts\start-services.ps1
```

## 3. Webhook URL

1. Open node **1 Webhook Trigger**.
2. **Listen for test event** or copy **Production URL**.
3. Path must be `property-triage` (POST).

Paste into `code/webui/.env`:

```
N8N_WEBHOOK_URL=https://YOUR.app.n8n.cloud/webhook/property-triage
USE_LOCAL_PIPELINE=false
```

## 4. Activate and test

1. Toggle workflow **Active**.
2. Run from WebUI **Submit listing** or:

```powershell
$body = @{
  description = "Bright 3-bedroom apartment in Tel Aviv, 95 sqm, parking. 2,750,000 ILS."
  image_urls = @("https://example.com/kitchen.jpg")
  agent_name = "Jane Cohen"
} | ConvertTo-Json
Invoke-RestMethod -Uri "https://YOUR.app.n8n.cloud/webhook/property-triage" -Method POST -Body $body -ContentType "application/json"
```

3. In n8n **Executions**, confirm green run and nodes 2→8.

## 5. Production upgrade (for full grade)

In `AI_Property_Triage_n8n.json`:

- Node 4 → Information Extractor + Gemini
- Node 5 → AI Agent + HTTP tools
- Node 6 → LLM Chain + Structured Output Parser

Paste prompts from `code/n8n/prompts/`.

Re-export workflow as `AI_Property_Triage_n8n.json` for ZIP submission.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| HTTP node timeout | Check ngrok/EC2 URL; security group |
| `pass` undefined | Guardrails response must include `"pass": true/false` |
| Webhook 404 | Workflow not active; wrong Production URL |
| Empty images | Send `image_urls` as JSON array |
