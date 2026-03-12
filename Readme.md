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
# Scrapi (Apify-like) — Complete Production Research & Build Blueprint

## 1) Executive summary
You can absolutely build a complete, production-grade Apify-like platform called **Scrapi** from scratch without any Apify modules. The right strategy is to:
- Build a strong **Actor runtime + platform APIs** first.
- Implement **durable queueing + autoscaling + sandboxing** as core primitives.
- Provide a first-class developer UX via CLI (`scrapi init/push/run/logs`) and SDKs.
- Roll out in phases from MVP to enterprise/multi-region.

This document provides a complete feature map, architecture, API design, queue model, sandbox execution model, and delivery roadmap.

---

## 2) What Apify offers today (feature research baseline)
To build a close equivalent, Scrapi should cover these capability areas end-to-end:

### A) Compute model: Actors
- User code packaged and executed as isolated jobs (containers).
- Versioned builds, environment configs, secrets, schedules.
- Run lifecycle states, retries, logs, timeout handling.

### B) Data primitives
- **Dataset**: append/list/export structured items.
- **Key-value store**: named records, checkpoints, INPUT/OUTPUT patterns.
- **Request queue**: URL/task queue with dedupe + reclaim + retries.

### C) Automation/orchestration
- Scheduling (cron/time-based), webhooks, API triggers.
- Integrations and event-driven workflows.

### D) Developer tooling
- CLI for scaffold, deploy (`push`), run, logs, storage access.
- API clients/SDKs and local development loop.

### E) Platform and operations
- Team/org permissions, tokens, usage metering, billing.
- Observability, reliability, anti-abuse, and scaling.

Scrapi should mirror this model but with your own implementations.

---

## 3) Product scope for Scrapi v1 → v3

### v1 (MVP)
- Actor deployment and remote execution.
- Request queue + dataset + key-value storage.
- CLI with `init/login/push/run/logs`.
- Basic scheduler and webhook callbacks.

### v2 (production)
- Robust retries/DLQ/priority queues.
- Team RBAC, usage limits, billing metering.
- Strong observability, audit trails, and security controls.

### v3 (scale/enterprise)
- Multi-region workers, dedicated tenant pools.
- Event streaming backbone, advanced anti-bot/browser features.
- Compliance controls and enterprise governance.

---

## 4) Full feature parity checklist (Scrapi target)

## 4.1 Actors (core unit)
- Create actor metadata (name, description, tags, version policy).
- Build from uploaded source tarball or git ref.
- Immutable build artifacts (OCI digest), mutable aliases (`latest`, `prod`).
- Runtime profiles (CPU, memory, timeout, max retries, ephemeral disk).
- Environment variables and secret references.
- Optional web UI input schema per actor.

## 4.2 Actor runs
- Run states: `CREATED → QUEUED → STARTING → RUNNING → SUCCEEDED|FAILED|TIMED_OUT|ABORTED`.
- Sync run (wait for completion) and async run.
- Abort, reboot, and retry semantics.
- Streaming logs and structured events.
- Exit-code capture and failure classification.

## 4.3 Storage primitives
- **Dataset API**
  - `pushItems`, pagination, filtering, sorting, export (JSON/CSV/NDJSON/Parquet).
- **Key-Value API**
  - Put/get/delete records, metadata (content-type, etag), binary support.
- **Request Queue API**
  - Add requests, unique-key dedupe, lease/reclaim, mark handled, requeue.

## 4.4 Scheduling and triggers
- Cron schedules with timezone support.
- One-off delayed runs (`runAt`).
- Webhook trigger ingestion.
- Event triggers from run status changes.

## 4.5 Integrations and API
- REST API for all control/data primitives.
- Webhooks with signatures + replay-safe IDs.
- API tokens and scoped keys.

## 4.6 Console/UI
- Dashboard: run list, health, logs, storage browser.
- Actor build/run pages with input forms and environment controls.
- Team management, audit logs, billing usage views.

## 4.7 Enterprise controls
- RBAC, SSO/OIDC/SAML.
- Quotas and spend limits.
- Dedicated worker pools and region pinning.

---

## 5) How Actors should work in Scrapi (deep-dive)

## 5.1 Actor package contract
Each actor project includes:
- `scrapi.yaml` (name, runtime, entrypoint, default memory/timeout, input schema path).
- Source files (JS/Python/other runtime).
- Optional `Dockerfile` (advanced mode) or managed buildpack mode.
- `.scrapiignore` for package exclusions.

