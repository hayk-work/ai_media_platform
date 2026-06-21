# Infrastructure

CloudFormation templates for the AWS network foundation (Sprint 03) and ECS API
(Sprint 04), S3 uploads (Sprint 05), and async workers (Sprint 06).

## Layout

```text
infrastructure/
  master.yaml        Nested stack orchestration (network foundation)
  network.yaml       VPC, subnets, routing, NAT gateway
  security.yaml      Security groups for ALB, ECS, RDS
  iam.yaml           ECS task execution and application roles
  outputs.yaml       Output contract for the network stack
  api-master.yaml    Nested stack orchestration (ECS API)
  ecr.yaml           ECR repository for the API image
  rds.yaml           PostgreSQL metadata database
  ecs-api.yaml       ECS Fargate service, ALB, CloudWatch Logs
  s3.yaml            Private media upload bucket and API IAM policy
  processing.yaml    EventBridge rule, SQS queue, DLQ, worker IAM policy
  ecs-worker.yaml    ECS Fargate worker service and CloudWatch Logs
  monitoring.yaml    CloudWatch log groups, metrics alarms, and SNS hooks
  cloudtrail.yaml    CloudTrail audit trail and private audit S3 bucket
  api-outputs.yaml   Output contract for the API stack
  scripts/
    deploy.sh        Package nested templates to S3 and deploy network stack
    deploy-api.sh    Build/push API image and deploy ECS stack
  tests/
    test_cloudformation.py
```

## Architecture

```text
Internet
   |
   v
Public subnets (ALB, NAT)
   |
   v
Private subnets (ECS API, ECS worker, RDS)
```

- **Public subnets** expose only the ALB and NAT gateway.
- **Private subnets** run ECS tasks and RDS without direct internet ingress.
- **Security groups** restrict traffic between ALB → API → RDS.

## Deploy

Prerequisites:

- AWS CLI configured
- S3 bucket for packaging nested templates

```bash
export DEPLOY_BUCKET=your-cfn-artifacts-bucket
export STACK_NAME=ai-media-platform-network
export ENVIRONMENT_NAME=ai-media-platform

./infrastructure/scripts/deploy.sh
```

Verify outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name ai-media-platform-network \
  --query 'Stacks[0].Outputs'
```

## Validate locally

```bash
pytest infrastructure/tests
aws cloudformation validate-template --template-body file://infrastructure/network.yaml
```

## Exported outputs

Downstream stacks (ECS, RDS, S3) consume exports listed in `outputs.yaml`, including:

- `VpcId`
- `PublicSubnetIds` / `PrivateSubnetIds`
- `AlbSecurityGroupId`, `ApiServiceSecurityGroupId`, `WorkerServiceSecurityGroupId`, `RdsSecurityGroupId`
- `EcsTaskExecutionRoleArn`, `EcsApiTaskRoleArn`, `EcsWorkerTaskRoleArn`

## Deploy API stack (Sprint 04)

Requires the network stack to be deployed first.

```bash
export DEPLOY_BUCKET=your-cfn-artifacts-bucket
export STACK_NAME=ai-media-platform-api
export ENVIRONMENT_NAME=ai-media-platform

./infrastructure/scripts/deploy-api.sh
```

The script builds and pushes the API and worker Docker images to ECR, deploys RDS,
S3, EventBridge/SQS processing, ECS API, and ECS worker, then waits for services
to stabilize and runs a health check against the ALB.

## Async processing (Sprint 06)

S3 `Object Created` events on `uploads/` flow through EventBridge into an SQS
queue. The ECS worker consumes messages, generates thumbnails, writes outputs to
`thumbnails/`, and updates PostgreSQL status (`UPLOADING` → `PROCESSING` →
`COMPLETED`).

API stack exports are listed in `api-outputs.yaml`, including:

- `ApiLoadBalancerUrl`
- `ApiRepositoryUri`
- `DbEndpoint`
- `ApiLogGroupName`
- `MediaBucketName` / `MediaBucketArn`
- `ProcessingQueueUrl`
- `WorkerLogGroupName`

## Monitoring and security (Sprint 10)

CloudWatch and CloudTrail provide two complementary views of the platform:

- **CloudWatch** answers operational questions: queue backlog, API 5xx errors,
  RDS pressure, and application log streams in `/ecs/api`, `/ecs/worker`, and
  `/aws/events/media-platform`.
- **CloudTrail** answers audit questions: who changed ECS services, IAM
  policies, S3 buckets, or RDS instances.

The monitoring stack creates CloudWatch alarms for:

- SQS visible message backlog
- Oldest SQS message age
- API target 5xx responses
- RDS CPU utilization and connection count

Alarms optionally publish to the processing notification SNS topic.

The CloudTrail stack creates a private audit bucket and enables management event
logging with log file validation.

Structured application logs include:

- `upload_requested`, `presigned_url_generated`
- `sqs_message_received`, `processing_started`, `processing_failed`
- `ai_workflow_started`, `ai_workflow_completed`
- `sns_notification_published`

Verify CloudWatch after deploy:

```bash
aws logs describe-log-groups --log-group-name-prefix /ecs/
aws cloudwatch describe-alarms --alarm-name-prefix ai-media-platform-
```

Verify CloudTrail after the network stack deploy:

```bash
aws cloudtrail describe-trails --trail-name-list ai-media-platform-audit-trail
aws cloudtrail get-trail-status --name ai-media-platform-audit-trail
```

Example CloudTrail investigation questions:

- Who changed ECS? Search event history for `UpdateService` on `ecs.amazonaws.com`.
- Who changed IAM permissions? Search for `AttachRolePolicy` on `iam.amazonaws.com`.
- Who deleted storage or database resources? Search for `DeleteBucket` or
  `DeleteDBInstance`.
