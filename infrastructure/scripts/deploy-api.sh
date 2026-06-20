#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
PACKAGED_TEMPLATE="${ROOT_DIR}/packaged-api-master.yaml"
STACK_NAME="${STACK_NAME:-ai-media-platform-api}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-ai-media-platform}"
DEPLOY_BUCKET="${DEPLOY_BUCKET:?Set DEPLOY_BUCKET to an S3 bucket for template packaging}"
AWS_REGION="${AWS_REGION:-$(aws configure get region)}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ENVIRONMENT_NAME}-api"
IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo "Phase 1: deploy ECR repository (if needed)..."
aws cloudformation package \
  --template-file "${ROOT_DIR}/api-master.yaml" \
  --s3-bucket "${DEPLOY_BUCKET}" \
  --output-template-file "${PACKAGED_TEMPLATE}"

aws cloudformation deploy \
  --template-file "${PACKAGED_TEMPLATE}" \
  --stack-name "${STACK_NAME}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    "EnvironmentName=${ENVIRONMENT_NAME}" \
    "ApiImageUri=${IMAGE_URI}" \
    "ApiDesiredCount=0" \
  --no-fail-on-empty-changeset

echo "Phase 2: build and push API image to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -f "${REPO_ROOT}/backend/api/Dockerfile" -t "${IMAGE_URI}" "${REPO_ROOT}"
docker push "${IMAGE_URI}"

echo "Phase 3: start ECS API service..."
aws cloudformation deploy \
  --template-file "${PACKAGED_TEMPLATE}" \
  --stack-name "${STACK_NAME}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    "EnvironmentName=${ENVIRONMENT_NAME}" \
    "ApiImageUri=${IMAGE_URI}" \
    "ApiDesiredCount=1" \
  --no-fail-on-empty-changeset

echo "Waiting for ECS service to stabilize..."
CLUSTER_NAME="${ENVIRONMENT_NAME}-cluster"
SERVICE_NAME="${ENVIRONMENT_NAME}-api"
aws ecs wait services-stable --cluster "${CLUSTER_NAME}" --services "${SERVICE_NAME}"

API_URL="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiLoadBalancerUrl'].OutputValue" \
  --output text)"

echo "Stack deployed: ${STACK_NAME}"
echo "API URL: ${API_URL}"

echo "Health check:"
curl -sf "${API_URL}/health"
echo
