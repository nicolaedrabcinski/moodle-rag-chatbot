"""
Qdrant vector database client for course materials storage and retrieval.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


class QdrantStorage:
    """
    Qdrant vector database client for storing and searching course embeddings.

    Handles:
    - Collection management
    - Document storage with metadata
    - Similarity search
    - Filtering by course_id
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Collection name
            api_key: API key (optional)
        """
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection
        self.api_key = api_key or settings.qdrant_api_key

        logger.info(
            "Initializing Qdrant client",
            host=self.host,
            port=self.port,
            collection=self.collection_name,
        )

        self.client = QdrantClient(
            host=self.host,
            port=self.port,
            api_key=self.api_key,
            timeout=30,
            https=False,  # Disable HTTPS for local development
        )

        # Verify connection
        try:
            self.client.get_collections()
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            logger.error("Failed to connect to Qdrant", error=str(e))
            raise

    def collection_exists(self) -> bool:
        """
        Check if collection exists.

        Returns:
            bool: True if collection exists
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(col.name == self.collection_name for col in collections)
            logger.debug("Collection existence check", exists=exists)
            return exists
        except Exception as e:
            logger.error("Failed to check collection existence", error=str(e))
            return False

    def create_collection(
        self,
        vector_size: Optional[int] = None,
        distance: Optional[str] = None,
        on_disk: bool = False,
    ) -> None:
        """
        Create collection with HNSW index.

        Args:
            vector_size: Vector dimension (default: from settings)
            distance: Distance metric (default: from settings)
            on_disk: Store vectors on disk (for large datasets)
        """
        if self.collection_exists():
            logger.info("Collection already exists", collection=self.collection_name)
            return

        vector_size = vector_size or settings.embedding_dimension
        distance_metric = distance or settings.qdrant_distance_metric

        # Map distance metric to Qdrant enum
        distance_map = {
            "Cosine": models.Distance.COSINE,
            "Euclidean": models.Distance.EUCLID,
            "Dot": models.Distance.DOT,
        }
        distance_obj = distance_map.get(distance_metric, models.Distance.COSINE)

        logger.info(
            "Creating collection",
            collection=self.collection_name,
            vector_size=vector_size,
            distance=distance_metric,
        )

        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=distance_obj,
                    on_disk=on_disk,
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=settings.qdrant_hnsw_m,
                    ef_construct=settings.qdrant_hnsw_ef_construct,
                    on_disk=on_disk,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=10000,
                ),
            )

            # Create payload index for course_id filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="course_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            logger.info("Collection created successfully")
        except Exception as e:
            logger.error("Failed to create collection", error=str(e))
            raise

    def delete_collection(self) -> None:
        """Delete collection."""
        if not self.collection_exists():
            logger.warning("Collection does not exist", collection=self.collection_name)
            return

        logger.info("Deleting collection", collection=self.collection_name)
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info("Collection deleted successfully")
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise

    def create_collection_hybrid(
        self,
        vector_size: Optional[int] = None,
        distance: Optional[str] = None,
    ) -> None:
        """Create collection with named dense + sparse vector configs for hybrid search."""
        if self.collection_exists():
            logger.info("Collection already exists", collection=self.collection_name)
            return

        vector_size = vector_size or settings.embedding_dimension
        distance_map = {"Cosine": models.Distance.COSINE, "Euclidean": models.Distance.EUCLID, "Dot": models.Distance.DOT}
        distance_obj = distance_map.get(distance or settings.qdrant_distance_metric, models.Distance.COSINE)

        logger.info("Creating hybrid collection", collection=self.collection_name)
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={"dense": models.VectorParams(size=vector_size, distance=distance_obj)},
                sparse_vectors_config={"sparse": models.SparseVectorParams()},
                hnsw_config=models.HnswConfigDiff(
                    m=settings.qdrant_hnsw_m,
                    ef_construct=settings.qdrant_hnsw_ef_construct,
                ),
                optimizers_config=models.OptimizersConfigDiff(indexing_threshold=10000),
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="course_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self._hybrid_mode = True
            logger.info("Hybrid collection created successfully")
        except Exception as e:
            logger.error("Failed to create hybrid collection", error=str(e))
            raise

    def upsert_points_hybrid(
        self,
        dense_vectors: List[List[float]],
        sparse_indices: List[List[int]],
        sparse_values: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> None:
        """Upsert points with both dense and sparse vectors."""
        if not ids:
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(dense_vectors))]

        logger.info("Upserting hybrid points", num_points=len(dense_vectors))
        for i in range(0, len(dense_vectors), batch_size):
            sl = slice(i, i + batch_size)
            points = [
                models.PointStruct(
                    id=pid,
                    vector={
                        "dense": dv,
                        "sparse": models.SparseVector(indices=si, values=sv),
                    },
                    payload=pl,
                )
                for pid, dv, si, sv, pl in zip(
                    ids[sl], dense_vectors[sl], sparse_indices[sl], sparse_values[sl], payloads[sl]
                )
            ]
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                logger.error("Failed to upsert hybrid batch", error=str(e))
                raise
        logger.info("All hybrid points upserted successfully")

    async def search_hybrid_async(
        self,
        dense_vector: List[float],
        sparse_indices: List[int],
        sparse_values: List[float],
        limit: int = 5,
        prefetch_limit: int = 20,
        course_id: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Hybrid dense+sparse search using Qdrant's built-in RRF fusion."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._search_hybrid,
            dense_vector,
            sparse_indices,
            sparse_values,
            limit,
            prefetch_limit,
            course_id,
        )

    def _search_hybrid(
        self,
        dense_vector: List[float],
        sparse_indices: List[int],
        sparse_values: List[float],
        limit: int,
        prefetch_limit: int,
        course_id: Optional[str],
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        query_filter = None
        if course_id:
            query_filter = models.Filter(must=[
                models.FieldCondition(key="course_id", match=models.MatchValue(value=course_id))
            ])
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=prefetch_limit,
                        filter=query_filter,
                    ),
                    models.Prefetch(
                        query=models.SparseVector(indices=sparse_indices, values=sparse_values),
                        using="sparse",
                        limit=prefetch_limit,
                        filter=query_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [(str(p.id), p.score, p.payload) for p in results.points if p.payload]
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            raise

    def upsert_points(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> None:
        """
        Insert or update points in collection.

        Args:
            vectors: List of embeddings
            payloads: List of metadata dicts
            ids: Optional list of IDs (auto-generated if None)
            batch_size: Batch size for upload
        """
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors and payloads must match")

        if ids and len(ids) != len(vectors):
            raise ValueError("Number of IDs must match number of vectors")

        logger.info(
            "Upserting points",
            num_points=len(vectors),
            batch_size=batch_size,
        )

        # Generate IDs if not provided
        if not ids:
            import uuid

            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]

        # Upload in batches
        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            points = [
                models.PointStruct(id=point_id, vector=vector, payload=payload)
                for point_id, vector, payload in zip(batch_ids, batch_vectors, batch_payloads)
            ]

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                logger.debug(
                    "Batch uploaded",
                    batch_num=i // batch_size + 1,
                    batch_size=len(points),
                )
            except Exception as e:
                logger.error("Failed to upsert batch", batch_num=i // batch_size + 1, error=str(e))
                raise

        logger.info("All points upserted successfully")

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        course_id: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding
            limit: Number of results
            score_threshold: Minimum similarity score
            course_id: Filter by course ID

        Returns:
            List of (id, score, payload) tuples
        """
        # Build filter
        query_filter = None
        if course_id:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="course_id",
                        match=models.MatchValue(value=course_id),
                    )
                ]
            )

        logger.debug(
            "Searching",
            limit=limit,
            score_threshold=score_threshold,
            course_id=course_id,
        )

        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )

            formatted_results = [
                (str(point.id), point.score, point.payload) 
                for point in results.points if point.payload
            ]

            logger.debug("Search completed", num_results=len(formatted_results))
            return formatted_results

        except Exception as e:
            logger.error("Search failed", error=str(e))
            raise

    async def upsert_points_async(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> None:
        """Non-blocking wrapper around upsert_points() for use in async contexts."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self.upsert_points, vectors, payloads, ids, batch_size
        )

    async def search_async(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        course_id: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Non-blocking wrapper around search() for use in async contexts."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.search, query_vector, limit, score_threshold, course_id
        )

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection information.

        Returns:
            Dict with collection stats
        """
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "status": info.status.value if hasattr(info.status, 'value') else str(info.status),
                "optimizer_status": info.optimizer_status.value if hasattr(info.optimizer_status, 'value') else str(info.optimizer_status),
            }
        except Exception as e:
            logger.error("Failed to get collection info", error=str(e))
            raise

    def count_points(self, course_id: Optional[str] = None) -> int:
        """
        Count points in collection.

        Args:
            course_id: Filter by course ID

        Returns:
            int: Number of points
        """
        query_filter = None
        if course_id:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="course_id",
                        match=models.MatchValue(value=course_id),
                    )
                ]
            )

        try:
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=query_filter,
                exact=True,
            )
            return result.count
        except Exception as e:
            logger.error("Failed to count points", error=str(e))
            return 0

    def delete_by_course_id(self, course_id: str) -> None:
        """
        Delete all points for a course.

        Args:
            course_id: Course ID to delete
        """
        logger.info("Deleting course points", course_id=course_id)

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="course_id",
                                match=models.MatchValue(value=course_id),
                            )
                        ]
                    )
                ),
            )
            logger.info("Course points deleted", course_id=course_id)
        except Exception as e:
            logger.error("Failed to delete course points", course_id=course_id, error=str(e))
            raise


# Global storage instance
_storage: Optional[QdrantStorage] = None


def get_qdrant_storage() -> QdrantStorage:
    """
    Get global Qdrant storage instance (singleton).

    Returns:
        QdrantStorage: Qdrant storage instance
    """
    global _storage
    if _storage is None:
        _storage = QdrantStorage()
    return _storage
