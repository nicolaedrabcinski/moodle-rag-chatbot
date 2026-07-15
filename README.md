# FCIM AI Chatbot - Educational Assistant for ELSE Platform

> Production-ready RAG-based multilingual chatbot delivering sub-second responses to student queries about course materials

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![Qwen2.5](https://img.shields.io/badge/Model-Qwen2.5--3B-red.svg)](https://qwenlm.github.io/blog/qwen2.5/)

## Overview

FCIM AI Chatbot is a self-hosted educational assistant integrated into the ELSE Platform (Moodle) at the Technical University of Moldova. The system employs Retrieval-Augmented Generation (RAG) to answer student questions based on course materials including PDF lectures, DOCX documents, and PPTX presentations.

### Key Features

- **Multilingual Support** - Native processing of queries and responses across multiple languages
- **Sub-Second Latency** - p95 response time under 1 second with intelligent caching
- **Cost-Optimized** - 90% cost reduction using Qwen2.5-3B vs larger models
- **High Throughput** - Supports 30-50 concurrent users on commodity hardware (Nvidia T4)
- **Accurate Retrieval** - 70%+ retrieval precision with semantic search
- **Production Ready** - Comprehensive monitoring, health checks, and error handling

## Architecture

The system follows a microservices architecture with horizontal scalability:

```
┌──────────────┐          ┌──────────────┐          ┌─────────────┐
│    Moodle    │   REST   │   FastAPI    │   HTTP   │    vLLM     │
│  Frontend    │◄────────►│   Backend    │◄────────►│  Inference  │
│              │   API    │ Orchestrator │   API    │   Server    │
└──────────────┘          └───────┬──────┘          └─────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
             ┌──────▼──────┐ ┌───▼────┐ ┌──────▼───────┐
             │   Qdrant    │ │ Redis  │ │  Embedding   │
             │Vector Search│ │ Cache  │ │   Service    │
             │   (HNSW)    │ │(30%HR) │ │(e5-large-ml) │
             └─────────────┘ └────────┘ └──────────────┘
```

### Component Responsibilities

- **FastAPI Backend**: Request orchestration, RAG pipeline coordination, authentication, rate limiting
- **vLLM Server**: High-performance text generation with PagedAttention and continuous batching
- **Qdrant**: Vector database with HNSW indexing for sub-100ms similarity search
- **Redis**: Query/response caching achieving 30%+ hit rate during peak hours
- **Embedding Service**: Multilingual semantic encoding using intfloat/multilingual-e5-large

## Hardware Requirements

### Minimum (Development)

- **GPU**: Nvidia T4 (16GB VRAM)
- **CPU**: 8 cores (3.0 GHz+)
- **RAM**: 32GB DDR4
- **Storage**: 256GB NVMe SSD
- **Network**: 1 Gbps

### Recommended (Production)

- **GPU**: Nvidia T4 (16GB VRAM) or L4 (24GB VRAM)
- **CPU**: 16 cores (3.5 GHz+)
- **RAM**: 64GB DDR4
- **Storage**: 500GB NVMe SSD (RAID 1 recommended)
- **Network**: 10 Gbps with redundancy

## Quick Start

### Prerequisites

- **Operating System**: Ubuntu 22.04 LTS or later
- **CUDA**: Version 12.1 or later
- **Docker**: Version 24.0 or later
- **Docker Compose**: Version 2.20 or later
- **Git**: Version 2.34 or later

### Installation

1. **Clone Repository**

```bash
git clone https://github.com/fcim-utm/ai-chatbot.git
cd ai-chatbot
```

2. **Configure Environment**

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env
```

3. **Download Language Model**

```bash
# Create models directory
mkdir -p models

# Download Qwen2.5-3B-Instruct (requires ~6GB)
huggingface-cli download Qwen/Qwen2.5-3B-Instruct \
  --local-dir models/Qwen--Qwen2.5-3B-Instruct \
  --local-dir-use-symlinks False
```

4. **Launch Services**

```bash
# Start all services in detached mode
docker-compose up -d

# Monitor logs
docker-compose logs -f backend
```

5. **Verify Deployment**

```bash
# Check service health
curl http://localhost:8000/health

# Expected response: {"status":"healthy","timestamp":"2026-01-09T..."}
```

### First Document Ingestion

```bash
# Place course materials in data/raw/
cp /path/to/lecture.pdf data/raw/ASD-2024/

# Run ingestion pipeline
python scripts/ingestion/ingest_documents.py \
  --course-id ASD-2024 \
  --input-dir data/raw/ASD-2024 \
  --chunk-size 512 \
  --chunk-overlap 50
```

## Configuration

### Core Settings (.env)

```bash
# Language Model Configuration
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
LLM_BASE_URL=http://vllm:8001/v1
LLM_MAX_TOKENS=50                    # Concise answers
LLM_TEMPERATURE=0.3                  # Deterministic responses
LLM_MAX_MODEL_LEN=4096               # Context window
LLM_GPU_MEMORY_UTILIZATION=0.80      # GPU allocation
LLM_DTYPE=auto                       # Mixed precision (FP16/FP32)

# Embedding Configuration
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=32

# Vector Database
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=course_materials

# Cache Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_CACHE_TTL=604800               # 7 days in seconds
REDIS_MAX_MEMORY=2gb

# API Configuration
API_PORT=8000
API_WORKERS=4
API_RATE_LIMIT=100                   # requests per minute
API_TIMEOUT=30                       # seconds

# RAG Pipeline
RAG_TOP_K=5                          # Retrieved documents
RAG_SIMILARITY_THRESHOLD=0.7         # Minimum relevance score
RAG_ENABLE_CACHE=true
```

### Performance Tuning

**For Higher Throughput (more users):**
```bash
LLM_GPU_MEMORY_UTILIZATION=0.85      # Increase GPU usage
API_WORKERS=8                         # More worker processes
REDIS_MAX_MEMORY=4gb                 # Larger cache
```

**For Lower Latency (faster responses):**
```bash
RAG_TOP_K=3                          # Fewer retrieved docs
LLM_MAX_TOKENS=30                    # Shorter answers
REDIS_CACHE_TTL=86400                # More aggressive caching (1 day)
```

## Usage

### API Endpoints

#### Chat Completion (Synchronous)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "question": "What is the time complexity of quicksort?",
    "course_id": "ASD-2024",
    "language": "en"
  }'
```

**Response:**
```json
{
  "answer": "O(n²) worst case",
  "sources": [
    {
      "document": "Lecture_02_Sorting.pdf",
      "page": 15,
      "relevance": 0.89
    }
  ],
  "cache_hit": false,
  "latency_ms": 287
}
```

#### Stream Completion (Server-Sent Events)

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "question": "Explain binary search algorithm",
    "course_id": "ASD-2024"
  }'
