"""
RAG Pipeline data models.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model."""

    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    course_id: Optional[str] = Field(None, description="Course ID for filtering")
    language: Optional[str] = Field("ro", description="Response language (ru/ro/en)")
    max_tokens: Optional[int] = Field(None, description="Max tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")


class RetrievedChunk(BaseModel):
    """Retrieved document chunk with metadata."""

    id: str = Field(..., description="Chunk ID")
    score: float = Field(..., description="Similarity score")
    text: str = Field(..., description="Chunk text")
    course_id: str = Field(..., description="Course ID")
    course_name: str = Field(..., description="Course name")
    topic: Optional[str] = Field(None, description="Topic/chapter")
    file_path: Optional[str] = Field(None, description="Source file path")
    page_number: Optional[int] = Field(None, description="Page number")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "abc123",
                "score": 0.92,
                "text": "Binary search tree is a data structure...",
                "course_id": "ASD-2024",
                "course_name": "Algorithms and Data Structures",
                "topic": "Trees",
                "file_path": "lecture_05_trees.pdf",
                "page_number": 15,
            }
        }


class TimingInfo(BaseModel):
    """Per-stage latency breakdown in milliseconds."""

    embed_ms: float = Field(..., description="Query embedding time")
    search_ms: float = Field(..., description="Qdrant vector search time")
    llm_ms: float = Field(..., description="LLM generation time")
    total_ms: float = Field(..., description="End-to-end time")


class ChatResponse(BaseModel):
    """Chat response model."""

    answer: str = Field(..., description="Generated answer")
    sources: List[RetrievedChunk] = Field(default_factory=list, description="Source chunks")
    language: str = Field(..., description="Response language")
    model: str = Field(..., description="Model used")
    total_chunks: int = Field(..., description="Total chunks retrieved")
    cached: bool = Field(default=False, description="Response from cache")
    timing: Optional[TimingInfo] = Field(None, description="Per-stage latency (ms)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "answer": "Binary search tree - это структура данных...",
                "sources": [
                    {
                        "id": "abc123",
                        "score": 0.92,
                        "text": "Binary search tree is...",
                        "course_id": "ASD-2024",
                        "course_name": "Algorithms",
                        "topic": "Trees",
                    }
                ],
                "language": "ru",
                "model": "Qwen/Qwen2.5-32B-Instruct",
                "total_chunks": 5,
                "cached": False,
            }
        }
