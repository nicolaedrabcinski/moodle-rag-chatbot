#!/usr/bin/env python3
"""
Download models (LLM and Embedding) from HuggingFace.
"""

import argparse
import sys
from pathlib import Path

from huggingface_hub import snapshot_download
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


def download_model(
    model_name: str,
    output_dir: Path,
    revision: str = "main",
    cache_dir: Path | None = None,
) -> None:
    """
    Download model from HuggingFace.

    Args:
        model_name: Model name (e.g., Qwen/Qwen2.5-32B-Instruct)
        output_dir: Output directory
        revision: Model revision/branch
        cache_dir: Cache directory
    """
    logger.info("Downloading model", model=model_name, output=str(output_dir))

    try:
        snapshot_download(
            repo_id=model_name,
            local_dir=output_dir,
            revision=revision,
            cache_dir=cache_dir,
            resume_download=True,
            local_dir_use_symlinks=False,
        )

        logger.info("Model downloaded successfully", model=model_name)
        print(f"\n✅ Downloaded {model_name} to {output_dir}")

    except Exception as e:
        logger.error("Failed to download model", model=model_name, error=str(e))
        print(f"\n❌ Error downloading {model_name}: {e}")
        sys.exit(1)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Download models from HuggingFace")
    parser.add_argument(
        "--model",
        type=str,
        help="Model name to download (default: all configured models)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "models",
        help="Output directory",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="HuggingFace cache directory",
    )
    parser.add_argument(
        "--revision",
        type=str,
        default="main",
        help="Model revision/branch",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.model:
        # Download specific model
        model_name = args.model
        output_dir = args.output_dir / model_name.replace("/", "--")
        download_model(model_name, output_dir, args.revision, args.cache_dir)
    else:
        # Download all configured models
        print("Downloading configured models:")
        print(f"  1. LLM: {settings.llm_model}")
        print(f"  2. Embedding: {settings.embedding_model}")
        print()

        # Download LLM
        llm_output = args.output_dir / settings.llm_model.replace("/", "--")
        download_model(settings.llm_model, llm_output, args.revision, args.cache_dir)

        # Download Embedding model
        emb_output = args.output_dir / settings.embedding_model.replace("/", "--")
        download_model(settings.embedding_model, emb_output, args.revision, args.cache_dir)

        print("\n✅ All models downloaded successfully!")


if __name__ == "__main__":
    main()