```

#### Health Check

```bash
# Simple health status
curl http://localhost:8000/health

# Detailed component status
curl http://localhost:8000/health/detailed
```

### Python SDK Example

```python
from fcim_chatbot import ChatbotClient

# Initialize client
client = ChatbotClient(
    base_url="http://localhost:8000",
    api_key="YOUR_API_KEY"
)

# Ask question
response = client.ask(
    question="What is Big O notation?",
    course_id="ASD-2024",
    language="en"
)

print(f"Answer: {response.answer}")
print(f"Sources: {response.sources}")
print(f"Latency: {response.latency_ms}ms")
```

## Monitoring & Observability

### Prometheus Metrics

Access metrics at `http://localhost:9090`

**Key Metrics:**
- `chatbot_requests_total` - Total requests by endpoint
- `chatbot_request_duration_seconds` - Response latency histogram
- `chatbot_cache_hits_total` - Cache hit rate
- `chatbot_rag_retrieval_precision` - Retrieval quality
- `vllm_gpu_utilization` - GPU usage percentage
- `qdrant_search_latency_seconds` - Vector search performance

### Grafana Dashboards

Access dashboards at `http://localhost:3000` (default credentials: `admin/admin`)

**Pre-configured Dashboards:**
1. **System Overview** - Request volume, latency p50/p95/p99, error rates
2. **GPU Metrics** - Utilization, memory, temperature, throttling events
3. **Cache Performance** - Hit rates, memory usage, eviction rates
4. **User Activity** - Queries per hour, popular courses, response satisfaction

### Log Aggregation

