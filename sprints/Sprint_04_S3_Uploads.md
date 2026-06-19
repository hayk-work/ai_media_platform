# Sprint 04 - S3 Upload System

## Portfolio context

Add the file upload workflow that makes this project feel like a real media
platform. Users do not upload large images or videos through the API container.
Instead, the API creates metadata in PostgreSQL and returns a presigned S3 URL
so the browser can upload directly to S3.

This demonstrates S3, presigned URLs, IAM permissions, private buckets, and the
common production pattern of keeping application servers out of the large file
data path.

## User story

As a user, I want to upload an image or video directly from my browser so the
platform can store it reliably and process it in the background.

## Architecture focus

```text
Frontend
   |
   | POST /uploads
   v
ECS API
   |
   +--> PostgreSQL: create media item with UPLOADING status
   |
   +--> S3: generate presigned upload URL
   |
   v
Frontend
   |
   | PUT file to presigned URL
   v
Private S3 Bucket
```

## Build scope

- Create an S3 bucket for original uploads.
- Keep the bucket private.
- Add bucket encryption and block public access.
- Add lifecycle rules for temporary or failed uploads if useful.
- Give the API task role permission to generate presigned URLs.
- Add `POST /uploads` request body:
  - file name
  - content type
  - file size
- Store a `media_items` record:
  - `id`
  - `user_id`
  - `original_s3_key`
  - `thumbnail_s3_key`
  - `status`
  - `created_at`
  - `updated_at`
- Return an API response like:

```json
{
  "media_id": "media_123",
  "upload_url": "https://s3-presigned-url",
  "status": "UPLOADING"
}
```

- Add `GET /media/{id}` so users can check upload and processing status.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| S3 | Stores original media files. |
| Presigned URLs | Browser uploads directly to S3. |
| IAM | API can sign uploads without making S3 public. |
| RDS PostgreSQL | Stores metadata and processing status. |
| Security | Bucket blocks public access and uses encryption. |

## Acceptance checks

- API returns a valid presigned upload URL.
- Browser or curl can upload a file using the URL.
- S3 object appears under the expected key.
- Database record is created with `UPLOADING` status.
- S3 bucket is not publicly readable.

## Portfolio proof

Show:

- API request and response for `POST /uploads`
- successful direct S3 upload
- private S3 bucket settings
- database row for the uploaded media item

## Result

Users can upload media directly to a private S3 bucket while the API stores
clean metadata for the later async processing pipeline.
