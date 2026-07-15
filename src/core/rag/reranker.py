"""
Cross-encoder reranker using BGE-reranker-v2-m3.

Runs on CPU (GPU is fully occupied by vLLM).
Accepts top-K candidates from Qdrant and returns them re-sorted by
joint (query, passage) relevance — much more accurate than cosine similarity.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from sentence_transformers import CrossEncoder

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


class Reranker:
    """BGE-reranker-v2-m3 cross-encoder wrapper."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.reranker_model
        self.device = device or settings.reranker_device

        logger.info("Loading reranker", model=self.model_name, device=self.device)
        self.model = CrossEncoder(
            self.model_name,
            device=self.device,
            max_length=512,
        )
        logger.info("Reranker ready")

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[str, float, Dict[str, Any]]],
        top_k: int = 5,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Re-sort candidates by cross-encoder relevance score.

        Args:
            query: User query
            candidates: List of (chunk_id, vector_score, payload) from Qdrant
            top_k: Number of results to return

        Returns:
            Top-k candidates sorted by reranker score (descending)
        """
        if not candidates:
            return candidates

        pairs = [(query, c[2].get("text", "")[:512]) for c in candidates]
        scores = self.model.predict(pairs, show_progress_bar=False)

        ranked = sorted(
            zip(scores.tolist(), candidates),
            key=lambda x: x[0],
            reverse=True,
        )

        logger.debug(
            "Reranked candidates",
            input_count=len(candidates),
            output_count=min(top_k, len(ranked)),
            top_score=ranked[0][0] if ranked else 0,
        )

        return [c for _, c in ranked[:top_k]]

    async def rerank_async(
        self,
        query: str,
        candidates: List[Tuple[str, float, Dict[str, Any]]],
        top_k: int = 5,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Non-blocking rerank — runs cross-encoder in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.rerank, query, candidates, top_k)


_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
