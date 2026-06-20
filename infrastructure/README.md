# Infrastructure

CloudFormation templates for the AWS network foundation (Sprint 03) and ECS API
(Sprint 04) and S3 uploads (Sprint 05).

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

The script builds and pushes the API Docker image to ECR, deploys RDS, S3, and ECS,
waits for the service to stabilize, and runs a health check against the ALB.

## S3 uploads (Sprint 05)

`POST /uploads` creates a PostgreSQL record and returns a presigned S3 URL when
`S3_MEDIA_BUCKET` is configured on the ECS task. The bucket is private, encrypted,
and blocks all public access.

API stack exports are listed in `api-outputs.yaml`, including:

- `ApiLoadBalancerUrl`
- `ApiRepositoryUri`
- `DbEndpoint`
- `ApiLogGroupName`
- `MediaBucketName` / `MediaBucketArn`
