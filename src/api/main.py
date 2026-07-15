"""
FastAPI application - FCIM AI Chatbot.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
# from prometheus_fastapi_instrumentator import Instrumentator

from src.core.config import settings
from src.core.config.logging import LoggerAdapter, configure_logging
from src.core.embeddings import get_embedding_service
from src.core.llm import close_llm_client, get_llm_client
from src.core.rag import get_rag_pipeline
from src.core.rag.reranker import get_reranker
from src.services.cache import close_redis_cache, get_redis_cache

from .routes import chat, health, upload

# Configure logging
configure_logging()
logger = LoggerAdapter(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting FCIM AI Chatbot API", version=settings.api_version)

    # Initialize services
    try:
        # Pre-warm embedding model (loads into GPU memory once)
        get_embedding_service()

        # Pre-warm reranker (downloads + loads BGE-reranker-v2-m3 on CPU)
        if settings.rag_rerank:
            get_reranker()

        # Pre-warm RAG pipeline (initializes all sub-services)
        get_rag_pipeline()

        # Initialize LLM client
        llm_client = get_llm_client()
        is_healthy = await llm_client.health_check()
        if not is_healthy:
            logger.warning("LLM server not healthy during startup")

        # Initialize Redis cache
        await get_redis_cache()

        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down FCIM AI Chatbot API")

    # Close connections
    try:
        await close_llm_client()
        await close_redis_cache()
        logger.info("All connections closed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI-powered chatbot for FCIM UTM ELSE Platform using RAG with Qwen2.5:32B",
    docs_url=settings.api_docs_url if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url=settings.api_openapi_url if settings.debug else None,
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.exception(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Prometheus metrics
# if settings.metrics_enabled:
#     instrumentator = Instrumentator(
#         should_group_status_codes=True,
#         should_ignore_untemplated=True,
#         should_respect_env_var=True,
#         should_instrument_requests_inprogress=True,
#         excluded_handlers=["/metrics", "/health"],
#         inprogress_name="http_requests_inprogress",
#         inprogress_labels=True,
#     )
#     instrumentator.instrument(app).expose(app, endpoint="/metrics")
#     logger.info("Prometheus metrics enabled at /metrics")


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(upload.router, prefix="/api", tags=["upload"])


# Mount static files for frontend
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
    logger.info("Frontend static files mounted at /static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve frontend."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "docs": f"{settings.api_docs_url}",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=1 if settings.api_reload else settings.api_workers,
        log_level=settings.log_level.lower(),
    )
