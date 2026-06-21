#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${API_URL:-https://d2rhsorulu1z8s.cloudfront.net}"
DEMO_PHOTO="${DEMO_PHOTO:-${ROOT_DIR}/scripts/demo-photo.jpg}"
EMAIL="demo-$(date +%s)@example.com"
PASSWORD="demo-password-123"
POLL_SECONDS="${POLL_SECONDS:-10}"
POLL_ATTEMPTS="${POLL_ATTEMPTS:-30}"

echo "=== AI Media Platform demo ==="
echo "API: ${API_URL}"
echo

step() { echo; echo "-> $1"; }

if [[ ! -f "${DEMO_PHOTO}" ]]; then
  echo "Demo photo not found at ${DEMO_PHOTO}"
  echo "Create it with: python3 scripts/create-demo-photo.py"
  exit 1
fi

FILE_SIZE=$(wc -c < "${DEMO_PHOTO}" | tr -d ' ')
echo "Using demo photo: ${DEMO_PHOTO} (${FILE_SIZE} bytes)"

step "Health check"
curl -sf "${API_URL}/health" | python3 -m json.tool

step "Register user (${EMAIL})"
curl -sf -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" | python3 -m json.tool

step "Login"
TOKEN=$(curl -sf -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "access_token acquired (${#TOKEN} chars)"

step "Request presigned upload URL"
UPLOAD=$(curl -sf -X POST "${API_URL}/uploads" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"demo.jpg\",\"content_type\":\"image/jpeg\",\"file_size_bytes\":${FILE_SIZE}}")
echo "${UPLOAD}" | python3 -m json.tool
MEDIA_ID=$(echo "${UPLOAD}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["media_id"])')
UPLOAD_URL=$(echo "${UPLOAD}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["upload_url"])')

step "Upload JPEG to S3"
curl -sf -X PUT "${UPLOAD_URL}" \
  -H "Content-Type: image/jpeg" \
  --data-binary @"${DEMO_PHOTO}"
echo "uploaded ${FILE_SIZE} bytes"

step "Poll processing status"
for ((i = 1; i <= POLL_ATTEMPTS; i++)); do
  MEDIA=$(curl -sf "${API_URL}/media/${MEDIA_ID}" -H "Authorization: Bearer ${TOKEN}")
  STATUS=$(echo "${MEDIA}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  AI_STATUS=$(echo "${MEDIA}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d.get("ai_result") or {}).get("status") or "pending")')
  echo "poll ${i}/${POLL_ATTEMPTS}: media=${STATUS} ai=${AI_STATUS}"
  if [[ "${STATUS}" == "COMPLETED" && "${AI_STATUS}" == "COMPLETED" ]]; then
    echo "${MEDIA}" | python3 -m json.tool
    echo
    echo "Demo complete. media_id=${MEDIA_ID}"
    exit 0
  fi
  if [[ "${STATUS}" == "FAILED" || "${AI_STATUS}" == "FAILED" ]]; then
    echo "${MEDIA}" | python3 -m json.tool
    exit 1
  fi
  sleep "${POLL_SECONDS}"
done

echo "Timed out waiting for processing to complete."
exit 1
