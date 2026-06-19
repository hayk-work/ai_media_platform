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

## API flow (authentication)

1. Register a user:

   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com","password":"strong-password-123"}'
   ```

2. Log in and copy the `access_token`:

   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com","password":"strong-password-123"}'
   ```

3. Create an upload request:

   ```bash
   curl -X POST http://localhost:8000/uploads \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <access_token>" \
     -d '{"filename":"photo.jpg","content_type":"image/jpeg","file_size_bytes":1024}'
   ```

4. List media:

   ```bash
   curl http://localhost:8000/media \
     -H "Authorization: Bearer <access_token>"
   ```

5. Log out (invalidates issued tokens server-side):

   ```bash
   curl -X POST http://localhost:8000/auth/logout \
     -H "Authorization: Bearer <access_token>"
   ```

   After logout, discard the token on the client. The same token will no longer work.

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

- **Sprint 02**: Authentication — **done locally**
- **Sprint 03**: CloudFormation VPC and network — **done locally (templates + tests)**
- **Sprint 04**: Deploy API on ECS Fargate — **next up**
- **Sprint 05**: S3 presigned uploads
- **Sprint 06**: SQS/EventBridge async workers