Example `scrapi.yaml` fields:
- `name`, `version`, `runtime`, `entrypoint`
- `build.strategy` (`buildpack|dockerfile`)
- `resources.cpu`, `resources.memoryMb`, `resources.timeoutSec`
- `storages.defaultDataset`, `storages.defaultKv`, `storages.defaultQueue`

## 5.2 Build pipeline
1. CLI packages source and uploads to Build Service.
2. Build Service creates container image and scans vulnerabilities.
3. Image pushed to private registry.
4. Build record stored (digest, SBOM, scan result).
5. Actor version points to build digest.

## 5.3 Run execution
1. Run requested via API/CLI/schedule.
2. Orchestrator validates quotas and enqueues run.
3. Worker scheduler starts container on Kubernetes.
4. Runtime injects env + ephemeral creds + storage endpoints.
5. Logs/events streamed to log pipeline.
6. On completion, finalize status and webhook notifications.

---

## 6) Commands and developer workflow (Apify-like UX)

### 6.1 Core CLI commands
- `scrapi init`
  - Scaffolds project, runtime template, starter scraper.
- `scrapi login`
  - Stores API key in secure local config.
- `scrapi push`
  - Packages, uploads, builds image, registers actor version.
- `scrapi run`
  - Runs local (docker) or cloud execution.
- `scrapi call <actor>`
  - One-shot remote run and return output.
- `scrapi logs <run-id>`
  - Follow live logs.
- `scrapi datasets get <id>` / `scrapi kv get <store>/<key>`
  - Data retrieval utilities.
- `scrapi queue add/fetch/ack`
  - Queue operations for debugging/ops.

### 6.2 `scrapi push` detailed flow
1. Validate `scrapi.yaml` and auth context.
2. Resolve ignore rules and create deterministic archive.
3. Upload archive with checksum.
4. Trigger remote build and stream progress.
5. Save actor version metadata and alias mapping.
6. Print run command and dashboard URL.

### 6.3 Local developer loop
- `scrapi dev`: hot-reload style local runner + local storages.
- `scrapi run --local`: execute inside local Docker for parity.
- `scrapi test`: validates actor input schema and smoke run.

---

## 7) Scraper flow architecture (end-to-end)

Typical web-scraping run:
1. User triggers actor run with input (seed URLs, concurrency, proxy settings).
2. Actor seeds Request Queue with normalized URLs and unique keys.
3. Worker pulls next request (lease acquired).
4. Fetch layer executes HTTP/browser request with retries and anti-block policies.
5. Parser extracts entities.
6. Entities appended to Dataset; checkpoints saved in KV.
7. New discovered links enqueued with dedupe.
8. Completion when queue drained and in-flight jobs reach zero.
9. Export output and notify via webhook.

This pattern should be runtime-agnostic so users can build API scrapers, browser scrapers, and ETL-style crawlers.

---

## 8) Queueing system redesign (production-grade)

## 8.1 Queue requirements
- At-least-once delivery, idempotent consumer design.
- Visibility timeout with lease extension heartbeats.
- Dedupe with `uniqueKey`.
- Priorities, delayed messages, dead-letter queues.
- Tenant and actor-level fairness.

## 8.2 Queue data model
Fields per request:
- `requestId`, `queueId`, `tenantId`, `actorId`
- `url`, `method`, `headersHash`, `payloadHash`
- `uniqueKey`, `priority`, `attempt`
- `notBefore`, `leaseOwner`, `leaseUntil`
- `status` (`PENDING|LEASED|DONE|FAILED|DLQ`)
- `createdAt`, `updatedAt`

## 8.3 Queue operations
- `addRequests(batch)` with dedupe result (`added|alreadyPresent`).
- `fetchNext(limit, leaseSec, strategy=fair|priority)`.
- `extendLease(requestId, leaseSec)`.
- `ack(requestId)` and `nack(requestId, delaySec)`.
- `reclaimExpiredLeases()` background process.
- `moveToDlq(requestId, reason)` on max-attempt breach.

## 8.4 Implementation path
- MVP: Postgres for durable metadata + Redis for lease-speed primitives.
- Scale path: Kafka/Pulsar events + state store + Redis hot index.
- Keep queue API stable to allow backend swap.

## 8.5 Backpressure and autoscaling
- Cap in-flight requests per actor and tenant.
- KEDA scales workers using queue lag and run backlog.
- Circuit-breaker policies for repeated domain failures.

---

