# Sprint 08 - SNS Notifications

## Portfolio context

Close the loop between background processing and the user. After the worker
finishes image processing and AI analysis, the platform should notify the user
that their media is ready.

This sprint demonstrates SNS as a fan-out notification service and shows how a
backend system communicates results without forcing users to poll forever.

## User story

As a user, I want to receive a notification when my uploaded media has finished
processing so I know when thumbnails and AI analysis are ready.

## Architecture focus

```text
ECS Worker
   |
   | processing completed
   v
SNS Topic
   |
   +--> Email subscription
   +--> SMS/mobile subscription placeholder
   +--> Future notification service
```

## Build scope

- Create an SNS topic for processing notifications.
- Add SNS subscription support for email during the portfolio version.
- Give the worker task role permission to publish to the topic.
- Publish an event when processing completes:

```json
{
  "media_id": "media_123",
  "user_id": "user_456",
  "status": "COMPLETED",
  "message": "Your image is ready"
}
```

- Publish a different notification for failed processing if useful.
- Store notification status in PostgreSQL:
  - `PENDING`
  - `SENT`
  - `FAILED`
- Add API support for user notification preferences (requires Sprint 02 JWT auth).
- Add CloudWatch logs for publish attempts and failures.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| SNS | Sends completion notifications. |
| IAM | Worker can publish only to the required topic. |
| ECS Fargate | Worker triggers notification after processing. |
| RDS PostgreSQL | Tracks notification state and preferences. |
| CloudWatch Logs | Captures publish results and errors. |

## Acceptance checks

- SNS topic is created by CloudFormation.
- Email subscription can be confirmed.
- Worker publishes a message after successful processing.
- User receives an email notification.
- Notification status is stored or logged.
- Failed publish attempts are visible in logs.

## Portfolio proof

Show:

- SNS topic and subscription
- example notification message
- worker log line showing publish success
- email screenshot with "Your image is ready"

## Result

Users can be notified when processing finishes, and the platform demonstrates a
real event-driven completion workflow with SNS.
