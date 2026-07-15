"""
Chat endpoints with RAG and caching.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.core.config.logging import LoggerAdapter
from src.core.rag import ChatRequest, ChatResponse, get_rag_pipeline
from src.services.cache import get_redis_cache

logger = LoggerAdapter(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with RAG.

    Processes user question and returns AI-generated answer with sources.

    Args:
        request: Chat request with question and optional course_id

    Returns:
        ChatResponse: Generated answer with source references

    Raises:
        HTTPException: If generation fails
    """
    start_time = time.time()

    logger.info(
        "Received chat request",
        question=request.question[:100],
        course_id=request.course_id,
        language=request.language,
    )

    cache = None
    try:
        cache = await get_redis_cache()
        cached_response = await cache.get(request.question, request.course_id)

        if cached_response:
            logger.info(
                "Returning cached response",
                elapsed_time=time.time() - start_time,
            )
            cached_response["cached"] = True
            return ChatResponse(**cached_response)
    except Exception as e:
        logger.warning("Cache check failed, proceeding without cache", error=str(e))

    try:
        pipeline = get_rag_pipeline()
        response = await pipeline.generate(request)

        elapsed_time = time.time() - start_time
        logger.info(
            "Generated response",
            answer_length=len(response.answer),
            num_sources=len(response.sources),
            elapsed_time=elapsed_time,
        )

        if cache is not None:
            try:
                await cache.set(
                    question=request.question,
                    response=response.dict(),
                    course_id=request.course_id,
                )
            except Exception as e:
                logger.warning("Failed to cache response", error=str(e))

        return response

    except Exception as e:
        logger.error("Failed to generate response", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}",
        ) from e


@router.post("/chat/stream", status_code=status.HTTP_200_OK)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Chat endpoint with streaming.

    Streams AI-generated answer in real-time.

    Args:
        request: Chat request with question and optional course_id

    Returns:
        StreamingResponse: Server-sent events stream

    Raises:
        HTTPException: If generation fails
    """
    import json as _json

    logger.info(
        "Received streaming chat request",
        question=request.question[:100],
        course_id=request.course_id,
    )

    # Check cache — if hit, replay as a stream so the client sees the same format
    try:
        cache = await get_redis_cache()
        cached_response = await cache.get(request.question, request.course_id)
        if cached_response:
            logger.info("Returning cached response (stream)")

            async def _cached_stream() -> Any:
                yield f"data: {_json.dumps({'type': 'meta', 'sources': [{'document': s.get('course_name', ''), 'topic': s.get('topic'), 'score': round(s.get('score', 0), 3)} for s in cached_response.get('sources', [])]})}\n\n"
                yield f"data: {_json.dumps({'type': 'token', 'text': cached_response.get('answer', '')})}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                _cached_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
    except Exception as e:
        logger.warning("Cache check failed for stream, proceeding without cache", error=str(e))

    async def generate_stream() -> Any:
        """Generate SSE stream."""
        try:
            pipeline = get_rag_pipeline()

            async for text_chunk in pipeline.generate_stream(request):
                yield f"data: {text_chunk}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Streaming generation failed", error=str(e))
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/cache/stats", status_code=status.HTTP_200_OK)
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dict with cache hit rate and other metrics
    """
    try:
        cache = await get_redis_cache()
        stats = cache.get_stats()

        logger.debug("Cache stats requested", stats=stats)
        return stats
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}",
        ) from e


@router.post("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_cache(course_id: str | None = None) -> Dict[str, Any]:
    """
    Clear cache (all or specific course).

    Args:
        course_id: Optional course ID to clear specific course cache

    Returns:
        Dict with cleared count
    """
    try:
        cache = await get_redis_cache()

        if course_id:
            cleared = await cache.clear_course(course_id)
            logger.info("Cleared course cache", course_id=course_id, cleared=cleared)
            return {"cleared": cleared, "course_id": course_id}
        else:
            await cache.clear_all()
            logger.info("Cleared all cache")
            return {"cleared": "all"}

    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        ) from e
