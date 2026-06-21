from io import BytesIO

import pytest
from common.ai.schemas import GroqMediaAnalysisOutput, MediaAnalysisOutput
from common.ai.workflow import run_media_analysis_workflow
from common.config import settings
from PIL import Image


def _sample_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (320, 240), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_run_media_analysis_workflow_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_mock_mode", True)
    monkeypatch.setattr(settings, "groq_api_key", "")

    result = run_media_analysis_workflow(
        filename="sunset_beach.jpg",
        content_type="image/jpeg",
        image_bytes=_sample_jpeg_bytes(),
    )

    assert isinstance(result, MediaAnalysisOutput)
    assert result.caption
    assert "mock" in result.tags
    assert "sunset" in result.tags
    assert result.is_safe is True


def test_groq_media_analysis_output_coerces_string_is_safe() -> None:
    parsed = GroqMediaAnalysisOutput(
        caption="A blue image",
        tags=["blue"],
        labels=["photo"],
        quality_issues=[],
        is_safe="true",
    )
    result = parsed.to_media_analysis()
    assert result.is_safe is True
    assert isinstance(result, MediaAnalysisOutput)


def test_run_media_analysis_workflow_validates_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ai_mock_mode", True)
    monkeypatch.setattr(settings, "groq_api_key", "")

    result = run_media_analysis_workflow(
        filename="photo.jpg",
        content_type="image/jpeg",
        image_bytes=_sample_jpeg_bytes(),
    )

    validated = MediaAnalysisOutput.model_validate(result.model_dump())
    assert validated.caption == result.caption
