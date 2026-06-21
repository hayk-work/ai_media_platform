#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-https://d2rhsorulu1z8s.cloudfront.net}"
EMAIL="demo-$(date +%s)@example.com"
PASSWORD="demo-password-123"

echo "=== AI Media Platform demo ==="
echo "API: ${API_URL}"
echo

step() { echo; echo "-> $1"; }

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
  -d '{"filename":"demo.jpg","content_type":"image/jpeg","file_size_bytes":2048}')
echo "${UPLOAD}" | python3 -m json.tool
MEDIA_ID=$(echo "${UPLOAD}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["media_id"])')

step "List media (empty or pending)"
curl -sf "${API_URL}/media" -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool

step "Notification preferences"
curl -sf "${API_URL}/notifications/preferences" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool

echo
echo "Demo complete. media_id=${MEDIA_ID}"
echo "Upload a JPEG to the presigned URL, then poll GET ${API_URL}/media/${MEDIA_ID}"
