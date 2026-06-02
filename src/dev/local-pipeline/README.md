# Local pipeline (development only)

Optional substitute for **Layer 2 n8n** during local testing. Production submissions must use the n8n webhook.

```powershell
uvicorn pipeline:app --host 127.0.0.1 --port 8090
```

Requires EC2 services (or mocks) on ports 8001–8004. WebUI: `USE_LOCAL_PIPELINE=true` in `code/webui/.env`.
