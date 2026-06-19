#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="${ROOT_DIR}"
PACKAGED_TEMPLATE="${ROOT_DIR}/packaged-master.yaml"
STACK_NAME="${STACK_NAME:-ai-media-platform-network}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-ai-media-platform}"
DEPLOY_BUCKET="${DEPLOY_BUCKET:?Set DEPLOY_BUCKET to an S3 bucket for template packaging}"

aws cloudformation package \
  --template-file "${TEMPLATE_DIR}/master.yaml" \
  --s3-bucket "${DEPLOY_BUCKET}" \
  --output-template-file "${PACKAGED_TEMPLATE}"

aws cloudformation deploy \
  --template-file "${PACKAGED_TEMPLATE}" \
  --stack-name "${STACK_NAME}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides "EnvironmentName=${ENVIRONMENT_NAME}" \
  --no-fail-on-empty-changeset

echo "Stack deployed: ${STACK_NAME}"
