# Sprint 03 - ECS Fargate API

## Portfolio context

Deploy the backend API as a real containerized service on ECS Fargate. This is
the main control plane for the AI Media Processing Platform: it authenticates
users, creates upload records, generates presigned upload URLs in a later sprint,
and lets users check processing status.

This sprint shows that you can run production-style APIs on AWS using Docker,
ECR, ECS, ALB, IAM, and CloudWatch Logs.

## User story

As a user, I want the API to be reachable through a stable HTTPS endpoint so I
can request uploads, list my media files, and check processing status.

## Architecture focus

```text
User
   |
   v
Application Load Balancer
   |
   v
ECS Fargate API Service
   |
   +--> CloudWatch Logs
   |
   +--> PostgreSQL metadata database
```

CloudFront can be added later in front of the ALB. For now, the ALB exposes the
API service and performs health checks.

## Build scope

- Create an ECR repository for the API Docker image.
- Build and push the API image.
- Create an ECS cluster.
- Create an ECS task definition for the API.
- Create an ECS Fargate service in private subnets.
- Create an Application Load Balancer in public subnets.
- Add target group health checks for `GET /health`.
- Configure ECS task execution role permissions.
- Send container logs to CloudWatch Logs.
- Add API endpoints:
  - `GET /health`
  - `POST /uploads`
  - `GET /media`
  - `GET /media/{id}`
- Connect the API to PostgreSQL metadata storage when RDS is available.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| ECS Fargate | Runs the backend API without managing EC2 servers. |
| ECR | Stores versioned Docker images. |
| ALB | Routes public traffic to private ECS tasks. |
| IAM | Task roles separate AWS permissions from application code. |
| CloudWatch Logs | Captures API logs for debugging and monitoring. |
| Security Groups | ALB can reach API tasks; API can reach database. |

## Acceptance checks

- API image is available in ECR.
- ECS service reaches a steady running state.
- ALB health checks pass.
- `GET /health` works through the ALB URL.
- API logs appear in CloudWatch.
- Failed requests produce useful error logs.

## Portfolio proof

Show:

- ECS service running tasks
- ALB target group healthy targets
- ECR image repository
- CloudWatch API logs
- API request example from the public endpoint

## Result

The backend API runs on ECS Fargate behind an ALB and is ready to control the
media upload and processing workflow.
