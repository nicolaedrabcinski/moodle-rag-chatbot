#!/usr/bin/env python3
"""
Initialize Qdrant database and create collection.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.config.logging import LoggerAdapter
from src.data_pipeline.storage import get_qdrant_storage

logger = LoggerAdapter(__name__)


def main() -> None:
    """Initialize Qdrant collection."""
    logger.info("Starting Qdrant initialization")

    try:
        storage = get_qdrant_storage()

        # Check if collection exists
        if storage.collection_exists():
            logger.info("Collection already exists", collection=settings.qdrant_collection)
            response = input("Do you want to recreate it? (yes/no): ")
            if response.lower() in ["yes", "y"]:
                logger.info("Deleting existing collection")
                storage.delete_collection()
            else:
                logger.info("Keeping existing collection")
                return

        # Create collection
        logger.info("Creating collection", collection=settings.qdrant_collection)
        storage.create_collection()

        # Get collection info
        info = storage.get_collection_info()
        logger.info("Collection created successfully", info=info)

        print("\n✅ Qdrant database initialized successfully!")
        print(f"   Collection: {settings.qdrant_collection}")
        print(f"   Vector size: {settings.embedding_dimension}")
        print(f"   Distance metric: {settings.qdrant_distance_metric}")
        print(f"   Status: {info['status']}")

    except Exception as e:
        logger.error("Failed to initialize Qdrant", error=str(e), exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
