# Sprint 07 - AI Processing with LangChain and LangGraph

## Portfolio context

Add the AI layer that makes the project stand out. The worker should not only
resize images; it should run an AI analysis workflow that can describe media,
extract tags, detect quality issues, and produce searchable metadata.

LangChain and LangGraph fit naturally here because the media processing job can
be modeled as a multi-step workflow with clear nodes, retries, and stored
results.

**Scope for this sprint:** images only. Video analysis is a future enhancement.

## User story

As a user, I want the platform to analyze my uploaded image and return useful
AI-generated metadata such as captions, tags, and content summaries that I can
search and filter later.

## Architecture focus

```text
ECS Worker
   |
   +--> Basic image processing (thumbnail)
   |
   +--> LangGraph workflow (Groq vision model)
          |
          +--> load_context
          +--> prepare_prompt
          +--> analyze_image
          +--> extract_tags
          +--> safety_check
          +--> validate_result
          +--> persist_ai_result
   |
   v
PostgreSQL (media_ai_results)
   |
   v
API (/media, /media?tag=...)
```

## AI provider strategy

| Provider | When to use | Notes |
| --- | --- | --- |
| **Groq** (default) | Local dev and portfolio demos | Free tier, fast inference. Requires a vision-capable model. |
| **Mock** (`AI_MOCK_MODE=true`) | Tests and CI | No external API calls; returns deterministic sample metadata. |
| **Bedrock** (optional later) | AWS-native deploy story | `langchain-aws` is already a dependency; not required for Sprint 07. |

**Not in scope:** Pinecone (vector DB) and Tavily (web search). PostgreSQL
stores captions/tags and supports basic tag filtering without extra services.

## Environment variables

Add to `.env` (never commit real keys):

```bash
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
AI_MOCK_MODE=false
```

- `GROQ_API_KEY` — required for live AI analysis (worker reads this).
- `GROQ_MODEL` — must be a Groq model that supports image input.
- `AI_MOCK_MODE` — when `true`, skip Groq and use stubbed AI output.

## Build scope

- Add LangChain + LangGraph integration for AI model calls (Groq via
  `langchain-groq`).
- Add a LangGraph workflow for image analysis with structured Pydantic output:
  - `caption`
  - `tags`
  - `labels`
  - `quality_issues`
  - `is_safe`
- Define workflow nodes:
  - load media metadata and image bytes
  - prepare prompt/context
  - analyze image (caption + labels)
  - extract/normalize tags
  - safety/quality check
  - validate result shape
  - persist AI results
- Add a `media_ai_results` table (separate from thumbnail `metadata_json`):
  - `media_item_id`
  - `caption`
  - `tags`
  - `labels`
  - `provider` / `model`
  - `status` (`PENDING`, `COMPLETED`, `FAILED`)
  - `error_message`
  - timestamps
- Partial success model:
  - thumbnail success can still mark media `COMPLETED`
  - AI failure sets AI status to `FAILED` without deleting the thumbnail
- Add retry/error handling around AI calls.
- Add worker logs for each LangGraph node (`ai_node`, `duration_ms`, status).
- Extend media API:
  - `GET /media/{id}` returns AI metadata
  - `GET /media?tag=sunset` filters by AI tag (portfolio search demo)
- Keep secrets and model API keys out of source code.

## AWS topics demonstrated

| Topic | Where it appears |
| --- | --- |
| ECS Fargate | Runs longer AI processing jobs better than short Lambda-only flows. |
| SQS | Buffers AI/media processing tasks. |
| S3 | Provides source media and processed artifacts. |
| RDS PostgreSQL | Stores structured AI analysis results. |
| IAM | Worker has only required AWS permissions. |
| CloudWatch Logs | Shows each LangGraph step and failure reason. |

## LangChain/LangGraph value

This sprint proves you can combine cloud architecture with AI orchestration:

- LangChain handles model interaction and structured output parsing.
- LangGraph makes the AI workflow explicit and inspectable.
- ECS workers allow longer processing than typical request/response APIs.
- PostgreSQL stores outputs for search, filtering, and UI display.

## Prerequisites (before coding)

- [x] Sprint 06 async worker pipeline (SQS → thumbnail → PostgreSQL)
- [x] LangChain / LangGraph dependencies in `pyproject.toml`
- [x] `GROQ_API_KEY` and `GROQ_MODEL` in `.env`
- [x] Groq vision model confirmed working with your API key
- [x] `langchain-groq` added to project dependencies

## Acceptance checks

- Worker runs the LangGraph workflow after thumbnail processing (when AI is enabled).
- AI results are saved to `media_ai_results` in PostgreSQL.
- `GET /media/{id}` returns AI metadata (caption, tags, labels, AI status).
- `GET /media?tag=...` returns items matching an AI tag.
- Failed AI calls set AI status to `FAILED` with a useful `error_message`.
- Thumbnail processing can still succeed when AI fails (partial success).
- CloudWatch / structlog output shows workflow start, node progress, and completion.
- Tests pass with `AI_MOCK_MODE=true` without calling Groq.

## Portfolio proof

Show:

- LangGraph workflow diagram (Mermaid in repo or sprint notes)
- example uploaded image
- generated caption/tags in API response
- `media_ai_results` database row
- worker logs showing each LangGraph node
- tag search example (`GET /media?tag=...`)

## Result

Uploaded images now receive AI-generated metadata through a clear LangChain and
LangGraph pipeline running inside ECS workers, powered by Groq for free local
demos and optional mock mode for tests.
