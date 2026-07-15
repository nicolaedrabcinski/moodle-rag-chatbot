# 🚀 Техники оптимизации LLM без потери качества

## 1. **Квантизация весов**

### ✅ 8-bit квантизация (LLM.int8)
**Используем сейчас!**
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    load_in_8bit=True,  # ← Используем
    device_map="auto"
)
```
- **Экономия**: 2x памяти (28GB → 14GB)
- **Потеря качества**: ~0% (практически нет)
- **Скорость**: ~1.2x медленнее из-за dequantization

### ⚡ 4-bit квантизация (GPTQ/AWQ)
```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",  # NormalFloat4
    bnb_4bit_use_double_quant=True,  # Двойная квантизация
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto"
)
```
- **Экономия**: 4x памяти (28GB → 7GB)
- **Потеря качества**: 0.5-1% (минимальная)
- **Скорость**: ~1.5x медленнее

### 🔥 GGUF (llama.cpp формат)
- Для CPU inference
- Квантизации: Q2, Q3, Q4, Q5, Q6, Q8
- Не подходит для наших GPU бенчмарков

## 2. **Оптимизация внимания (Attention)**

### ✅ Flash Attention 2
```python
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    attn_implementation="flash_attention_2",  # ← Добавим
    torch_dtype=torch.float16,
    device_map="auto"
)
```
- **Экономия**: 10-20x меньше памяти для attention
- **Ускорение**: 2-4x быстрее
- **Потеря качества**: 0% (математически эквивалентно)
- **Требует**: `pip install flash-attn`

### ⚡ Scaled Dot Product Attention (SDPA)
```python
attn_implementation="sdpa"  # Встроено в PyTorch 2.0+
```
- **Ускорение**: 1.5-2x
- **Потеря качества**: 0%

## 3. **Компиляция и оптимизация кода**

### 🔥 Torch Compile (PyTorch 2.0+)
```python
import torch
model = torch.compile(model, mode="reduce-overhead")
```
- **Ускорение**: 1.5-2x
- **Потеря качества**: 0%
- **Требует**: PyTorch 2.0+

### ✅ BetterTransformer
```python
model = model.to_bettertransformer()
```
- **Ускорение**: 1.2-1.5x
- **Потеря качества**: 0%

## 4. **Оптимизация типов данных**

### ✅ Mixed Precision (FP16/BF16)
```python
torch_dtype=torch.float16  # или torch.bfloat16
```
- **Экономия**: 2x памяти
- **Потеря качества**: 0-0.5%
- **BF16 лучше для стабильности**

## 5. **Оптимизация inference**

### ⚡ Greedy Decoding (вместо sampling)
```python
do_sample=False,  # Greedy вместо sampling
num_beams=1       # Без beam search
```
- **Ускорение**: 2-3x
- **Потеря качества**: Детерминистичный вывод

### 🔥 Speculative Decoding
- Использует маленькую модель для предсказания
- Ускорение: 2-3x
- Требует две модели

### ⚡ KV Cache Optimization
```python
use_cache=True  # Кэширование ключей/значений
```
- Стандартно включено

## 6. **Батчинг и параллелизм**

### ✅ Dynamic Batching
```python
from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model=model,
    batch_size=8,  # Обработка нескольких запросов
    device_map="auto"
)
```

## 📊 **РЕКОМЕНДУЕМАЯ КОНФИГУРАЦИЯ** (без потери качества):

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

# Квантизация 8-bit (0% потери качества)
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0,
    llm_int8_has_fp16_weight=False
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    attn_implementation="flash_attention_2",  # 2-4x ускорение
    torch_dtype=torch.bfloat16,  # Стабильная точность
    device_map="auto",
    trust_remote_code=True
)

# Опционально: torch.compile для дополнительного ускорения
model = torch.compile(model, mode="reduce-overhead")

# Pipeline с оптимизациями
pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    do_sample=False,  # Greedy decoding (быстрее)
    pad_token_id=tokenizer.eos_token_id
)
```

## 🎯 **ИТОГОВЫЕ ОПТИМИЗАЦИИ:**

| Техника | Экономия памяти | Ускорение | Потеря качества |
|---------|----------------|-----------|-----------------|
| 8-bit квантизация | 2x | 0.8x | 0% |
| Flash Attention 2 | 10-20x (attention) | 2-4x | 0% |
| BF16 precision | 2x | 1.2x | 0% |
| Torch compile | - | 1.5-2x | 0% |
| Greedy decoding | - | 2-3x | - |
| **ИТОГО** | **4x** | **5-10x** | **~0%** |

## 🚀 **ДЛЯ МАКСИМАЛЬНОГО КАЧЕСТВА:**

Используй:
1. ✅ 8-bit квантизация (не 4-bit!)
2. ✅ Flash Attention 2
3. ✅ BFloat16
4. ✅ Torch compile
5. ✅ Greedy decoding (для бенчмарков)

**Итог**: 32B модель в 16GB RAM с качеством как у FP32!
