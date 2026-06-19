# Sprint 08 - CloudFront Production Layer

## Portfolio context

Add CloudFront so the project looks like a production media platform. CloudFront
can deliver the frontend, accelerate API requests, and serve processed media
from private S3 buckets without exposing S3 directly to the public internet.

This sprint demonstrates CDN architecture, edge caching, HTTPS, private S3
origins, and the difference between upload and download paths.

## User story

As a user, I want the web app and processed images to load quickly and securely
through a CDN.

## Architecture focus

```text
Users
   |
   v
CloudFront
   |
   +--> S3 frontend origin
   |
   +--> ALB origin for API requests
   |
   +--> Private S3 media origin using Origin Access Control
```

Upload path:

```text
Frontend -> ECS API -> presigned S3 URL -> S3 upload bucket
```

Download path:

```text
User -> CloudFront URL -> private S3 processed media bucket
```

## Build scope

- Create a CloudFront distribution.
- Add an S3 origin for static frontend assets if the frontend is in scope.
- Add an ALB origin for API routes.
- Add a private S3 media origin for thumbnails and processed files.
- Use Origin Access Control so only CloudFront can read private S3 media.
- Configure cache behaviors:
  - frontend static assets: cache longer
  - processed media: cache safely
  - API routes: forward required headers and avoid caching unsafe responses
- Enforce HTTPS with `redirect-to-https`.
- Add custom domain and ACM certificate if available.
- Return CloudFront media URLs from the API instead of public S3 URLs.

## AWS topics demonstrated

| AWS topic | Where it appears |
| --- | --- |
| CloudFront | CDN for frontend, API, and media delivery. |
| S3 | Private origins for frontend/media assets. |
| Origin Access Control | Keeps S3 private while allowing CDN delivery. |
| ALB | API origin behind CloudFront. |
| HTTPS/TLS | Secure viewer connections. |
| Caching | Different behavior for static files, media, and API. |

## Acceptance checks

- CloudFront distribution deploys successfully.
- S3 media bucket is not public.
- Processed media loads through a CloudFront URL.
- Direct public S3 access is denied.
- API routes still work through CloudFront.
- HTTPS redirect works.

## Portfolio proof

Show:

- CloudFront distribution origins and behaviors
- private S3 bucket policy using CloudFront access
- processed image loading through CDN URL
- explanation of upload path versus download path

## Result

The platform serves frontend and processed media through a secure CDN layer,
using private S3 plus CloudFront instead of public buckets.
