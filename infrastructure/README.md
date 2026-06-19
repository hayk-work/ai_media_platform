# Infrastructure

CloudFormation templates for the AWS network foundation (Sprint 03).

## Layout

```text
infrastructure/
  master.yaml      Nested stack orchestration
  network.yaml     VPC, subnets, routing, NAT gateway
  security.yaml    Security groups for ALB, ECS, RDS
  iam.yaml         ECS task execution and application roles
  outputs.yaml     Output contract for later stacks
  scripts/
    deploy.sh      Package nested templates to S3 and deploy
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
