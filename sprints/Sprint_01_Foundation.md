# Sprint 01 - Foundation

## Portfolio context

Build the base of an AI Media Processing Platform, a mini Google Photos style
project where users upload images or videos, AWS processes them asynchronously,
and users can view generated thumbnails, metadata, and AI analysis results.

This sprint proves that the project is more than a simple CRUD app. It creates
the local application structure that later sprints will deploy to AWS with ECS,
S3, RDS, SQS/SNS, EventBridge, CloudFormation, CloudWatch, CloudTrail,
CloudFront, and optional Kinesis analytics.

## User story

As a user, I want to sign in, create an upload request, and later see my media
items with processing status so the platform feels like a real cloud-backed
product from the beginning.

## Architecture focus

```text
API Client
   |
   v
Backend API
   |
   +--> Local PostgreSQL
   |
   +--> Local worker placeholder
```

## Build scope

- Create the repository structure:
  - `backend/api`
  - `backend/worker`
  - `infrastructure`
  - `sprints`
- Add a backend API skeleton for:
  - health check
  - user/session placeholder
  - upload request placeholder
  - media status placeholder
- Add a worker skeleton that can later consume SQS messages.
- Add a local PostgreSQL database with initial tables:
  - `users`
  - `media_items`
  - `processing_jobs`
- Define media statuses:
  - `UPLOADING`
  - `PROCESSING`
  - `COMPLETED`
  - `FAILED`
- Add Docker support for local API, worker, and database development.
- Add project configuration, linting, formatting, and README instructions.

## AWS topics prepared

| Topic | How this sprint prepares it |
| --- | --- |
| ECS Fargate | API and worker are containerized from the start. |
| RDS PostgreSQL | Local schema mirrors the future RDS schema. |
| S3 | Upload API contract is planned before S3 integration. |
| SQS | Worker entrypoint is ready for async jobs. |
| IAM | Service responsibilities are separated early. |
| CloudFormation | Infrastructure folder is created for later templates. |

## Acceptance checks

- API runs locally.
- Worker runs locally without processing real jobs yet.
- PostgreSQL starts locally and migrations create the base schema.
- `GET /health` returns a successful response.
- README explains how to run the project locally.

## Portfolio proof

Show a screenshot or terminal output of:

- local API health check
- local database tables
- Docker services running
- early architecture diagram

## Result

The platform has a clean local foundation that can grow naturally into a
production-style AWS architecture.

**Next sprint:** [Sprint 02 - Authentication](./Sprint_02_Authentication.md)
replaces the `POST /auth/session` placeholder with register, login, and JWT.
