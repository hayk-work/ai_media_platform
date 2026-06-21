from pydantic import BaseModel, Field


class MediaAnalysisOutput(BaseModel):
    caption: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)
    is_safe: bool = True


class GroqMediaAnalysisOutput(BaseModel):
    """Loose schema for Groq tool calls that may return booleans as strings."""

    caption: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)
    is_safe: str = Field(default="true", description="true or false")

    def to_media_analysis(self) -> MediaAnalysisOutput:
        normalized = self.is_safe.strip().lower()
        return MediaAnalysisOutput(
            caption=self.caption,
            tags=self.tags,
            labels=self.labels,
            quality_issues=self.quality_issues,
            is_safe=normalized in {"true", "1", "yes"},
        )