## 9) API design blueprint

### 9.1 Public REST domains
- `/v1/actors` — create/list/update actors and versions.
- `/v1/runs` — start/stop/get runs, stream logs.
- `/v1/datasets` — push/list/export items.
- `/v1/key-value-stores` — record CRUD.
- `/v1/request-queues` — add/fetch/ack/nack requests.
- `/v1/schedules` — cron schedules.
- `/v1/webhooks` — webhook subscriptions.
- `/v1/teams`, `/v1/tokens`, `/v1/billing`.

### 9.2 Internal APIs
- gRPC for orchestrator ↔ worker supervisor ↔ storage services.
- Event schema for run lifecycle and billing metering events.

### 9.3 API quality
- Idempotency keys for mutating requests.
- Cursor pagination for large collections.
- Rate limits and clear error taxonomy.

---

## 10) Container sandbox and code execution model

## 10.1 Isolation model
- Every run executes in its own container/pod.
- Non-root user, read-only root filesystem.
- Seccomp/AppArmor profiles enforced.
- CPU/memory/timeouts hard-enforced by K8s limits.

## 10.2 Network and security controls
- Default-deny egress with optional domain/IP allowlists.
- Block access to cloud metadata endpoints (SSRF defense).
- Per-run short-lived credentials for storage APIs.
- Secret retrieval via external secret manager.

## 10.3 Runtime support
- Managed Node.js and Python runtimes first.
- Optional custom Docker image mode for advanced users.
- Optional browser-enabled worker class for Playwright/Puppeteer use cases.

## 10.4 Safe code execution guardrails
- Max open files/process limits (ulimit/cgroups).
- Output/log size caps.
- Sandbox cleanup and artifact retention policies.

---

## 11) Recommended technology stack

### Backend
- Go for orchestration/platform services.
- gRPC internally, REST publicly.

### Frontend
- Next.js + TypeScript + Tailwind + TanStack Query.

### Datastores
- PostgreSQL (core metadata/transactions).
- Redis (leases/cache/rate limiting).
- S3-compatible object storage (artifacts/exports).
- ClickHouse (analytics/log-index at scale).

### Runtime/infra
- Kubernetes + KEDA/HPA autoscaling.
- Private container registry.
- Terraform + GitOps (ArgoCD/Flux).

### Observability
- OpenTelemetry, Prometheus, Grafana, Loki, Tempo/Jaeger.

---

## 12) Multi-tenant scaling architecture

## 12.1 Control plane vs data plane
- **Control plane**: API gateway, auth, actor registry, run orchestrator, billing.
- **Data plane**: worker pools, queue execution, data write services.

## 12.2 Tenant isolation levels
- Shared pool (startup) with strict quotas.
- Pool-per-tier (growth).
- Dedicated pool/cluster (enterprise).

## 12.3 Multi-region evolution
- Stage 1: single region + backups.
- Stage 2: active/passive failover.
- Stage 3: region-local execution + global routing.

---

## 13) Reliability, SRE, and security baseline
- SLOs: API availability, queue delay, run success, webhook delivery.
- Retry standards: exponential backoff + jitter everywhere.
- DR: Postgres PITR, object versioning, queue replay strategy.
- Security: audit logs, signed images, SBOM, vulnerability gating.
- Governance: policy checks before run start (quota, domain restrictions, legal flags).

---

## 14) Suggested implementation plan

### Phase 1 (6–8 weeks)
- Actor registry, build service, run orchestrator.
- Request queue v1 + dataset + KV storage.
- CLI (`init/login/push/run/logs`) and basic dashboard.

### Phase 2 (8–12 weeks)
- Scheduler, webhooks, RBAC, billing metering.
- Hardened sandbox and observability stack.
- Autoscaling and improved queue fairness.

### Phase 3 (12+ weeks)
- Kafka-backed event pipeline and advanced analytics.
- Multi-region worker execution.
- Enterprise controls and dedicated tenancy.

---

## 15) Practical “from scratch” recommendation
If your target is a close Apify-style platform quickly:
1. Start with **Go + Postgres + Redis + K8s**.
2. Implement **Actors + Runs + Request Queue + Dataset/KV** before advanced features.
3. Ship **`scrapi push`** early to lock dev UX and reduce friction.
4. Build sandbox security and observability as first-class requirements.
5. Keep queue/storage interfaces abstract for painless backend evolution.

With this plan, Scrapi can reach production quality while keeping a clear path to high throughput and enterprise scale.
