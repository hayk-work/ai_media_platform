from pydantic import BaseModel, Field


class MediaAnalysisOutput(BaseModel):
    caption: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)
    is_safe: bool = True
