# Sprint roadmap

Eleven sprints from local foundation to a production-style AWS media platform.
This project is **API-only** — clients use HTTP (`curl`, Postman, `/docs`).

| Sprint | Name | Focus |
| --- | --- | --- |
| 01 | [Foundation](./Sprint_01_Foundation.md) | Local API, worker placeholder, PostgreSQL, Docker |
| 02 | [Authentication](./Sprint_02_Authentication.md) | Register, login, logout, JWT, protected routes |
| 03 | [CloudFormation Network](./Sprint_03_CloudFormation_Network.md) | VPC, subnets, security groups, IAM foundations |
| 04 | [ECS Fargate API](./Sprint_04_ECS_API.md) | Deploy API on ECS behind ALB |
| 05 | [S3 Uploads](./Sprint_05_S3_Uploads.md) | Presigned URLs, private bucket |
| 06 | [Async Workers](./Sprint_06_Async_Workers.md) | EventBridge, SQS, ECS worker processing |
| 07 | [AI LangChain / LangGraph](./Sprint_07_AI_LangChain_LangGraph.md) | Image/video analysis pipeline |
| 08 | [SNS Notifications](./Sprint_08_SNS_Notifications.md) | Email alerts when processing completes |
| 09 | [CloudFront](./Sprint_09_CloudFront.md) | CDN for API and processed media |
| 10 | [Monitoring & Security](./Sprint_10_Monitoring_Security.md) | CloudWatch, CloudTrail, alarms, IAM review |
| 11 | [Kinesis Analytics](./Sprint_11_Kinesis_Analytics.md) | Optional real-time usage analytics |

## Recommended order

```text
01 Foundation
   ↓
02 Authentication        ← real login before uploads go to AWS
   ↓
03 CloudFormation
   ↓
04 ECS API
   ↓
05 S3 Uploads
   ↓
06 Async Workers
   ↓
07 AI Processing
   ↓
08 SNS Notifications
   ↓
09 CloudFront
   ↓
10 Monitoring & Security
   ↓
11 Kinesis Analytics (optional)
```

## Current status

- **Sprint 02** — implemented locally (JWT auth)
- **Sprint 03** — next up (CloudFormation network)
