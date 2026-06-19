# Sprint 02 - CloudFormation and AWS Network

## Portfolio context

Move the project from local development toward a real AWS environment by
creating the networking foundation with CloudFormation. The goal is to show that
the platform is designed like a production system, not manually assembled in the
AWS console.

All later services depend on this sprint: ECS Fargate, ALB, RDS, S3 endpoints,
SQS, SNS, EventBridge, CloudWatch, CloudTrail, and CloudFront all need secure
networking and IAM boundaries.

## User story

As a developer, I want to deploy the base AWS network from repeatable templates
so the project can be recreated, reviewed, and extended safely.

## Architecture focus

```text
AWS Account
   |
   v
CloudFormation
   |
   +--> VPC
   +--> Public subnets
   +--> Private subnets
   +--> Route tables
   +--> NAT Gateway
   +--> Security groups
   +--> IAM role foundations
```

## Build scope

- Create CloudFormation template structure:
  - `infrastructure/master.yaml`
  - `infrastructure/network.yaml`
  - `infrastructure/security.yaml`
  - `infrastructure/outputs.yaml` or exported stack outputs
- Create a VPC with multiple Availability Zones.
- Add public subnets for:
  - Application Load Balancer
  - NAT Gateway
- Add private subnets for:
  - ECS API tasks
  - ECS worker tasks
  - RDS PostgreSQL
- Add route tables and internet/NAT routing.
- Add security groups for:
  - ALB
  - API service
  - worker service
  - RDS
- Add IAM role foundations for ECS task execution and application tasks.
- Export values needed by later stacks.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| CloudFormation | Infrastructure is created with YAML templates. |
| VPC | Private application network for the whole platform. |
| Subnets | Public edge layer and private application/data layers. |
| NAT Gateway | Private ECS tasks can reach AWS APIs and package registries. |
| Security Groups | ALB, ECS, and RDS traffic is controlled explicitly. |
| IAM | Base roles prepare for least-privilege service access. |

## Acceptance checks

- CloudFormation stack deploys successfully.
- VPC spans at least two Availability Zones.
- Public and private subnets are created.
- Security groups allow only required traffic.
- Stack outputs are available for ECS, RDS, and storage templates.

## Portfolio proof

Show:

- CloudFormation stack screenshot
- VPC/subnet diagram
- security group rules
- explanation of why ECS and RDS belong in private subnets

## Result

The project has a repeatable AWS network foundation that supports a secure,
multi-service media platform.
