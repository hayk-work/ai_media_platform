# Sprint 05 - Async Processing

## Portfolio context

Turn uploads into an event-driven processing pipeline. When S3 receives a new
object, the platform should create a background job instead of making users wait
for image processing, thumbnail generation, metadata extraction, or AI analysis.

This sprint demonstrates the natural use of EventBridge, SQS, ECS workers, IAM,
CloudWatch Logs, and database status updates.

## User story

As a user, I want my uploaded media to process in the background so I can leave
the upload page and return later when results are ready.

## Architecture focus

```text
S3 ObjectCreated Event
   |
   v
EventBridge Rule
   |
   v
SQS Processing Queue
   |
   v
ECS Fargate Worker
   |
   +--> Download original from S3
   +--> Create thumbnail / extract metadata
   +--> Upload processed output to S3
   +--> Update PostgreSQL status
```

## Build scope

- Enable S3 object-created events through EventBridge.
- Create an EventBridge rule for upload events.
- Create an SQS processing queue.
- Add a dead-letter queue for failed jobs.
- Create an ECS worker task definition and service.
- Give the worker task role least-privilege access to:
  - read original S3 objects
  - write thumbnails or processed outputs
  - consume and delete SQS messages
  - update PostgreSQL records
- Implement worker behavior:
  - receive SQS message
  - parse S3 object key
  - set media status to `PROCESSING`
  - process the file
  - write thumbnail/result keys
  - set status to `COMPLETED` or `FAILED`
- Add idempotency so duplicate S3/SQS events do not corrupt records.
- Add structured logs for each job.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| EventBridge | Routes S3 events into the application pipeline. |
| SQS | Buffers processing jobs and decouples S3 from workers. |
| ECS Fargate | Runs long-lived worker containers. |
| S3 | Source files and processed outputs. |
| RDS PostgreSQL | Tracks job status and output locations. |
| CloudWatch Logs | Captures worker processing logs. |

## Acceptance checks

- Uploading a file to S3 creates an SQS message.
- Worker consumes the message.
- Media status changes from `UPLOADING` to `PROCESSING`.
- Thumbnail or processed output is written to S3.
- Media status changes to `COMPLETED`.
- Failed jobs move toward retry or DLQ behavior.

## Portfolio proof

Show:

- EventBridge rule
- SQS queue receiving messages
- ECS worker logs for one processed file
- database status transition
- generated thumbnail or processed output in S3

## Result

The platform now has a real asynchronous processing pipeline that can scale
workers independently from the API.
