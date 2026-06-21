from common.config import settings


def build_cloudfront_media_url(object_key: str | None) -> str | None:
    """Build a viewer-facing CloudFront URL for a private S3 object key."""
    if not object_key:
        return None
    if not settings.cloudfront_media_base_url:
        return None

    base = settings.cloudfront_media_base_url.rstrip("/")
    key = object_key.lstrip("/")
    return f"{base}/{key}"
