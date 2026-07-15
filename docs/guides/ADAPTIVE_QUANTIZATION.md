# Стратегия Адаптивной Квантизации

## Принцип

**Используем квантизацию ТОЛЬКО когда это необходимо**

- ✅ **Модели ≤10B параметров**: БЕЗ квантизации (float16) - **максимальное качество**
- ⚡ **Модели >10B параметров**: 4-bit квантизация (NF4) - **единственный способ поместиться**

## GPU Память (NVIDIA L4 24GB)

### Без квантизации (float16 - 2 bytes/параметр)

| Размер модели | GPU память | Overhead (+15%) | Статус |
|---------------|------------|-----------------|--------|
| 1.5B | 3.0 GB | 3.4 GB | ✅ БЕЗ квантизации |
| 3B | 6.0 GB | 6.9 GB | ✅ БЕЗ квантизации |
| 7B | 14.0 GB | 16.1 GB | ✅ БЕЗ квантизации |
| 8B | 16.0 GB | 18.4 GB | ✅ БЕЗ квантизации |
| 9B | 18.0 GB | 20.7 GB | ✅ БЕЗ квантизации |
| 14B | 28.0 GB | 32.2 GB | ❌ 4-BIT квантизация |
| 32B | 64.0 GB | 73.6 GB | ❌ 4-BIT квантизация |
| 35B | 70.0 GB | 80.5 GB | ❌ 4-BIT квантизация |

### С 4-bit квантизацией (NF4 - 0.5 bytes/параметр)

| Размер модели | GPU память | Overhead (+15%) | Статус |
|---------------|------------|-----------------|--------|
| 14B | 7.0 GB | 8.1 GB | ✅ Помещается |
| 32B | 16.0 GB | 18.4 GB | ✅ Помещается |
| 35B | 17.5 GB | 20.1 GB | ✅ Помещается |
| 70B | 35.0 GB | 40.3 GB | ❌ НЕ помещается |

## Распределение моделей (21 total)

### БЕЗ квантизации - 18 моделей

**Qwen (4):**
- Qwen 1.5B Instruct - 3.4 GB
- Qwen 3B Instruct - 6.9 GB  
- Qwen 7B Instruct - 16.1 GB
- Qwen Math 7B - 16.1 GB
- CodeQwen 7B - 16.1 GB

**Mistral (3):**
- Mistral 7B v0.3 - 16.1 GB
- Mistral Nemo - 16.1 GB
- Mixtral 8x7B - 16.1 GB

**Open Models (3):**
- OpenChat 8B - 18.4 GB
- Zephyr 7B - 16.1 GB
- OpenHermes 7B - 16.1 GB

**Microsoft (1):**
- Phi 3.5 Mini 3.8B - 8.7 GB

**Meta (1):**
- Llama 3.1 8B - 18.4 GB

**Google (1):**
- Gemma 2 9B - 20.7 GB

**Yi (2):**
- Yi 1.5 6B - 13.8 GB
- Yi 1.5 9B - 20.7 GB

**DeepSeek (2):**
- DeepSeek Coder 6.7B - 15.4 GB
- DeepSeek Math 7B - 16.1 GB

### С 4-bit квантизацией - 3 модели

**Qwen (2):**
- Qwen 14B Instruct - 8.1 GB (4-bit)
- Qwen 32B Instruct - 18.4 GB (4-bit)

**Cohere (1):**
- Command-R 35B - 20.1 GB (4-bit)

## Преимущества подхода

### 1. Максимальное качество для маленьких моделей
- 18 моделей (≤10B) работают в **float16** - **0% потери качества**
- Нет артефактов квантизации
- Быстрее генерация (нет overhead на деквантизацию)

### 2. Возможность использовать большие модели
- 3 модели (>10B) работают в **4-bit NF4** - всего ~1% потери качества
- Иначе они просто не поместятся в 24GB GPU

### 3. Оптимальное использование ресурсов
- Автоматический выбор режима в зависимости от размера модели
- Не тратим память на квантизацию там, где она не нужна

## Технические детали

### Конфигурация float16 (БЕЗ квантизации)
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,  # или torch.float16
    device_map="auto",
    attn_implementation="flash_attention_2",  # Ускорение attention
)
```

### Конфигурация 4-bit (С квантизацией)
```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",           # Normal Float 4-bit
    bnb_4bit_use_double_quant=True,      # Двойная квантизация
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
    attn_implementation="flash_attention_2",
)
```

## Использование

### Автоматический режим (рекомендуется)
```bash
./run_benchmark.py
```
Скрипт автоматически выберет режим для каждой модели.

### Принудительная квантизация
```bash
python scripts/benchmarks/benchmark_rag_adaptive.py models/MODEL_NAME --use-quantization
```

### Принудительно БЕЗ квантизации
```bash
python scripts/benchmarks/benchmark_rag_adaptive.py models/MODEL_NAME --no-quantization
```

## Ожидаемые результаты

### Качество (F1 Score)
- **Модели ≤10B (float16)**: Максимальное качество, baseline метрики
- **Модели >10B (4-bit)**: ~99% от качества float16 (потеря 0.5-1%)

### Скорость (с Flash Attention 2)
- **Модели ≤10B**: Быстрее на ~5-10% vs 4-bit (нет overhead на деквантизацию)
- **Модели >10B**: Те же ~20 tokens/sec для 32B модели

### Память GPU
- **Модели ≤10B**: 3-21 GB (в зависимости от размера)
- **Модели >10B**: 8-20 GB (4-bit квантизация)

## Файлы

- `scripts/benchmarks/benchmark_rag_adaptive.py` - новый benchmark скрипт
- `run_benchmark.py` - обновлен для использования adaptive скрипта
- `docs/guides/ADAPTIVE_QUANTIZATION.md` - эта документация

## Миграция со старой версии

Старые результаты (с 4-bit для всех):
```
benchmark_results/MODEL_NAME.json
```

Новые результаты (с адаптивной квантизацией):
```
benchmark_results/MODEL_NAME_adaptive.json
```

Это позволяет сравнить разницу в качестве между режимами!
