# WebUI — AI Property Triage (Layer 1)

Streamlit app with two tabs:
- **Assistant** — chat with a local Ollama model grounded as a real-estate assistant (§5.1)
- **Submit listing** — form that POSTs to the n8n webhook and displays the returned report (§5.2)

## Prerequisites

1. **Ollama running locally**
   ```
   ollama serve
   ollama pull llama3.1
   ```

2. **n8n webhook URL** — import the n8n flow and copy the webhook URL.

3. **`.env` file** at the project root:
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1
   N8N_WEBHOOK_URL=<your n8n webhook URL>
   REQUEST_TIMEOUT=120
   ```

## Run

From the project root:
```
streamlit run src/webui/app.py
```

Opens at `http://localhost:8501`.
