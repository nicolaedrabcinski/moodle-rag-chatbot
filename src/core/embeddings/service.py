"""
Embedding service using multilingual-e5-large with batch processing.
"""

import asyncio
from typing import List, Optional, Union

import torch
from sentence_transformers import SentenceTransformer

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


class EmbeddingService:
    """
    Embedding service for generating dense vector representations.

    Uses multilingual-e5-large model with batch processing and GPU acceleration.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """
        Initialize embedding service.

        Args:
            model_name: Model name (default: from settings)
            device: Device (cuda/cpu, default: from settings)
            batch_size: Batch size for processing (default: from settings)
        """
        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.batch_size = batch_size or settings.embedding_batch_size

        # Check CUDA availability
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"

        logger.info(
            "Initializing embedding service",
            model=self.model_name,
            device=self.device,
            batch_size=self.batch_size,
        )

        # Load model
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.model.eval()  # Set to evaluation mode

        # Get embedding dimension
        self.dimension = self.model.get_sentence_embedding_dimension()

        logger.info(
            "Embedding service initialized",
            dimension=self.dimension,
            max_seq_length=self.model.max_seq_length,
        )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        normalize: bool = True,
        show_progress_bar: bool = False,
    ) -> Union[List[float], List[List[float]]]:
        """
        Encode text(s) to embeddings (synchronous).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size (default: from settings)
            normalize: Normalize embeddings to unit length
            show_progress_bar: Show progress bar

        Returns:
            Embeddings (single or list)
        """
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        batch_size = batch_size or self.batch_size

        logger.debug(
            "Encoding texts",
            num_texts=len(texts),
            batch_size=batch_size,
            device=self.device,
        )

        try:
            with torch.no_grad():
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress_bar,
                    convert_to_numpy=True,
                )

            # Convert to list
            embeddings_list = embeddings.tolist()

            logger.debug(
                "Encoding successful",
                num_embeddings=len(embeddings_list),
                embedding_dim=len(embeddings_list[0]) if embeddings_list else 0,
            )

            return embeddings_list[0] if is_single else embeddings_list

        except Exception as e:
            logger.error("Encoding failed", error=str(e), num_texts=len(texts))
            raise

    async def encode_async(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        normalize: bool = True,
    ) -> Union[List[float], List[List[float]]]:
        """
        Encode text(s) to embeddings (asynchronous).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size
            normalize: Normalize embeddings

        Returns:
            Embeddings (single or list)
        """
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.encode,
            texts,
            batch_size,
            normalize,
            False,
        )

    def encode_query(self, query: str, normalize: bool = True) -> List[float]:
        """
        Encode query with special prefix for E5 models.

        E5 models benefit from "query: " prefix for queries.

        Args:
            query: Query text
            normalize: Normalize embedding

        Returns:
            List[float]: Query embedding
        """
        # Add E5 query prefix
        prefixed_query = f"query: {query}"
        return self.encode(prefixed_query, normalize=normalize)

    async def encode_query_async(self, query: str, normalize: bool = True) -> List[float]:
        """
        Encode query asynchronously with E5 prefix.

        Args:
            query: Query text
            normalize: Normalize embedding

        Returns:
            List[float]: Query embedding
        """
        prefixed_query = f"query: {query}"
        return await self.encode_async(prefixed_query, normalize=normalize)

    def encode_documents(
        self,
        documents: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = True,
        show_progress_bar: bool = True,
    ) -> List[List[float]]:
        """
        Encode documents with special prefix for E5 models.

        E5 models benefit from "passage: " prefix for documents.

        Args:
            documents: List of documents
            batch_size: Batch size
            normalize: Normalize embeddings
            show_progress_bar: Show progress bar

        Returns:
            List of embeddings
        """
        # Add E5 passage prefix
        prefixed_docs = [f"passage: {doc}" for doc in documents]

        logger.info(
            "Encoding documents",
            num_documents=len(documents),
            batch_size=batch_size or self.batch_size,
        )

        embeddings = self.encode(
            prefixed_docs,
            batch_size=batch_size,
            normalize=normalize,
            show_progress_bar=show_progress_bar,
        )

        return embeddings

    async def encode_documents_async(
        self,
        documents: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = True,
    ) -> List[List[float]]:
        """
        Encode documents asynchronously with E5 prefix.

        Args:
            documents: List of documents
            batch_size: Batch size
            normalize: Normalize embeddings

        Returns:
            List of embeddings
        """
        prefixed_docs = [f"passage: {doc}" for doc in documents]
        return await self.encode_async(prefixed_docs, batch_size=batch_size, normalize=normalize)

    def get_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            int: Embedding dimension
        """
        return self.dimension

    def get_max_sequence_length(self) -> int:
        """
        Get maximum sequence length.

        Returns:
            int: Max sequence length
        """
        return self.model.max_seq_length


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get global embedding service instance (singleton).

    Returns:
        EmbeddingService: Embedding service instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
