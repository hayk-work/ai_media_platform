# Demo walkthrough

This document describes the end-to-end API flow and how to record a terminal demo
for your portfolio README or LinkedIn.

## Live endpoints

| Endpoint | URL |
| -------- | --- |
| **CloudFront (HTTPS, recommended)** | https://d2rhsorulu1z8s.cloudfront.net |
| **Swagger UI** | https://d2rhsorulu1z8s.cloudfront.net/docs |
| **ALB (HTTP, direct)** | http://ai-media-platform-api-alb-458236488.us-east-1.elb.amazonaws.com |

## Quick demo script

Run the automated curl demo against the live deployment:

```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

For local Docker:

```bash
API_URL=http://localhost:8000 ./scripts/demo.sh
```

## Full upload → process → AI flow

After `./scripts/demo.sh` returns a presigned `upload_url`, upload a small JPEG:

```bash
# Replace UPLOAD_URL from the script output
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

Poll until processing completes:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://d2rhsorulu1z8s.cloudfront.net/media/$MEDIA_ID"
```

Expected progression: `UPLOADING` → `PROCESSING` → `COMPLETED` with `thumbnail_url`
and `ai_result` (caption + tags).

## Record a terminal GIF (optional)

1. Install [asciinema](https://asciinema.org/) and [agg](https://github.com/asciinema/agg):

   ```bash
   pip install asciinema agg
   ```

2. Record the demo:

   ```bash
   asciinema rec demo.cast
   ./scripts/demo.sh
   # exit recording with Ctrl+D
   agg demo.cast docs/assets/demo.gif
   ```

3. Commit `docs/assets/demo.gif` and add it to the README:

   ```markdown
   ![Demo](docs/assets/demo.gif)
   ```

## Demo flow diagram

See [demo-flow.svg](assets/demo-flow.svg) for a static visual of the request path.
