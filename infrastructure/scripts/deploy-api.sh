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
API_ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ENVIRONMENT_NAME}-api"
WORKER_ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ENVIRONMENT_NAME}-worker"
API_IMAGE_URI="${API_ECR_URI}:${IMAGE_TAG}"
WORKER_IMAGE_URI="${WORKER_ECR_URI}:${IMAGE_TAG}"
GROQ_SECRET_NAME="${ENVIRONMENT_NAME}/worker/groq-api-key"

sync_groq_secret() {
  local env_file="${REPO_ROOT}/.env"
  if [[ ! -f "${env_file}" ]]; then
    echo "Skipping Groq secret sync: ${env_file} not found."
    return 0
  fi

  local groq_key
  groq_key="$(grep -E '^GROQ_API_KEY=' "${env_file}" | cut -d= -f2- || true)"
  if [[ -z "${groq_key}" ]]; then
    echo "Skipping Groq secret sync: GROQ_API_KEY is empty in ${env_file}."
    return 0
  fi

  if ! aws secretsmanager describe-secret --secret-id "${GROQ_SECRET_NAME}" >/dev/null 2>&1; then
    echo "Groq secret ${GROQ_SECRET_NAME} not found yet; it will be created by CloudFormation."
    return 0
  fi

  echo "Syncing Groq API key to Secrets Manager (${GROQ_SECRET_NAME})..."
  aws secretsmanager put-secret-value \
    --secret-id "${GROQ_SECRET_NAME}" \
    --secret-string "${groq_key}" >/dev/null
}

echo "Phase 1: deploy platform stacks (scale services to 0)..."
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
    "ApiImageUri=${API_IMAGE_URI}" \
    "WorkerImageUri=${WORKER_IMAGE_URI}" \
    "ApiDesiredCount=0" \
    "WorkerDesiredCount=0" \
  --no-fail-on-empty-changeset

sync_groq_secret

echo "Phase 2: build and push API + worker images to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -f "${REPO_ROOT}/backend/api/Dockerfile" -t "${API_IMAGE_URI}" "${REPO_ROOT}"
docker push "${API_IMAGE_URI}"
docker build -f "${REPO_ROOT}/backend/worker/Dockerfile" -t "${WORKER_IMAGE_URI}" "${REPO_ROOT}"
docker push "${WORKER_IMAGE_URI}"

echo "Phase 3: start API and worker services..."
aws cloudformation deploy \
  --template-file "${PACKAGED_TEMPLATE}" \
  --stack-name "${STACK_NAME}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    "EnvironmentName=${ENVIRONMENT_NAME}" \
    "ApiImageUri=${API_IMAGE_URI}" \
    "WorkerImageUri=${WORKER_IMAGE_URI}" \
    "ApiDesiredCount=1" \
    "WorkerDesiredCount=1" \
  --no-fail-on-empty-changeset

sync_groq_secret

CLUSTER_NAME="${ENVIRONMENT_NAME}-cluster"
echo "Waiting for ECS services to stabilize..."
aws ecs wait services-stable --cluster "${CLUSTER_NAME}" --services "${ENVIRONMENT_NAME}-api" "${ENVIRONMENT_NAME}-worker"

API_URL="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiLoadBalancerUrl'].OutputValue" \
  --output text)"

CLOUDFRONT_URL="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" \
  --output text)"

echo "Stack deployed: ${STACK_NAME}"
echo "API URL: ${API_URL}"
echo "CloudFront URL: ${CLOUDFRONT_URL}"

echo "Health check:"
curl -sf "${API_URL}/health"
echo
if [[ -n "${CLOUDFRONT_URL}" && "${CLOUDFRONT_URL}" != "None" ]]; then
  echo "CloudFront health check:"
  curl -sf "${CLOUDFRONT_URL}/health"
  echo
fi
