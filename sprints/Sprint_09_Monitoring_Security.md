# Sprint 09 - Monitoring, Security, CloudWatch, and CloudTrail

## Portfolio context

Make the platform observable and auditable. A production-style AWS project needs
two different kinds of visibility:

- CloudWatch answers: "How is my application and infrastructure behaving?"
- CloudTrail answers: "Who changed something in my AWS account?"

This sprint demonstrates that you understand operations, security, auditing,
least-privilege IAM, and incident investigation.

## User story

As an operator, I want logs, metrics, alarms, and audit trails so I can detect
application problems, scale workers, and investigate AWS account changes.

## Architecture focus

```text
ECS API
   |
   v
CloudWatch Logs

ECS Worker
   |
   v
CloudWatch Logs

SQS / ECS / RDS / ALB
   |
   v
CloudWatch Metrics + Alarms

AWS API Activity
   |
   v
CloudTrail
   |
   v
Audit S3 Bucket
```

## Build scope

### CloudWatch

- Create log groups:
  - `/ecs/api`
  - `/ecs/worker`
  - `/aws/events/media-platform`
- Add structured application logs:
  - upload requested
  - presigned URL generated
  - SQS message received
  - processing started
  - LangGraph workflow started/completed
  - SNS notification published
  - processing failed
- Track key metrics:
  - ECS CPU and memory
  - API task count
  - worker task count
  - SQS visible messages
  - age of oldest SQS message
  - RDS CPU/connections/storage
  - ALB 5xx errors and target response time
- Create alarms:
  - SQS messages above threshold
  - oldest SQS message too old
  - API 5xx errors too high
  - RDS CPU or connections too high
- Optionally connect alarms to SNS.

### CloudTrail

- Create an audit S3 bucket for CloudTrail logs.
- Enable a CloudTrail trail for management events.
- Record actions such as:
  - `UpdateService` on ECS
  - `DeleteBucket` on S3
  - `AttachRolePolicy` on IAM
  - `DeleteDBInstance` on RDS
- Document how CloudTrail helps answer:
  - who changed ECS?
  - who changed IAM permissions?
  - who deleted or modified storage/database resources?

### Security

- Review IAM least-privilege permissions for API and worker roles.
- Keep S3 buckets private.
- Restrict security group access.
- Store secrets outside source code.
- Add RDS access only from approved ECS security groups.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| CloudWatch Logs | API and worker application logs. |
| CloudWatch Metrics | ECS, SQS, RDS, and ALB health. |
| CloudWatch Alarms | Alert on queue backlog, errors, and database pressure. |
| CloudTrail | Audit AWS API activity and account changes. |
| IAM | Least-privilege API and worker roles. |
| S3 | Audit log storage and private media buckets. |

## Acceptance checks

- API and worker logs appear in CloudWatch.
- SQS and ECS metrics are visible.
- At least one CloudWatch alarm is configured.
- CloudTrail is enabled and writing to an S3 audit bucket.
- IAM roles are scoped to required actions.
- Security groups do not expose RDS publicly.

## Portfolio proof

Show:

- CloudWatch log streams for API and worker
- CloudWatch alarm for SQS backlog
- CloudTrail event history example
- IAM policy snippets for API and worker roles
- explanation of CloudWatch versus CloudTrail

## Result

The platform can be monitored for health, audited for AWS account activity, and
explained as a secure production-style architecture.
