# Layer 1 — WebUI (Streamlit + Ollama)

User interface for the AI Property Triage System.

**Full documentation:** [README.md](../../README.md) · **Run guide:** [docs/GETTING_STARTED.md](../../docs/GETTING_STARTED.md)

## Files

| File | Role |
|------|------|
| `app.py` | Streamlit app — two tabs |
| `config.py` | Loads `.env` |
| `ollama_client.py` | Assistant tab → Ollama |
| `n8n_client.py` | Submit tab → n8n webhook |
| `report_view.py` | Triage report rendering |
| `prompts/ollama_system.txt` | System prompt (Surface 5) |
| `samples/listings.json` | Demo listings |

## Run

```powershell
# From repo root (recommended)
..\..\scripts\start-services.ps1
..\..\scripts\start-webui.ps1
```

Or manually:

```powershell
cd code\webui
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run app.py
```

Open: http://localhost:8501

## Tabs

| Tab | Backend |
|-----|---------|
| **Assistant** | Ollama only (not n8n) |
| **Submit listing** | `AI_Property_Triage_n8n.json` via `N8N_WEBHOOK_URL` |

## `.env`

| Variable | Recommended value |
|----------|-------------------|
| `N8N_WEBHOOK_URL` | `http://localhost:5678/webhook/property-triage` |
| `USE_LOCAL_PIPELINE` | `false` (use `true` only with `start-all.ps1`) |

## Demo samples

`samples/listings.json`: Success · Spam · FAIL_OUTPUT · Commercial

## Links

- n8n workflow: [../n8n/AI_Property_Triage_n8n.json](../n8n/AI_Property_Triage_n8n.json)
- n8n docs: [../n8n/README.md](../n8n/README.md)
