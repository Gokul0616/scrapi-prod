# Scrapi (Apify-like) Starter Platform

This repository contains a runnable, from-scratch Scrapi starter with:
- **FastAPI control plane** for Actors, Runs, Request Queue, Dataset APIs.
- **Celery + Redis workers** for run execution and queue processing (**no Kafka**).
- **Celery Beat scheduler** for cron-based run dispatch (Phase 2).
- **Webhook subscriptions** for run completion callbacks (Phase 2).
- **Usage summary endpoint** for basic metering (Phase 2).
- **Phase 3 queue reliability**: lease timeout, retry backoff, max-attempt failover, and queue stats.
- **Run cancellation + resume APIs/CLI** for operational control.
- **Key-Value store APIs/CLI** for actor-level metadata storage.
- **PostgreSQL** for metadata and storage primitives.
- **CLI** (`scrapi init`, `scrapi push`, `scrapi run`, `scrapi runs`, `scrapi schedule`, `scrapi webhook`, `scrapi resume`, `scrapi cancel`).

## Architecture
- API: `backend/app/main.py`
- API routes: `backend/app/api/routes.py`
- Queue worker/scheduler tasks: `backend/app/workers/tasks.py`
- Data model: `backend/app/db/models.py`
- CLI: `cli/scrapi.py`

## Security
All `/v1/*` endpoints except health require `x-api-key` header.
Default development key: `dev-secret-key`.

## Run with Docker Compose
```bash
docker compose up --build
```

## API checks
```bash
# health (no auth)
curl http://localhost:8000/v1/health

# create actor (with auth)
curl -X POST http://localhost:8000/v1/actors \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-secret-key' \
  -d '{"name":"demo-actor"}'

# create run
curl -X POST http://localhost:8000/v1/runs \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-secret-key' \
  -d '{"actor_id":1,"input_payload":{}}'

# create schedule
curl -X POST http://localhost:8000/v1/schedules \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-secret-key' \
  -d '{"actor_id":1,"cron":"*/5 * * * *","payload":{}}'

# subscribe webhook
curl -X POST http://localhost:8000/v1/webhooks \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-secret-key' \
  -d '{"event_type":"run.finished","target_url":"https://example.com/webhook"}'

# resume a non-terminal run
curl -X POST http://localhost:8000/v1/runs/1/resume \
  -H 'x-api-key: dev-secret-key'

# cancel a run
curl -X POST http://localhost:8000/v1/runs/1/cancel \
  -H 'x-api-key: dev-secret-key'

# queue stats
curl -H 'x-api-key: dev-secret-key' http://localhost:8000/v1/request-queue/1/stats

# upsert key-value record
curl -X PUT http://localhost:8000/v1/key-value \
  -H 'content-type: application/json' \
  -H 'x-api-key: dev-secret-key' \
  -d '{"actor_id":1,"key":"state","value":{"cursor":"page-10"}}'

# fetch key-value record
curl -H 'x-api-key: dev-secret-key' http://localhost:8000/v1/key-value/1/state

# list key-value records for actor
curl -H 'x-api-key: dev-secret-key' http://localhost:8000/v1/key-value/1

# usage summary
curl -H 'x-api-key: dev-secret-key' http://localhost:8000/v1/usage/summary
```

## CLI
```bash
export SCRAPI_API_KEY=dev-secret-key
python cli/scrapi.py init
python cli/scrapi.py push
python cli/scrapi.py run --actor-id 1
python cli/scrapi.py runs
python cli/scrapi.py schedule --actor-id 1 --cron '*/5 * * * *'
python cli/scrapi.py webhook --url 'https://example.com/webhook'
python cli/scrapi.py resume --run-id 1
python cli/scrapi.py queue-stats --run-id 1
python cli/scrapi.py cancel --run-id 1
python cli/scrapi.py kv-set --actor-id 1 --key state --value '{"cursor":"page-10"}'
python cli/scrapi.py kv-get --actor-id 1 --key state
python cli/scrapi.py kv-list --actor-id 1
```

## Notes
- This is a production-oriented **starter foundation** and phase-by-phase implementation.
- Queueing and workers use **Celery + Redis** only.