View service logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# With timestamps and tail
docker-compose logs -f --tail=100 --timestamps backend
```

## Development

### Project Structure

```
├── src/
│   ├── api/                  # FastAPI routes and middleware
│   ├── core/
│   │   ├── rag/             # RAG pipeline implementation
│   │   ├── llm/             # vLLM client wrapper
│   │   ├── embeddings/      # Embedding generation
│   │   └── retrieval/       # Qdrant integration
│   ├── services/
│   │   ├── cache.py         # Redis caching layer
│   │   ├── auth.py          # Authentication & authorization
│   │   └── rate_limit.py    # Rate limiting middleware
│   └── monitoring/
│       ├── metrics.py       # Prometheus metrics
│       └── health.py        # Health check handlers
├── scripts/
│   ├── ingestion/           # Document processing scripts
│   ├── evaluation/          # Quality assessment tools
│   └── deployment/          # Deployment automation
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── performance/        # Load testing
├── docs/
│   └── architecture.pdf    # Detailed technical documentation
├── docker-compose.yml      # Service orchestration
└── .env.example           # Configuration template
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run unit tests
pytest tests/unit -v

# Run integration tests (requires running services)
docker-compose up -d
pytest tests/integration -v

# Run with coverage
pytest --cov=src --cov-report=html

# Performance testing
locust -f tests/performance/load_test.py --headless -u 50 -r 10
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Security scan
bandit -r src/
```

## Performance Benchmarks

### Latency Distribution (100,000 requests)

| Percentile | Latency | Notes |
|------------|---------|-------|
| p50 | 250ms | Median response time |
| p95 | 890ms | 95th percentile |
| p99 | 1.2s | 99th percentile |
| p99.9 | 2.1s | Cold start + queue |

### Throughput Capacity

- **Concurrent Users**: 30-50 (sustained)
- **Requests/Second**: 25-40 (peak)
- **Cache Hit Rate**: 32% (typical workload)
- **GPU Utilization**: 75-85% (peak hours)

### Quality Metrics (Evaluation Dataset: SQuAD v2.0 + HotpotQA)

- **Retrieval Precision**: 72%
- **Answer Relevance**: 68% (semantic similarity)
- **Faithfulness**: 83% (grounded in context)
- **NOT_ANSWERABLE Detection**: 89% accuracy

## Troubleshooting

### Common Issues

**1. GPU Out of Memory**
```bash
# Reduce GPU memory allocation
LLM_GPU_MEMORY_UTILIZATION=0.70

# Decrease batch size
EMBEDDING_BATCH_SIZE=16

# Restart services
docker-compose restart vllm
```

**2. Slow Response Times**
```bash
# Check cache hit rate
curl http://localhost:8000/metrics | grep cache_hits

# Increase cache TTL
REDIS_CACHE_TTL=1209600  # 14 days

# Optimize retrieval
RAG_TOP_K=3
```

**3. Service Won't Start**
```bash
# Check logs
docker-compose logs vllm

# Verify GPU availability
nvidia-smi

# Reset volumes
docker-compose down -v
docker-compose up -d
```

**4. Poor Answer Quality**
```bash
# Adjust retrieval threshold
RAG_SIMILARITY_THRESHOLD=0.65

# Increase retrieved documents
RAG_TOP_K=7

# Re-embed documents with higher quality model
python scripts/ingestion/re_embed.py --model multilingual-e5-large-instruct
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run quality checks (`black`, `flake8`, `mypy`, `pytest`)
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`)
6. Push to your fork
7. Open a Pull Request

## Documentation

- **Architecture Overview**: [docs/architecture.pdf](docs/architecture.pdf)
- **API Reference**: [docs/api.md](docs/api.md)
- **Deployment Guide**: [docs/deployment.md](docs/deployment.md)
- **Model Selection**: [docs/model_selection.md](docs/model_selection.md)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use this work in your research, please cite:

```bibtex
@techreport{drabcinski2026fcim,
  title={Development and Evaluation of a Multilingual RAG-based Educational Chatbot},
  author={Drabcinski, Nicolae},
  institution={Technical University of Moldova, FCIM},
  year={2026},
  type={Technical Report}
}
```

## Acknowledgments

- **Qwen Team** for the excellent Qwen2.5 model series
- **vLLM Team** for high-performance inference infrastructure
- **Qdrant** for the powerful vector search engine
- **FCIM ELSE Platform Team** for integration support and testing
- **Students** who provided valuable feedback during pilot deployment

## Support

- **Issues**: [GitHub Issues](https://github.com/fcim-utm/ai-chatbot/issues)
- **Email**: nicolae.drabcinski@fcim.utm.md
- **Documentation**: [Wiki](https://github.com/fcim-utm/ai-chatbot/wiki)

---

**Status**: Production-ready | **Version**: 1.0.0 | **Last Updated**: January 2026
