#!/usr/bin/env python3
"""
Smoke test to verify all components are working.
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


async def test_health() -> bool:
    """Test health endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{settings.api_host}:{settings.api_port}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check: {data['status']}")
                print(f"   Services: {data.get('services', {})}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_chat() -> bool:
    """Test chat endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{settings.api_host}:{settings.api_port}/api/chat",
                json={
                    "question": "Hello, how are you?",
                    "language": "en",
                },
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Chat test passed")
                print(f"   Answer length: {len(data['answer'])} chars")
                print(f"   Sources: {data['total_chunks']}")
                return True
            else:
                print(f"❌ Chat test failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Chat test error: {e}")
        return False


async def test_qdrant() -> bool:
    """Test Qdrant connection."""
    try:
        from src.data_pipeline.storage import get_qdrant_storage

        storage = get_qdrant_storage()
        info = storage.get_collection_info()
        print(f"✅ Qdrant connected")
        print(f"   Collection: {info['name']}")
        print(f"   Points: {info['points_count']}")
        return True
    except Exception as e:
        print(f"❌ Qdrant error: {e}")
        return False


async def test_redis() -> bool:
    """Test Redis connection."""
    try:
        from src.services.cache import get_redis_cache

        cache = await get_redis_cache()
        if cache.redis:
            await cache.redis.ping()
            stats = cache.get_stats()
            print(f"✅ Redis connected")
            print(f"   Hit rate: {stats['hit_rate']:.2%}")
            return True
        else:
            print(f"⚠️  Redis disabled")
            return True
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


async def test_llm() -> bool:
    """Test LLM connection."""
    try:
        from src.core.llm import get_llm_client

        client = get_llm_client()
        is_healthy = await client.health_check()
        if is_healthy:
            print(f"✅ LLM server healthy")
            return True
        else:
            print(f"❌ LLM server unhealthy")
            return False
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return False


async def main() -> None:
    """Run all smoke tests."""
    print("🧪 Running Smoke Tests")
    print("=" * 50)
    print()

    results = {}

    # Test individual components
    print("Testing Components:")
    print("-" * 50)
    results["qdrant"] = await test_qdrant()
    print()
    results["redis"] = await test_redis()
    print()
    results["llm"] = await test_llm()
    print()

    # Test API
    print("Testing API:")
    print("-" * 50)
    results["health"] = await test_health()
    print()
    results["chat"] = await test_chat()
    print()

    # Summary
    print("=" * 50)
    print("Summary:")
    print("-" * 50)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test:12s}: {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
