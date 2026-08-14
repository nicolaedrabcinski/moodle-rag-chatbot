# Moodle RAG Chatbot — FCIM UTM

> Self-hosted educational AI assistant integrated into the ELSE Moodle platform at the Technical University of Moldova (UTM). Answers student questions using course materials via Retrieval-Augmented Generation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![Model](https://img.shields.io/badge/Model-Qwen2.5--14B--AWQ-red.svg)](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-AWQ)
[![Eval](https://img.shields.io/badge/LLM--judge%20score-3.65%20%2F%205-brightgreen.svg)]()

## Overview

The chatbot is embedded in Moodle as a block plugin (`block_aichatbot`). Students type questions in Romanian, Russian, or English and receive answers grounded in uploaded course materials, with inline source citations.

**Indexed content:** 13,305 chunks from 2 courses (ECD-2026, FILOS-2026)  
**Eval quality:** LLM-judge mean 3.65/5, retrieval hit rate 93.9%, no-info rate 3.1%  
**Access:** public HTTPS via Tailscale Funnel — `https://biovm00006.tail46c0ff.ts.net`

---

## Architecture

```
Browser / Moodle student
        │  HTTPS (Tailscale Funnel)
        ▼
  ┌─────────────────┐
  │  nginx :8090    │  path routing
  │  /   → Moodle   │
  │  /api/ → API    │
  └────────┬────────┘
           │
  ┌────────▼────────┐       ┌──────────────────┐
  │  Moodle :80     │       │  FastAPI :8010   │
  │  block_aichatbot│──────►│  RAG pipeline    │
  │  proxy.php      │       │  API key auth    │
  └─────────────────┘       └───────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
     ┌────────▼──────┐    ┌─────────▼──────┐    ┌────────▼────────┐
     │  Qdrant :6334 │    │  vLLM  :8011   │    │  Redis  :6379   │
     │  hybrid search│    │  Qwen2.5-14B   │    │  response cache │
     │  13,305 chunks│    │  AWQ, L4 GPU   │    │  TTL 7 days     │
     └───────────────┘    └────────────────┘    └─────────────────┘
```

### RAG Pipeline

1. **Multi-query expansion** — LLM generates 3 phrasings of the question
2. **Hybrid retrieval** — dense (multilingual-e5-large, 1024d) + sparse (BM25), top-25 candidates
3. **RRF fusion** — Reciprocal Rank Fusion merges multi-query results
4. **Cross-encoder rerank** — BGE-reranker-v2-m3 narrows to top-7 chunks
5. **Generation** — Qwen2.5-14B-Instruct-AWQ with numbered source context
6. **Source citations** — response includes `[1]`, `[2]` references rendered as UI pills

---

## Stack

| Component | Image / Model | Port |
|---|---|---|
| Moodle 3.9.24 | custom bitnami base | 80 |
| FastAPI backend | Python 3.10, uvicorn | 8010 |
| vLLM inference | vllm/vllm-openai:v0.6.3 | 8011 (host) |
| Qdrant | qdrant/qdrant:latest | 6334 (host) |
| Redis | redis:7-alpine | 6379 |
| MariaDB | mariadb:10.5 | internal |
| nginx | host | 8090 |

**Embedding model:** `intfloat/multilingual-e5-large` (1024d, GPU)  
**LLM:** `Qwen/Qwen2.5-14B-Instruct-AWQ` (quantized, 24GB L4 GPU)  
**Reranker:** `BAAI/bge-reranker-v2-m3` (CPU)

---

## Quick Start

### Prerequisites

- Ubuntu 22.04+, Docker + Docker Compose v2
- NVIDIA GPU with 16GB+ VRAM, CUDA 12.1+
- Tailscale installed (for public HTTPS access)

### 1. Clone and configure

```bash
git clone https://github.com/nicolaedrabcinski/moodle-rag-chatbot.git
cd moodle-rag-chatbot
cp .env.example .env        # edit API keys, model paths
```

### 2. Download models

```bash
# LLM (~28GB AWQ)
huggingface-cli download Qwen/Qwen2.5-14B-Instruct-AWQ \
  --local-dir models/Qwen--Qwen2.5-14B-Instruct-AWQ

# Embedding and reranker models download automatically on first run
```

### 3. Start services

```bash
# Moodle + DB
docker compose -f docker-compose.moodle.yml up -d

# Chatbot backend + vLLM (takes ~2 min for GPU warmup)
docker compose -f docker-compose.chatbot.yml up -d

# Check health
curl http://localhost:8010/health
```

### 4. Install Moodle plugin

```bash
# Plugin is bind-mounted automatically via docker-compose.moodle.yml
# Or zip and install via Moodle admin UI:
cd moodle_plugin && zip -r block_aichatbot.zip block_aichatbot/
# Upload at: Site administration → Plugins → Install plugins
```

### 5. Ingest course materials

```bash
# Place PDFs/DOCX/TXT in data/raw/<COURSE-ID>/
mkdir -p data/raw/ASD-2026
cp /path/to/lectures/*.pdf data/raw/ASD-2026/

# Ingest (hybrid dense+sparse, ~15 min for 500 pages)
source .venv/bin/activate
python scripts/ingestion/ingest_courses.py \
  --course-dir data/raw/ASD-2026 \
  --hybrid

# Or use the all-in-one script (creates Moodle course too):
python scripts/ingestion/add_course.py --course-id ASD-2026
```

### 6. Public HTTPS via Tailscale Funnel

```bash
# Start nginx routing
sudo systemctl start nginx

# Start Tailscale Funnel (systemd unit included)
sudo systemctl start tailscale-funnel

# Accessible at: https://<node>.tail<id>.ts.net
```

---

## Moodle Plugin

The plugin lives at `moodle_plugin/block_aichatbot/`. Key files:

| File | Purpose |
|---|---|
| `block_aichatbot.php` | Block class, UI HTML/CSS |
| `proxy.php` | Server-side SSE proxy (Moodle → API, adds auth header) |
| `settings.php` | Admin settings: API URL, API key |
| `amd/src/chatbot.js` | Frontend: streaming, source citation pills |

**Authentication:** API key is set in Moodle admin settings and injected server-side by `proxy.php`. The browser never sees the key.

### Plugin settings (Moodle admin)

| Setting | Value |
|---|---|
| API URL | `http://localhost:8010` |
| API Key | (from `docker-compose.chatbot.yml` → `API_KEY`) |

---

## API

All endpoints require `Authorization: Bearer <API_KEY>` except `/health`.

```
POST /api/chat         → non-streaming JSON response
POST /api/chat/stream  → SSE stream (token-by-token)
GET  /health           → {"status": "healthy"}
GET  /docs             → Swagger UI
```

### Streaming response format

```
data: {"type": "meta", "sources": [{"index": 1, "document": "ECD 2026", "topic": "14_gdpr", ...}]}
data: {"type": "token", "text": "GDPR "}
data: {"type": "token", "text": "reglementează "}
...
data: [DONE]
```

### Example

```bash
curl -X POST http://localhost:8010/api/chat/stream \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Ce este GDPR?", "language": "ro"}'
```

---

## Adding New Courses

```bash
# 1. List configured courses and their ingest status
python scripts/ingestion/add_course.py --list

# 2. Add a course (copies files, ingests, creates Moodle course, clears cache)
python scripts/ingestion/add_course.py \
  --course-id BD-2026 \
  --materials-dir /path/to/bd/pdfs

# 3. Or place files manually and re-ingest all courses with BM25 re-fit
python scripts/ingestion/ingest_courses.py --all --hybrid
```

Course metadata (names, descriptions) is in `data/courses_config.json`.

---

## Evaluation

LLM-as-judge evaluation using Qwen2.5-14B itself as judge. 844 questions across ECD-2026 and FILOS-2026.

```bash
python scripts/evaluation/evaluate.py \
  --dataset data/eval/dataset_v2.jsonl \
  --api-url http://localhost:8010 \
  --api-key <API_KEY> \
  --results-jsonl data/eval/results_v8.jsonl \
  --llm-url http://localhost:8011/v1 \
  --model "Qwen/Qwen2.5-14B-Instruct" \
  --concurrency 3
```

### Results (v8, current)

| Metric | Value |
|---|---|
| Mean score (1–5) | **3.65** |
| Retrieval hit rate | 93.9% |
| No-info rate | 3.1% |
| p50 latency | 28s |
| Questions evaluated | 844 |

| Course | n | Score | Hit rate |
|---|---|---|---|
| ECD-2026 | 424 | 3.62 | 398/424 (93.9%) |
| FILOS-2026 | 416 | 3.68 | 391/416 (94.0%) |

---

## Project Structure

```
.
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app, auth middleware
│   │   └── routes/
│   │       ├── chat.py          # /chat and /chat/stream endpoints
│   │       └── health.py
│   └── core/
│       ├── config/
│       │   ├── settings.py      # env-based config
│       │   └── prompts.py       # system prompts (ro/ru/en)
│       ├── embeddings/service.py
│       ├── llm/client.py
│       └── rag/
│           ├── pipeline.py      # multi-query, RRF, rerank, generate
│           ├── bm25_encoder.py  # sparse BM25 vectors
│           └── models.py        # Pydantic request/response models
├── moodle_plugin/
│   └── block_aichatbot/
│       ├── block_aichatbot.php  # Moodle block, UI
│       ├── proxy.php            # Server-side SSE proxy
│       ├── settings.php
│       └── amd/src/chatbot.js   # Frontend streaming + source pills
├── scripts/
│   ├── ingestion/
│   │   ├── ingest_courses.py    # batch ingest
│   │   └── add_course.py        # add single course + Moodle course
│   └── evaluation/
│       └── evaluate.py          # LLM-as-judge eval
├── data/
│   ├── courses_config.json      # course id → name/description
│   ├── raw/                     # source PDFs and TXT per course
│   ├── bm25_vocab.json          # fitted BM25 vocabulary
│   └── eval/                    # eval datasets and results
├── docker-compose.chatbot.yml   # backend + vLLM
├── docker-compose.moodle.yml    # Moodle + MariaDB
└── docker/
    ├── chatbot/Dockerfile
    └── moodle/
```

---

## Server

Production environment:

- **OS:** Ubuntu 24.04
- **CPU:** 64 cores
- **RAM:** 125 GB
- **GPU:** NVIDIA L4 (24 GB VRAM)
- **LAN IP:** 10.202.40.130
- **Public URL:** `https://biovm00006.tail46c0ff.ts.net` (Tailscale Funnel)

---

## License

MIT
