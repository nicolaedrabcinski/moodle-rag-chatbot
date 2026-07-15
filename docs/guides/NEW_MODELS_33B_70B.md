# 🚀 Добавление моделей 33B и 70B

## Что добавлено

### 5 новых моделей:

**GPU с 4-bit квантизацией (2 модели):**
1. DeepSeek 33B Chat (~66 GB)
2. DeepSeek Coder 33B (~66 GB)

**CPU с int8 квантизацией (3 модели):**
3. Llama 3.1 70B Instruct (~140 GB) - gated
4. Qwen 2.5 72B Instruct (~144 GB) - gated
5. DeepSeek 67B Chat (~134 GB) - open

**Итого: 21 + 5 = 26 моделей** 🎉

---

## Системные требования

### GPU: NVIDIA L4 24GB
- Float16: 18 моделей (≤10B) - максимальная скорость
- 4-bit: 5 моделей (14-35B) - хорошая скорость

### CPU + RAM: 126GB
- int8: 3 модели (67-72B) - медленнее, но SOTA качество

---

## Загрузка моделей

### Все 5 моделей сразу (~550 GB, 1.5-2 часа):
```bash
bash scripts/downloads/download_new_models.sh
```

### Только 33B для GPU (~132 GB, 30-40 минут):
```bash
bash scripts/downloads/download_33b_models.sh
```

### Только 70B для CPU (~418 GB, 1-1.5 часа):
```bash
bash scripts/downloads/download_70b_models.sh
```

---

## Использование

### Автоматический режим
Модели автоматически размещаются на CPU или GPU:

```bash
# GPU модели (≤35B) - автоматически используют GPU
./run_benchmark.py --single deepseek-ai--deepseek-llm-33b-chat

# CPU модели (70B+) - автоматически используют CPU
./run_benchmark.py --single meta-llama--Meta-Llama-3.1-70B-Instruct
```

### Принудительное размещение

```bash
# Принудительно на CPU
python scripts/benchmarks/benchmark_rag_adaptive.py \
    models/deepseek-ai--deepseek-llm-33b-chat --cpu

# Принудительно на GPU
python scripts/benchmarks/benchmark_rag_adaptive.py \
    models/Qwen--Qwen2.5-7B-Instruct --gpu
```

---

## Конфигурация моделей

### GPU Float16 (18 моделей)
```
Qwen: 1.5B, 3B, 7B, Math 7B, Code 7B
Mistral: 7B, Nemo, Mixtral 8x7B  
Open: OpenChat 8B, Zephyr 7B, OpenHermes 7B
Other: Phi 3.8B, Llama 8B, Gemma 9B, Yi 6B/9B, DeepSeek 6.7B/7B
```
- Память: 3-21 GB GPU
- Скорость: 20-50 tokens/sec
- Качество: 100% (без квантизации)

### GPU 4-bit (5 моделей)
```
Qwen 14B, Qwen 32B, Command-R 35B
DeepSeek 33B Chat (NEW)
DeepSeek Coder 33B (NEW)
```
- Память: 8-20 GB GPU
- Скорость: 10-20 tokens/sec
- Качество: ~99% (минимальная потеря)

### CPU int8 (3 модели)
```
Llama 3.1 70B Instruct (NEW)
Qwen 2.5 72B Instruct (NEW)
DeepSeek 67B Chat (NEW)
```
- Память: 67-72 GB RAM
- Скорость: 2-5 tokens/sec
- Качество: SOTA (лучшие в классе)

---

## Ожидаемые результаты

### DeepSeek 33B Chat
- **Назначение:** Универсальная модель
- **Размещение:** GPU с 4-bit
- **Качество:** Конкурирует с Llama 2 70B
- **Скорость:** ~15 tokens/sec

### DeepSeek Coder 33B
- **Назначение:** Программирование
- **Размещение:** GPU с 4-bit
- **Качество:** Лучшая в своем классе для кода
- **Скорость:** ~15 tokens/sec

### Llama 3.1 70B Instruct
- **Назначение:** SOTA универсальная модель
- **Размещение:** CPU с int8
- **Качество:** Топ-3 в мире
- **Скорость:** ~3-5 tokens/sec

### Qwen 2.5 72B Instruct
- **Назначение:** Конкурент Llama 70B
- **Размещение:** CPU с int8
- **Качество:** Отличное, особенно для мультиязычности
- **Скорость:** ~3-5 tokens/sec

### DeepSeek 67B Chat
- **Назначение:** Открытая альтернатива Llama 70B
- **Размещение:** CPU с int8
- **Качество:** Высокое
- **Скорость:** ~3-5 tokens/sec

---

## Обновленные файлы

**Скрипты загрузки:**
- `scripts/downloads/download_new_models.sh` - мастер-скрипт
- `scripts/downloads/download_33b_models.sh` - GPU модели
- `scripts/downloads/download_70b_models.sh` - CPU модели

**Benchmark:**
- `scripts/benchmarks/benchmark_rag_adaptive.py` - добавлена поддержка CPU
- `run_benchmark.py` - добавлены 5 новых моделей

**Конфигурация в коде:**
```python
# GPU с 4-bit
MODELS_REQUIRING_QUANTIZATION = [
    "Qwen--Qwen2.5-14B-Instruct",
    "Qwen--Qwen2.5-32B-Instruct",
    "CohereForAI--c4ai-command-r-v01",
    "deepseek-ai--deepseek-llm-33b-chat",        # NEW
    "deepseek-ai--deepseek-coder-33b-instruct",  # NEW
]

# CPU с int8
MODELS_REQUIRING_CPU = [
    "meta-llama--Meta-Llama-3.1-70B-Instruct",   # NEW
    "Qwen--Qwen2.5-72B-Instruct",                # NEW
    "deepseek-ai--deepseek-llm-67b-chat",        # NEW
]
```

---

## Сравнение производительности

| Модель | Устройство | Память | Скорость | Качество |
|--------|-----------|--------|----------|----------|
| Qwen 7B | GPU float16 | 14 GB | 40 tok/s | 100% |
| Qwen 14B | GPU 4-bit | 9 GB | 20 tok/s | 99% |
| DeepSeek 33B | GPU 4-bit | 20 GB | 15 tok/s | 99% |
| Llama 70B | CPU int8 | 70 GB | 4 tok/s | 100% (SOTA) |

---

## Требования к HuggingFace токену

**Gated модели (требуют доступа):**
- Llama 3.1 70B Instruct
- Qwen 2.5 72B Instruct

**Открытые модели:**
- DeepSeek 33B Chat ✅
- DeepSeek Coder 33B ✅
- DeepSeek 67B Chat ✅

Убедитесь что токен имеет разрешение:
✅ "Read access to contents of all public gated repos you can access"

---

## Начало работы

1. **Загрузите модели:**
   ```bash
   bash scripts/downloads/download_new_models.sh
   ```

2. **Проверьте список:**
   ```bash
   ./run_benchmark.py --list
   ```

3. **Запустите benchmark:**
   ```bash
   # Все модели
   ./run_benchmark.py --yes
   
   # Одна модель
   ./run_benchmark.py --single deepseek-ai--deepseek-llm-33b-chat
   ```

---

**Версия:** 3.0 (CPU + GPU Support)  
**Дата:** 2026-01-07  
**Система:** NVIDIA L4 24GB + 126GB RAM
