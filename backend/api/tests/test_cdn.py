import pytest

from common.cdn import build_cloudfront_media_url
from common.config import Settings


def test_build_cloudfront_media_url_returns_none_without_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "common.cdn.settings",
        Settings(cloudfront_media_base_url=""),
    )
    assert build_cloudfront_media_url("thumbnails/u/m/photo.jpg") is None


def test_build_cloudfront_media_url_returns_none_for_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "common.cdn.settings",
        Settings(cloudfront_media_base_url="https://d111.cloudfront.net"),
    )
    assert build_cloudfront_media_url(None) is None


def test_build_cloudfront_media_url_builds_https_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "common.cdn.settings",
        Settings(cloudfront_media_base_url="https://d111.cloudfront.net"),
    )
    url = build_cloudfront_media_url("thumbnails/user/media/photo.jpg")
    assert url == "https://d111.cloudfront.net/thumbnails/user/media/photo.jpg"


def test_build_cloudfront_media_url_strips_slashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "common.cdn.settings",
        Settings(cloudfront_media_base_url="https://d111.cloudfront.net/"),
    )
    url = build_cloudfront_media_url("/thumbnails/user/media/photo.jpg")
    assert url == "https://d111.cloudfront.net/thumbnails/user/media/photo.jpg"
