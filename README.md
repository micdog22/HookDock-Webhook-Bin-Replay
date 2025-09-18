# HookDock — Webhook Bin + Replay (FastAPI + SQLite)

HookDock é um mini RequestBin self‑hosted para capturar, inspecionar e reexecutar webhooks.
Recursos: criação de bins, coleta de qualquer método HTTP, painel com detalhes e **replay** para uma URL alvo.

## Instalação (local)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```
Acesse: `http://localhost:9000`

## Docker
```bash
docker compose up --build
```

## API & Painel
- Criar bin: `POST /api/bins`
- Coletar: `ANY /i/{bin_id}`
- Listar eventos: `GET /api/bins/{bin_id}/events`
- Replay: `POST /api/events/{event_id}/replay`

Veja mais no código e em `/docs`.
