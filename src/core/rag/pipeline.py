"""
RAG Pipeline with multi-query expansion, RRF merging, and cross-encoder reranking.
"""

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.config.logging import LoggerAdapter
from src.core.config.prompts import get_system_prompt
from src.core.embeddings import get_embedding_service
from src.core.llm import get_llm_client
from src.data_pipeline.storage import get_qdrant_storage

from .bm25_encoder import get_bm25_encoder
from .models import ChatRequest, ChatResponse, RetrievedChunk, TimingInfo
from .reranker import get_reranker

logger = LoggerAdapter(__name__)

# Prompt that asks the LLM to produce N alternative phrasings of the query.
# Temperature should be low (0.3) to stay on-topic; max_tokens=150 is enough.
_MULTI_QUERY_PROMPT = """Generează {n} reformulări alternative ale întrebării de mai jos.
Scopul este să acoperiți diferite unghiuri și formulări ale aceleiași întrebări.
Returnează DOAR o listă JSON de strings, fără explicații.

Întrebare: {question}

JSON:"""


def _rrf_merge(
    results_per_query: List[List[Tuple[str, float, Dict[str, Any]]]],
    k: int = 60,
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Reciprocal Rank Fusion across multiple retrieval result lists.

    score(doc) = Σ_i  1 / (k + rank_i(doc))

    Higher k → less aggressive rank discounting.
    k=60 is the standard value from the original RRF paper.
    """
    rrf_scores: Dict[str, float] = {}
    best_payload: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

    for results in results_per_query:
        for rank, (chunk_id, vec_score, payload) in enumerate(results):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            if chunk_id not in best_payload:
                best_payload[chunk_id] = (chunk_id, vec_score, payload)

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
    return [best_payload[cid] for cid in sorted_ids]


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.

    Steps:
    1. (Optional) Expand query into N variants via LLM
    2. Embed all variants and search Qdrant in parallel
    3. Merge results with Reciprocal Rank Fusion
    4. (Optional) Re-rank merged candidates with BGE-reranker-v2-m3
    5. Build context from top-k chunks
    6. Generate answer with LLM
    """

    def __init__(self) -> None:
        self.embedding_service = get_embedding_service()
        self.llm_client = get_llm_client()
        self.storage = get_qdrant_storage()
        self.reranker = get_reranker() if settings.rag_rerank else None
        self.bm25 = get_bm25_encoder()  # None if vocab file not present
        logger.info(
            "RAG pipeline initialised",
            multi_query=settings.rag_multi_query,
            rerank=settings.rag_rerank,
            hybrid_search=self.bm25 is not None,
        )

    # ------------------------------------------------------------------
    # Query expansion
    # ------------------------------------------------------------------

    async def _expand_query(self, question: str) -> List[str]:
        """
        Generate `rag_multi_query_count` alternative phrasings of `question`.
        Falls back to [question] on any error so retrieval still proceeds.
        """
        n = settings.rag_multi_query_count
        prompt = _MULTI_QUERY_PROMPT.format(n=n, question=question)
        try:
            raw = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=150,
                temperature=0.3,
            )
            start, end = raw.find("["), raw.rfind("]")
            if start == -1 or end == -1:
                return [question]
            variants = json.loads(raw[start : end + 1])
            variants = [v.strip() for v in variants if isinstance(v, str) and v.strip()]
            # Always include the original query
            all_queries = [question] + [v for v in variants if v != question]
            logger.debug("Query variants generated", count=len(all_queries))
            return all_queries[:n + 1]
        except Exception as e:
            logger.warning("Query expansion failed, using original", error=str(e))
            return [question]

    # ------------------------------------------------------------------
    # Main retrieve
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        course_id: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> Tuple[List[RetrievedChunk], float, float]:
        """
        Retrieve relevant chunks.

        Pipeline:
          1. Optionally expand query into variants via LLM
          2. Batch-embed all variants in ONE GPU call (avoids serialisation)
          3. Run Qdrant searches in parallel (one per embedding)
          4. Merge results with RRF
          5. Optionally rerank with cross-encoder (CPU)
          6. Return top_k as RetrievedChunk objects

        Returns:
            (chunks, embed_ms, search_ms)
        """
        top_k = top_k or settings.rag_top_k
        retrieve_k = settings.rag_retrieve_k
        score_threshold = score_threshold or settings.rag_similarity_threshold

        t0 = time.perf_counter()

        # Step 1: query expansion
        if settings.rag_multi_query:
            queries = await self._expand_query(query)
        else:
            queries = [query]

        # Step 2: batch embed all queries in a single GPU call
        # Prefix each with "query: " (E5 convention) — encode_async handles a list
        prefixed = [f"query: {q}" for q in queries]
        embeddings: List[List[float]] = await self.embedding_service.encode_async(
            prefixed, normalize=True
        )
        if isinstance(embeddings[0], float):
            # Single query returned a flat list — wrap it
            embeddings = [embeddings]  # type: ignore[assignment]

        embed_ms = (time.perf_counter() - t0) * 1000

        # Step 3: parallel Qdrant searches (one per embedding)
        t1 = time.perf_counter()

        if self.bm25 is not None:
            # Hybrid dense+sparse search — use primary query only (BM25 adds recall)
            sparse_idx, sparse_val = self.bm25.encode_query(query)
            search_tasks = [
                self.storage.search_hybrid_async(
                    dense_vector=embeddings[0],
                    sparse_indices=sparse_idx,
                    sparse_values=sparse_val,
                    limit=retrieve_k,
                    prefetch_limit=retrieve_k,
                    course_id=course_id,
                )
            ]
        else:
            search_tasks = [
                self.storage.search_async(
                    query_vector=emb,
                    limit=retrieve_k,
                    score_threshold=score_threshold,
                    course_id=course_id,
                )
                for emb in embeddings
            ]

        results_list = await asyncio.gather(*search_tasks, return_exceptions=False)

        # Step 4: RRF merge (only needed for multi-query dense mode)
        if len(results_list) > 1:
            merged = _rrf_merge(results_list)
        else:
            merged = results_list[0]

        # Step 5: cross-encoder rerank
        if self.reranker and merged:
            merged = await self.reranker.rerank_async(query, merged, top_k=top_k)
        else:
            merged = merged[:top_k]

        search_ms = (time.perf_counter() - t1) * 1000

        # Step 6: build RetrievedChunk objects
        chunks = []
        for chunk_id, score, payload in merged:
            chunks.append(
                RetrievedChunk(
                    id=chunk_id,
                    score=score,
                    text=payload.get("text", ""),
                    course_id=payload.get("course_id", ""),
                    course_name=payload.get("course_name", ""),
                    topic=payload.get("topic"),
                    file_path=payload.get("file_path"),
                    page_number=payload.get("page_number"),
                )
            )

        logger.info(
            "Retrieved chunks",
            queries=len(queries),
            candidates=len(merged),
            returned=len(chunks),
            embed_ms=round(embed_ms, 1),
            search_ms=round(search_ms, 1),
        )

        return chunks, embed_ms, search_ms

    # ------------------------------------------------------------------
    # Context + prompt building
    # ------------------------------------------------------------------

    def build_context(self, chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return "Нет доступной информации из материалов курса."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[{i}] {chunk.course_name}"
            if chunk.topic:
                source_info += f" — {chunk.topic}"
            if chunk.page_number:
                source_info += f", p.{chunk.page_number}"
            context_parts.append(f"{source_info}\n{chunk.text}")

        context = "\n\n---\n\n".join(context_parts)

        max_length = settings.rag_max_context_length
        if len(context) > max_length:
            logger.warning("Context truncated", original=len(context), max=max_length)
            context = context[:max_length] + "..."

        return context

    def build_prompt(self, query: str, context: str, language: str = "ru") -> str:
        system_prompt = get_system_prompt(language)
        return system_prompt.format(context=context, question=query)

    # ------------------------------------------------------------------
    # Generate (non-streaming)
    # ------------------------------------------------------------------

    async def generate(self, request: ChatRequest) -> ChatResponse:
        logger.info(
            "Processing chat request",
            question=request.question[:100],
            course_id=request.course_id,
        )

        t_start = time.perf_counter()

        chunks, embed_ms, search_ms = await self.retrieve(
            query=request.question,
            course_id=request.course_id,
        )

        context = self.build_context(chunks)
        prompt = self.build_prompt(request.question, context, request.language)

        t_llm = time.perf_counter()
        answer = await self.llm_client.generate(
            prompt=prompt,
            max_tokens=request.max_tokens or settings.llm_max_tokens,
            temperature=request.temperature or settings.llm_temperature,
        )
        llm_ms = (time.perf_counter() - t_llm) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000

        logger.info(
            "Generated response",
            embed_ms=round(embed_ms, 1),
            search_ms=round(search_ms, 1),
            llm_ms=round(llm_ms, 1),
            total_ms=round(total_ms, 1),
        )

        return ChatResponse(
            answer=answer.strip(),
            sources=chunks,
            language=request.language or "ru",
            model=settings.llm_model,
            total_chunks=len(chunks),
            cached=False,
            timing=TimingInfo(
                embed_ms=round(embed_ms, 1),
                search_ms=round(search_ms, 1),
                llm_ms=round(llm_ms, 1),
                total_ms=round(total_ms, 1),
            ),
        )

    # ------------------------------------------------------------------
    # Generate (streaming)
    # ------------------------------------------------------------------

    async def generate_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        logger.info(
            "Processing streaming chat request",
            question=request.question[:100],
            course_id=request.course_id,
        )

        chunks, embed_ms, search_ms = await self.retrieve(
            query=request.question,
            course_id=request.course_id,
        )

        context = self.build_context(chunks)
        prompt = self.build_prompt(request.question, context, request.language)

        yield json.dumps({
            "type": "meta",
            "sources": [
                {
                    "index": i,
                    "document": c.course_name,
                    "topic": c.topic,
                    "file_path": c.file_path,
                    "score": round(c.score, 3),
                }
                for i, c in enumerate(chunks, 1)
            ],
            "timing": {"embed_ms": round(embed_ms, 1), "search_ms": round(search_ms, 1)},
        })

        async for text_chunk in self.llm_client.generate_stream(
            prompt=prompt,
            max_tokens=request.max_tokens or settings.llm_max_tokens,
            temperature=request.temperature or settings.llm_temperature,
        ):
            yield json.dumps({"type": "token", "text": text_chunk})


# Singleton
_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
