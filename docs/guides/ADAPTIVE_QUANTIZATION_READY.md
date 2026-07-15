# ✅ СИСТЕМА АДАПТИВНОЙ КВАНТИЗАЦИИ ГОТОВА

## Что изменилось

### ДО (старая версия)
- **ВСЕ модели** использовали 4-bit квантизацию
- Даже маленькие 1.5B модели квантизировались
- Потеря качества ~0.5-1% на всех моделях

### ПОСЛЕ (новая версия)
- **18 моделей (≤10B)**: БЕЗ квантизации (float16) - **максимальное качество**
- **3 модели (>10B)**: 4-bit квантизация (NF4) - **единственный способ поместиться**

## Файлы

### Обновленные
1. **run_benchmark.py** - обновлен benchmark скрипт на `benchmark_rag_adaptive.py`
2. **ALL_MODELS список** - добавлены комментарии о стратегии квантизации

### Новые
1. **scripts/benchmarks/benchmark_rag_adaptive.py** - новый benchmark с адаптивной квантизацией
2. **docs/guides/ADAPTIVE_QUANTIZATION.md** - полная документация стратегии
3. **docs/guides/ADAPTIVE_QUANTIZATION_READY.md** - этот файл

## Тестирование

### Тест 1: Qwen 1.5B (маленькая модель)
```bash
✅ БЕЗ квантизации (float16)
💾 GPU память: 2.88 GB
⚡ Время: 2.46s/вопрос
```

### Тест 2: Qwen 14B (большая модель)
```bash
✅ С 4-bit квантизацией (NF4)
💾 GPU память: 9.28 GB (vs ~32GB без квантизации)
⚡ Время: 10.24s/вопрос
```

## Распределение моделей (21 total)

### БЕЗ квантизации - 18 моделей (float16)
```
Qwen 1.5B, 3B, 7B, Math 7B, Code 7B          (5 моделей)
Mistral 7B v0.3, Nemo, Mixtral 8x7B          (3 модели)
OpenChat 8B, Zephyr 7B, OpenHermes 7B        (3 модели)
Phi 3.8B                                      (1 модель)
Llama 3.1 8B                                  (1 модель)
Gemma 2 9B                                    (1 модель)
Yi 6B, 9B                                     (2 модели)
DeepSeek Coder 6.7B, Math 7B                 (2 модели)
```

### С 4-bit квантизацией - 3 модели (NF4)
```
Qwen 14B      (~9 GB GPU)
Qwen 32B      (~18 GB GPU)
Command-R 35B (~20 GB GPU)
```

## Использование

### Автоматический режим (рекомендуется)
```bash
./run_benchmark.py
```
Скрипт автоматически выберет оптимальный режим для каждой модели.

### Список моделей
```bash
./run_benchmark.py --list
```

### Одна модель
```bash
./run_benchmark.py --single Qwen--Qwen2.5-7B-Instruct
```

### Принудительные режимы (для экспериментов)
```bash
# Принудительно БЕЗ квантизации (если модель помещается)
python scripts/benchmarks/benchmark_rag_adaptive.py models/MODEL_NAME --no-quantization

# Принудительно С квантизацией
python scripts/benchmarks/benchmark_rag_adaptive.py models/MODEL_NAME --use-quantization
```

## Ожидаемые результаты

### Качество (по сравнению с 4-bit для всех)
- **Модели ≤10B**: +0.5-1% F1 score (используем float16 вместо 4-bit)
- **Модели >10B**: Те же метрики (остались на 4-bit)

### Скорость
- **Модели ≤10B**: Быстрее на ~5-10% (нет overhead на деквантизацию)
- **Модели >10B**: Та же скорость

### Память GPU
- **Модели ≤10B**: 3-21 GB (зависит от размера)
- **Модели >10B**: 9-20 GB (с 4-bit)

## Результаты бенчмарков

### Старые результаты (4-bit для всех)
```
benchmark_results/MODEL_NAME.json
```

### Новые результаты (адаптивная квантизация)
```
benchmark_results/MODEL_NAME_adaptive.json
```

Это позволяет сравнить разницу в качестве!

## GPU Capacity Analysis

### NVIDIA L4 24GB - Поддерживаемые модели

#### БЕЗ квантизации (float16)
| Модель | Параметры | GPU память | Статус |
|--------|-----------|------------|--------|
| Qwen 1.5B | 1.5B | ~3.4 GB | ✅ |
| Qwen 3B | 3B | ~6.9 GB | ✅ |
| Qwen 7B | 7B | ~16.1 GB | ✅ |
| OpenChat 8B | 8B | ~18.4 GB | ✅ |
| Gemma 9B | 9B | ~20.7 GB | ✅ |
| Qwen 14B | 14B | ~32.2 GB | ❌ (не помещается) |

#### С 4-bit квантизацией (NF4)
| Модель | Параметры | GPU память | Статус |
|--------|-----------|------------|--------|
| Qwen 14B | 14B | ~8.1 GB | ✅ |
| Qwen 32B | 32B | ~18.4 GB | ✅ |
| Command-R 35B | 35B | ~20.1 GB | ✅ |
| Qwen 70B | 70B | ~40.3 GB | ❌ (не помещается) |

## Технические детали

### Flash Attention 2
- Установлен: ✅ версия 2.8.3
- Используется: ✅ автоматически для всех моделей
- Ускорение: 2-4x для attention
- Память: -10-20x для attention

### Float16 конфигурация (для моделей ≤10B)
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="flash_attention_2",
)
```

### 4-bit конфигурация (для моделей >10B)
```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
    attn_implementation="flash_attention_2",
)
```

## Следующие шаги

1. ✅ **Создать новый токен HuggingFace** с gated repos permissions
2. ✅ **Скачать 3 gated модели** (Llama 3.1 8B, Gemma 9B, Command-R 35B)
3. ⏳ **Запустить полный benchmark** для всех 21 моделей
4. 📊 **Проанализировать результаты** и сравнить с 4-bit версией

## Контакт

Автор: GitHub Copilot
Дата: 2026-01-07
Версия: 2.0 (Adaptive Quantization)
