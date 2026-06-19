# Sprint 06 - AI Processing with LangChain and LangGraph

## Portfolio context

Add the AI layer that makes the project stand out. The worker should not only
resize images; it should run an AI analysis workflow that can describe media,
extract tags, detect quality issues, and produce searchable metadata.

LangChain and LangGraph fit naturally here because the media processing job can
be modeled as a multi-step workflow with clear nodes, retries, and stored
results.

## User story

As a user, I want the platform to analyze my uploaded image or video and return
useful AI-generated metadata such as captions, tags, and content summaries.

## Architecture focus

```text
ECS Worker
   |
   +--> Basic image processing
   |
   +--> LangGraph workflow
          |
          +--> Load media context
          +--> Generate caption
          +--> Extract tags
          +--> Check safety/quality
          +--> Store AI result
   |
   v
PostgreSQL
```

## Build scope

- Add LangChain integration for AI model calls.
- Add a LangGraph workflow for media analysis.
- Define workflow nodes:
  - load media metadata
  - prepare prompt/context
  - generate description
  - extract tags/categories
  - validate result shape
  - persist AI results
- Add database tables or columns for:
  - caption
  - tags
  - detected objects or labels
  - AI provider/model
  - AI processing status
  - error message
- Store AI output separately from raw upload metadata.
- Add retry/error handling around AI calls.
- Add worker logs for each LangGraph node.
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

- LangChain handles model/tool interaction.
- LangGraph makes the AI workflow explicit and inspectable.
- ECS workers allow longer processing than typical request/response APIs.
- PostgreSQL stores outputs for search, filtering, and UI display.

## Acceptance checks

- Worker runs the LangGraph workflow after a media upload.
- AI results are saved to PostgreSQL.
- Media detail API returns AI metadata.
- Failed AI calls mark the job as `FAILED` or `AI_FAILED` with a useful reason.
- CloudWatch logs show workflow start, node progress, and completion.

## Portfolio proof

Show:

- LangGraph workflow diagram
- example uploaded image
- generated caption/tags
- database row containing AI result
- worker logs showing AI workflow execution

## Result

Uploaded media now receives AI-generated metadata through a clear LangChain and
LangGraph pipeline running inside ECS workers.
