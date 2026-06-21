import base64
import time
from typing import Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from common.ai.schemas import MediaAnalysisOutput
from common.config import settings

logger = structlog.get_logger(__name__)

AI_MAX_RETRIES = 3
AI_RETRY_DELAY_SECONDS = 1.0


class AnalysisState(TypedDict, total=False):
    filename: str
    content_type: str
    image_bytes: bytes
    prompt: str
    caption: str
    tags: list[str]
    labels: list[str]
    quality_issues: list[str]
    is_safe: bool
    provider: str
    model: str
    error: str | None


def _log_node_start(node_name: str, media_context: str = "") -> float:
    logger.info("ai_node_started", ai_node=node_name, filename=media_context or None)
    return time.perf_counter()


def _log_node_done(node_name: str, started_at: float, **extra: Any) -> None:
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info("ai_node_completed", ai_node=node_name, duration_ms=duration_ms, **extra)


def load_context(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("load_context", state.get("filename", ""))
    provider = "mock" if settings.ai_mock_mode else "groq"
    model = settings.groq_model if provider == "groq" else "mock-analysis"
    _log_node_done("load_context", started_at, provider=provider, model=model)
    return {"provider": provider, "model": model, "error": None}


def prepare_prompt(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("prepare_prompt", state.get("filename", ""))
    prompt = (
        "Analyze this image and return structured metadata.\n"
        f"Filename: {state['filename']}\n"
        f"Content type: {state['content_type']}\n"
        "Provide a concise caption, searchable tags, descriptive labels, "
        "any quality issues (blur, low light, cropped, etc.), and whether the "
        "content appears safe for a general audience."
    )
    _log_node_done("prepare_prompt", started_at)
    return {"prompt": prompt}


def _mock_analysis(state: AnalysisState) -> MediaAnalysisOutput:
    stem = state["filename"].rsplit(".", 1)[0].lower().replace("_", " ")
    caption = f"Mock analysis of {stem or 'uploaded image'}."
    tags = ["mock", "portfolio", "image"]
    if stem:
        tags.append(stem.split()[0])
    return MediaAnalysisOutput(
        caption=caption,
        tags=tags,
        labels=["photo", "upload"],
        quality_issues=[],
        is_safe=True,
    )


def _groq_analysis(state: AnalysisState) -> MediaAnalysisOutput:
    from langchain_groq import ChatGroq

    encoded = base64.b64encode(state["image_bytes"]).decode("ascii")
    content_type = state["content_type"] or "image/jpeg"
    message = HumanMessage(
        content=[
            {"type": "text", "text": state["prompt"]},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{content_type};base64,{encoded}"},
            },
        ]
    )
    model = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
    )
    structured_model = model.with_structured_output(MediaAnalysisOutput)
    result = structured_model.invoke([message])
    if isinstance(result, MediaAnalysisOutput):
        return result
    return MediaAnalysisOutput.model_validate(result)


def analyze_image(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("analyze_image", state.get("filename", ""))
    last_error: Exception | None = None

    for attempt in range(1, AI_MAX_RETRIES + 1):
        try:
            output = (
                _mock_analysis(state)
                if settings.ai_mock_mode
                else _groq_analysis(state)
            )
            _log_node_done("analyze_image", started_at, attempt=attempt)
            return {
                "caption": output.caption,
                "tags": output.tags,
                "labels": output.labels,
                "quality_issues": output.quality_issues,
                "is_safe": output.is_safe,
                "error": None,
            }
        except Exception as exc:
            last_error = exc
            logger.warning(
                "ai_node_retry",
                ai_node="analyze_image",
                attempt=attempt,
                error=str(exc),
            )
            if attempt < AI_MAX_RETRIES:
                time.sleep(AI_RETRY_DELAY_SECONDS)

    assert last_error is not None
    _log_node_done("analyze_image", started_at, status="failed")
    raise last_error


def extract_tags(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("extract_tags", state.get("filename", ""))
    normalized = []
    seen: set[str] = set()
    for tag in state.get("tags", []):
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    _log_node_done("extract_tags", started_at, tag_count=len(normalized))
    return {"tags": normalized}


def safety_check(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("safety_check", state.get("filename", ""))
    quality_issues = list(state.get("quality_issues", []))
    is_safe = bool(state.get("is_safe", True))
    if not is_safe and "unsafe content" not in [issue.lower() for issue in quality_issues]:
        quality_issues.append("unsafe content flagged by model")
    _log_node_done("safety_check", started_at, is_safe=is_safe)
    return {"quality_issues": quality_issues, "is_safe": is_safe}


def validate_result(state: AnalysisState) -> dict[str, Any]:
    started_at = _log_node_start("validate_result", state.get("filename", ""))
    output = MediaAnalysisOutput(
        caption=state.get("caption", ""),
        tags=state.get("tags", []),
        labels=state.get("labels", []),
        quality_issues=state.get("quality_issues", []),
        is_safe=state.get("is_safe", True),
    )
    validated = MediaAnalysisOutput.model_validate(output.model_dump())
    _log_node_done("validate_result", started_at)
    return validated.model_dump()


def build_analysis_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("load_context", load_context)
    graph.add_node("prepare_prompt", prepare_prompt)
    graph.add_node("analyze_image", analyze_image)
    graph.add_node("extract_tags", extract_tags)
    graph.add_node("safety_check", safety_check)
    graph.add_node("validate_result", validate_result)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "prepare_prompt")
    graph.add_edge("prepare_prompt", "analyze_image")
    graph.add_edge("analyze_image", "extract_tags")
    graph.add_edge("extract_tags", "safety_check")
    graph.add_edge("safety_check", "validate_result")
    graph.add_edge("validate_result", END)
    return graph.compile()


_analysis_graph = None


def get_analysis_graph():
    global _analysis_graph
    if _analysis_graph is None:
        _analysis_graph = build_analysis_graph()
    return _analysis_graph


def run_media_analysis_workflow(
    *,
    filename: str,
    content_type: str,
    image_bytes: bytes,
) -> MediaAnalysisOutput:
    logger.info("ai_workflow_started", filename=filename, content_type=content_type)
    started_at = time.perf_counter()
    graph = get_analysis_graph()
    final_state = graph.invoke(
        {
            "filename": filename,
            "content_type": content_type,
            "image_bytes": image_bytes,
        }
    )
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info("ai_workflow_completed", filename=filename, duration_ms=duration_ms)
    return MediaAnalysisOutput.model_validate(final_state)
