# AI Media Processing Platform

A mini Google Photos–style platform where users upload images or videos, AWS
processes them asynchronously, and users view thumbnails, metadata, and AI analysis
results.

Sprint 01 establishes the local foundation: API, worker placeholder, PostgreSQL
schema, and Docker-based development. This project is **API-only** — clients use
HTTP (`curl`, Postman, mobile apps, etc.) or the built-in Swagger UI at `/docs`.

## Architecture (Sprint 01)

```text
API clients (curl, Postman, /docs)
   |
   v
Backend API (FastAPI)
   |
   +--> PostgreSQL
   |
   +--> Worker placeholder (future SQS consumer)
```

## Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local development without Docker)

## Quick start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Start all services:

   ```bash
   docker compose up --build
   ```

3. Verify the API health check:

   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:

   ```json
   {"status":"ok","db":"connected"}
   ```

4. Open interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Database tables

After the API starts, Alembic runs migrations automatically. Verify tables:

```bash
docker compose exec db psql -U amp -d ai_media_platform -c '\dt'
```

Expected tables: `users`, `media_items`, `processing_jobs`, `alembic_version`.

PostgreSQL is exposed on host port **5433** (mapped to 5432 inside Docker) to avoid
conflicts with a local PostgreSQL installation.

## API flow (placeholder auth)

1. Create a session:

   ```bash
   curl -X POST http://localhost:8000/auth/session \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com"}'
   ```

2. Create an upload request (use `user_id` from step 1 as the bearer token):

   ```bash
   curl -X POST http://localhost:8000/uploads \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <user_id>" \
     -d '{"filename":"photo.jpg","content_type":"image/jpeg","file_size_bytes":1024}'
   ```

3. List media:

   ```bash
   curl http://localhost:8000/media \
     -H "Authorization: Bearer <user_id>"
   ```

## Media statuses

| Status       | Meaning                          |
| ------------ | -------------------------------- |
| `UPLOADING`  | Upload request created           |
| `PROCESSING` | Background job in progress       |
| `COMPLETED`  | Processing finished successfully |
| `FAILED`     | Processing failed                |

## Project structure

```text
backend/
  api/          FastAPI application and Alembic migrations
  worker/       Async worker placeholder for future SQS jobs
  common/       Shared package (config, models, database, logging)
infrastructure/ CloudFormation placeholder (Sprint 03)
sprints/        Sprint planning documents (see sprints/README.md)
```

## Local development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Start PostgreSQL separately, then:
export DATABASE_URL=postgresql+asyncpg://amp:amp@localhost:5432/ai_media_platform
cd backend/api && alembic upgrade head
uvicorn app.main:app --reload --app-dir backend/api
```

Set `PYTHONPATH=backend:backend/api` when running commands locally (pytest picks
this up automatically from `pyproject.toml`).

## Linting and tests

```bash
ruff check backend
pytest                  # unit tests (mocked DB)
pytest -m integration   # live API tests (requires docker compose up)
```

## What's next

See [sprints/README.md](sprints/README.md) for the full roadmap.

- **Sprint 02**: Authentication (register, login, JWT) — **next up**
- **Sprint 03**: CloudFormation VPC and network
- **Sprint 04**: Deploy API on ECS Fargate
- **Sprint 05**: S3 presigned uploads
- **Sprint 06**: SQS/EventBridge async workers
