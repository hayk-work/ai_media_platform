# Sprint 10 - Kinesis Analytics

## Portfolio context

Add real-time analytics as the optional but impressive final layer. Every user
action and processing milestone can emit an event to Kinesis Data Streams so the
platform can track usage and performance like a real product.

This sprint demonstrates streaming architecture, event producers, consumers,
shards, analytics dashboards, and separation between transactional data
PostgreSQL and event data Kinesis.

## User story

As a product owner, I want to see real-time upload and processing analytics so I
can understand how users interact with the platform and whether workers are
keeping up.

## Architecture focus

```text
ECS API
   |
   +--> Kinesis Data Stream

ECS Worker
   |
   +--> Kinesis Data Stream

Kinesis Consumer
   |
   +--> Analytics storage or dashboard
```

Example event:

```json
{
  "user_id": "user_123",
  "media_id": "media_456",
  "action": "UPLOAD_COMPLETED",
  "timestamp": "2026-06-19T10:00:00Z",
  "processing_ms": 18420
}
```

## Build scope

- Create a Kinesis Data Stream.
- Define event types:
  - `UPLOAD_REQUESTED`
  - `UPLOAD_COMPLETED`
  - `PROCESSING_STARTED`
  - `AI_ANALYSIS_STARTED`
  - `AI_ANALYSIS_COMPLETED`
  - `PROCESSING_COMPLETED`
  - `PROCESSING_FAILED`
  - `MEDIA_VIEWED`
- Add event producers:
  - API emits upload and media-view events.
  - Worker emits processing and AI workflow events.
- Choose a partition key:
  - `user_id` for user activity analytics
  - or `media_id` for per-media processing order
- Add a consumer service that reads from Kinesis and aggregates:
  - uploads per hour/day
  - processing success/failure rate
  - average processing time
  - AI analysis duration
  - most active users
- Store aggregates in PostgreSQL or a separate analytics table.
- Add a simple dashboard endpoint or frontend page for analytics.
- Add CloudWatch metrics/alarms for stream write/read errors.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| Kinesis Data Streams | Real-time event ingestion. |
| Shards | Controls stream throughput and partitioning. |
| ECS Fargate | API, worker, and consumer services produce/read events. |
| CloudWatch | Monitors stream and consumer errors. |
| IAM | Producers and consumers have scoped stream permissions. |
| RDS PostgreSQL | Stores analytics aggregates if needed. |

## Acceptance checks

- API can write an upload event to Kinesis.
- Worker can write processing events to Kinesis.
- Consumer can read records from the stream.
- Aggregated analytics are visible through an endpoint or dashboard.
- CloudWatch shows Kinesis stream metrics.
- IAM policies restrict Kinesis access to required actions.

## Portfolio proof

Show:

- Kinesis stream with incoming records
- example event JSON
- analytics dashboard or API response
- CloudWatch Kinesis metrics
- explanation of why event streams are separate from PostgreSQL transactions

## Result

The platform includes a real-time analytics layer that demonstrates streaming
architecture in addition to the core upload, processing, AI, and notification
system.
