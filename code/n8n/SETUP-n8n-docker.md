# n8n local (Docker Desktop) — setup for Layer 2

**Main run guide:** [docs/GETTING_STARTED.md](../../docs/GETTING_STARTED.md)  
**Workflow file:** `AI_Property_Triage_n8n.json` (workflow name: `AI_Property_Triage`)

You run n8n in Docker (`localhost:5678`). The WebUI runs on the **host**. Layer 3 services run on the **host** (`start-services.ps1`).

## Network diagram

```
[Host Windows]
  Streamlit :8501  ──POST──►  n8n container :5678  (webhook)
  Guardrails  :8001  ◄──HTTP──  n8n HTTP nodes
  RAG         :8002  ◄──HTTP──
  Image       :8003  ◄──HTTP──
  LangGraph   :8004  ◄──HTTP──
  Ollama      :11434 ◄──  WebUI only (not n8n)
```

**Important:** Inside the n8n container, `127.0.0.1` is the container itself — **not** your PC.  
Use **`host.docker.internal`** so n8n reaches services on the host.

## Step 1 — Start Layer 3 on the host

```powershell
cd C:\Users\admin\ai-property-triage
.\scripts\start-services.ps1
.\scripts\verify-setup.ps1
```

You do **not** need `start-pipeline.ps1` when using n8n (that was only a dev substitute).

## Step 2 — Import workflow

1. Open http://localhost:5678
2. **Workflows** → **Import from file** → `code/n8n/AI_Property_Triage_n8n.json`
3. Save

## Step 3 — URLs for HTTP nodes (important)

### You will NOT find "Settings → Variables" in most self-hosted installs

In the n8n docs, **Variables** in the left menu is a **Pro / Cloud** feature.  
Community + Docker uses **`$env.VAR_NAME`** only if you pass those names into the **container environment** when starting n8n — not from the UI.

**n8n 2.19+** blocks `$env` in **Code** nodes (`access to env vars denied`).  
The repo `AI_Property_Triage_n8n.json` uses **hardcoded** `host.docker.internal` URLs — re-import after updates.

Pick **one** method below (or just re-import the JSON).

---

### Method A — Edit URLs inside the workflow (easiest, no Docker restart)

Open each HTTP/Code node and replace `{{ $env.... }}` with full URLs:

| Node | Field | Set URL to |
|------|-------|------------|
| `2 Guardrails Input Check` | URL | `http://host.docker.internal:8001/check/input` |
| `RAG HTTP` | URL | `http://host.docker.internal:8002/query` |
| `Image HTTP` | Code: `const base = ...` | `const base = "http://host.docker.internal:8003";` |
| `7 Guardrails Output Check` | URL | `http://host.docker.internal:8001/check/output` |

Save workflow. **No Variables menu needed.**

---

### Method B — Docker environment variables (for `$env.GUARDRAILS_URL` in JSON)

Stop and recreate the n8n container with `-e` flags (example):

```powershell
docker stop n8n-8
docker rm n8n-8

docker run -d --name n8n `
  -p 5678:5678 `
  -e GUARDRAILS_URL=http://host.docker.internal:8001 `
  -e RAG_URL=http://host.docker.internal:8002 `
  -e IMAGE_URL=http://host.docker.internal:8003 `
  -e LANGGRAPH_URL=http://host.docker.internal:8004 `
  -v n8n_data:/home/node/.n8n `
  docker.n8n.io/n8nio/n8n
```

Use your real container name/volume if different.

**Docker Compose** — under `n8n: environment:`:

```yaml
environment:
  GUARDRAILS_URL: http://host.docker.internal:8001
  RAG_URL: http://host.docker.internal:8002
  IMAGE_URL: http://host.docker.internal:8003
  LANGGRAPH_URL: http://host.docker.internal:8004
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Then restart: `docker compose up -d --force-recreate`

**Verify inside n8n:** open any node expression, type `{{ $env.GUARDRAILS_URL }}` → Execute step → should show the URL string.

## Step 4 — Webhook URL for WebUI

Open node **1 Webhook Trigger**:

| Mode | URL pattern | When |
|------|-------------|------|
| **Test** | `http://localhost:5678/webhook-test/property-triage` | Workflow open + "Listen for test event" |
| **Production** | `http://localhost:5678/webhook/property-triage` | Workflow **Active** (toggle ON) |

Put the URL in `code/webui/.env`:

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/property-triage
USE_LOCAL_PIPELINE=false
```

For quick testing while editing the workflow, use `webhook-test` and click **Listen for test event** before each submit.

## Step 5 — Activate and test

1. Toggle workflow **Active** (for production URL).
2. Test from PowerShell on the **host**:

```powershell
$body = @{
  description = "Bright 3-bedroom apartment in Tel Aviv, 95 sqm, parking. 2,750,000 ILS."
  image_urls = @("https://example.com/kitchen.jpg")
  agent_name = "Jane Cohen"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:5678/webhook/property-triage" `
  -Method POST -Body $body -ContentType "application/json"
```

3. In n8n → **Executions** — check each node is green.
4. Start WebUI: `.\scripts\start-webui.ps1` → **Submit listing** → same payload.

## Troubleshooting (Docker)

| Problem | Cause | Fix |
|---------|--------|-----|
| HTTP node "connection refused" | n8n uses `127.0.0.1:8001` | Use `host.docker.internal` |
| WebUI "Cannot reach webhook" | n8n not running / wrong URL | `docker ps`, fix `.env` URL |
| 404 on webhook | Workflow not active | Activate or use `webhook-test` + Listen |
| `test-demo-scenarios.ps1` fails | Script hits port **8090**, not n8n | Use n8n test above, or start pipeline |
| Empty execution | Variables not set | Add Variables in n8n Settings |

## vs n8n.cloud

Same `AI_Property_Triage_n8n.json`. Only URLs change:

- WebUI → `localhost:5678` instead of `*.app.n8n.cloud`
- n8n → `host.docker.internal` instead of ngrok/EC2 public IP

See also `SETUP.md` for cloud deployment later.
