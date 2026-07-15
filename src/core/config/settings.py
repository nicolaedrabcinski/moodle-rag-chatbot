"""
Core configuration module for FCIM AI Chatbot.
Loads and validates configuration from environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    data_dir: str = Field(default="./data", description="Data directory path")

    # =========================================================================
    # LLM Configuration (Qwen2.5:32B)
    # =========================================================================
    llm_model: str = Field(
        default="Qwen/Qwen2.5-32B-Instruct",
        description="LLM model name",
    )
    llm_host: str = Field(default="http://localhost", description="LLM server host")
    llm_port: int = Field(default=8001, description="LLM server port")
    llm_api_base: str = Field(
        default="http://localhost:8001/v1",
        description="LLM API base URL",
    )
    llm_max_tokens: int = Field(default=512, description="Max generation tokens")
    llm_temperature: float = Field(default=0.7, description="Sampling temperature")
    llm_top_p: float = Field(default=0.9, description="Nucleus sampling threshold")
    llm_top_k: int = Field(default=40, description="Top-k sampling")
    llm_max_model_len: int = Field(default=8192, description="Max model context length")
    llm_gpu_memory_utilization: float = Field(
        default=0.95,
        description="GPU memory utilization",
    )
    llm_tensor_parallel_size: int = Field(
        default=1,
        description="Tensor parallelism size",
    )
    llm_dtype: str = Field(default="half", description="Model dtype (half/bfloat16)")

    # =========================================================================
    # Embedding Configuration
    # =========================================================================
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-large",
        description="Embedding model name",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding dimension",
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Embedding batch size",
    )
    embedding_device: str = Field(default="cuda", description="Device (cuda/cpu)")

    # =========================================================================
    # Vector Database (Qdrant)
    # =========================================================================
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_collection: str = Field(
        default="fcim_courses",
        description="Qdrant collection name",
    )
    qdrant_distance_metric: str = Field(
        default="Cosine",
        description="Distance metric",
    )
    qdrant_hnsw_m: int = Field(default=16, description="HNSW M parameter")
    qdrant_hnsw_ef_construct: int = Field(
        default=100,
        description="HNSW ef_construct",
    )
    qdrant_hnsw_ef: int = Field(default=128, description="HNSW ef parameter")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")

    # =========================================================================
    # Redis Cache
    # =========================================================================
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(
        default=50,
        description="Redis max connections",
    )
    redis_ttl: int = Field(default=604800, description="Redis TTL (seconds)")
    redis_max_memory: str = Field(default="2GB", description="Redis max memory")
    redis_eviction_policy: str = Field(
        default="allkeys-lru",
        description="Redis eviction policy",
    )

    # =========================================================================
    # RAG Configuration
    # =========================================================================
    rag_top_k: int = Field(default=5, description="Final chunks returned to LLM")
    rag_retrieve_k: int = Field(default=20, description="Candidates retrieved before reranking")
    rag_similarity_threshold: float = Field(
        default=0.4,
        description="Minimum similarity score (lower = more candidates for reranker)",
    )
    rag_chunk_size: int = Field(default=1000, description="Text chunk size")
    rag_chunk_overlap: int = Field(default=200, description="Chunk overlap")
    rag_max_context_length: int = Field(
        default=6000,
        description="Max context length in chars",
    )
    rag_rerank: bool = Field(default=True, description="Enable reranking")
    rag_multi_query: bool = Field(default=True, description="Enable multi-query expansion")
    rag_multi_query_count: int = Field(default=3, description="Number of query variants")

    # =========================================================================
    # Reranker
    # =========================================================================
    reranker_model: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="Cross-encoder reranker model",
    )
    reranker_device: str = Field(default="cpu", description="Reranker device (cpu/cuda)")

    # =========================================================================
    # FastAPI Application
    # =========================================================================
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of workers")
    api_reload: bool = Field(default=False, description="Auto-reload on code changes")
    api_title: str = Field(
        default="FCIM AI Assistant API",
        description="API title",
    )
    api_version: str = Field(default="1.0.0", description="API version")
    api_docs_url: str = Field(default="/docs", description="API docs URL")
    api_openapi_url: str = Field(default="/openapi.json", description="OpenAPI URL")

    # =========================================================================
    # Security & Authentication
    # =========================================================================
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        description="JWT token expiration (minutes)",
    )
    cors_origins: str = Field(
        default="https://else.fcim.utm.md,http://localhost:3000",
        description="CORS allowed origins (comma-separated)",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="CORS allow credentials",
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(
        default=100,
        description="Requests per minute",
    )
    rate_limit_per_hour: int = Field(default=1000, description="Requests per hour")
    rate_limit_storage_uri: str = Field(
        default="redis://localhost:6379",
        description="Rate limit storage URI",
    )

    # =========================================================================
    # Monitoring
    # =========================================================================
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus")
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    grafana_port: int = Field(default=3000, description="Grafana port")
    metrics_enabled: bool = Field(default=True, description="Enable metrics")

    # =========================================================================
    # Data Pipeline
    # =========================================================================
    data_raw_path: str = Field(default="/app/data/raw", description="Raw data path")
    data_processed_path: str = Field(
        default="/app/data/processed",
        description="Processed data path",
    )
    data_embeddings_path: str = Field(
        default="/app/data/embeddings",
        description="Embeddings path",
    )
    batch_size_embedding: int = Field(
        default=32,
        description="Embedding batch size",
    )
    batch_size_upload: int = Field(default=100, description="Upload batch size")

    # =========================================================================
    # Moodle Integration
    # =========================================================================
    moodle_url: str = Field(
        default="https://else.fcim.utm.md",
        description="Moodle URL",
    )
    moodle_api_token: Optional[str] = Field(
        default=None,
        description="Moodle API token",
    )
    moodle_service_name: str = Field(
        default="fcim_ai_assistant",
        description="Moodle service name",
    )

    # =========================================================================
    # Logging
    # =========================================================================
    log_format: str = Field(default="json", description="Log format (json/text)")
    log_file_path: str = Field(
        default="/app/logs/app.log",
        description="Log file path",
    )
    log_rotation_size: str = Field(
        default="100MB",
        description="Log rotation size",
    )
    log_retention_days: int = Field(
        default=30,
        description="Log retention (days)",
    )

    # =========================================================================
    # Performance Tuning
    # =========================================================================
    max_request_size: str = Field(default="10MB", description="Max request size")
    request_timeout: int = Field(default=60, description="Request timeout (seconds)")
    max_concurrent_requests: int = Field(
        default=50,
        description="Max concurrent requests",
    )
    cache_hit_target: float = Field(default=0.30, description="Cache hit rate target")

    @property
    def llm_api_url(self) -> str:
        """Get full LLM API URL."""
        return f"{self.llm_host}:{self.llm_port}/v1"

    @property
    def qdrant_url(self) -> str:
        """Get full Qdrant URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def redis_url(self) -> str:
        """Get full Redis URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration
    """
    return Settings()


# Export settings instance
settings = get_settings()
