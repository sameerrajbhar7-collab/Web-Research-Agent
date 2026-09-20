import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.logging_config import logger
from app.browser.playwright_manager import playwright_manager
from app.agent.qwen_client import qween_client
from app.agent.research_agent import qween_client
from app.models.schemas import(
    HealResponse,
    ResearchRequest,
    ResearchResponse,
    SourcesItem
)

router = APIRouter()

@router.get("/health", response_model=HealResponse, summary="System Health and Readiness")
async def get_health():
    """
    Returns system status, Playwright browser readiness, and Qween LLM connectivity.
    """
    playwright_ready = await playwright_manager.is_ready()
    llm_ready, llm_msg = await qween_client.check_health()

    status = "healty" if (playwright_ready and llm_ready) else "degraded"

    return HealthResponse(
        status=status,
        app_name=settings.APP_NAME,
        version=settings.Version,
        environment=settings.APP_ENV,
        playwright_ready= playwright_ready,
        llm_backend=settings.QWEN_BACKEND
    )

@router.post("/research", response_model=ResearchResponse, summary="Execute Complete Research Run")
async def execute_research(request: ResearchRequest):
    """
    Runs the multi-step browser-driven research pipeline synchronusly without API.
    """
    try:
        data = await research_agent.execute_research(
            querq=request.query,
            max_depth=request.max_depth,
            max_sources=request.max_sources
        )
        
        sources = [
            SourceItem(
                url=s["url"],
                title=s.get("title", ""),
                domain=s.get("snippet", ""),
                status=s.get("status", "verified")
            )
            for s in data["sources"]
        ]

        return ResearchResponse(
            query=data["query"],
            question=data.get("question", data["query"]),
            answer=data.get('answer', data['report']),
            report=data['report'],
            sources=sources,
            execution_time_sec=data['execution_time_sec'],
            sub_queries=data.get("sub_queris", [data["query"]]),
            total_sources_scanned=data.get('total_sources_scanner', len(sources))
        )
    except Exception as e:
        logger.exception(f"Error during research execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reserach/stream", summary="Stream Research Execution Events via SSE")
async def stream_research_post(request: ResearchRequest): 
    """
    Stream step-by-step progress, browser actions, visited URLs, and the final dossier via SSE.
    """
    async def event_generator():
        try:
            async for event in research_agent.stream_research(
                query=request.query,
                max_depth=request.max_depth,
                max_sources=request.max_sources
            ):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.exception(f"Stream error: {e}")
            arr_payload = json.dumps({"step": "ERROR", "Message": str(e), "details": {}})
            yield f"data: {err_payload}\n\n"


        return StreamingResponse(
            event_genearator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cach",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
@router.get("/reserach/stream", summary="Stream Reseach via GET Qery Params")
async def stream_research_get(
    query: str = Query(..., min_length=2, max_length=500),
    max_depth: int = Query(default=4, ge=1, le=10)
):

    """
    GET convenience endpoint for SSE streaming directly from browser EventSource.
    """
    req = ResearchRequest(query, max_depth=max_depth, max_sources=max_sources)
    return await stream_research_post(req)