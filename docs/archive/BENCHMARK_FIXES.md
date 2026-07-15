# 🔧 Исправления для запуска бенчмарка

## Проблемы и решения

### 1. ❌ Модели не загружаются - путь не найден

**Проблема:**
```
OSError: Can't load the configuration of '/models/Qwen/Qwen2.5-7B-Instruct'
```

**Причина:**
- Модели скачаны в HuggingFace cache формате: `Qwen--Qwen2.5-7B-Instruct`
- Скрипт передавал путь в формате: `Qwen/Qwen2.5-7B-Instruct`

**Решение:**
```bash
# В benchmark_master.sh добавлено:
local hf_model_name=$(echo "$model_path" | sed 's/\//--/g')
# Превращает Qwen/Qwen2.5-7B → Qwen--Qwen2.5-7B
```

### 2. ❌ GPU Out of Memory

**Проблема:**
```
ValueError: Free memory on device (20.98/23.54 GiB) is less than desired (21.18 GiB)
```

**Причина:**
- GPU utilization = 0.90 (90%)
- Модель 7B требует 21.18 GB, доступно только 20.98 GB

**Решение:**
```bash
# Снизили с 0.90 до 0.85:
--gpu-memory-utilization 0.85
```

### 3. ⚠️ Timeout слишком короткий

**Проблема:**
- Модель загружается 2-3 минуты
- Старый timeout: 60s + 20×5s = 160s

**Решение:**
```bash
# Увеличен timeout:
sleep 90  # было 60
max_attempts=40  # было 20
sleep 10  # было 5 между попытками
# Итого: 90 + 40×10 = 490 секунд (8 минут)
```

## ✅ Финальная конфигурация

### Правильный запуск Docker:

```bash
docker run -d --gpus all \
  --name vllm_gpu_server \
  -p 8001:8000 \
  -v /home/nicolaedrabcinski/llm_else/models:/models \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model "/models/Qwen--Qwen2.5-7B-Instruct" \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.85
```

### Структура моделей:

```
~/llm_else/models/
├── Qwen--Qwen2.5-7B-Instruct/
│   ├── config.json
│   ├── model-00001-of-00004.safetensors
│   └── ...
├── Qwen--Qwen2.5-3B-Instruct/
└── meta-llama--Meta-Llama-3.1-8B-Instruct/
```

## 🎯 Проверка работоспособности

```bash
# 1. Проверить статус бенчмарка
./benchmark_status.sh

# 2. Проверить API модели
curl http://localhost:8001/v1/models

# 3. Следить за логами
tail -f benchmark_master.log

# 4. Проверить Docker
docker logs -f vllm_gpu_server

# 5. Проверить GPU
nvidia-smi
```

## 📊 Ожидаемое время

- **Загрузка модели**: 2-3 минуты
- **Один бенчмарк**: ~10 минут
- **Все 6 бенчмарков**: ~60 минут
- **Все 5 моделей**: **~5 часов**

## 🚀 Запуск

```bash
# Автоматический режим (без подтверждений)
nohup ./benchmark_master.sh --yes > benchmark_master.log 2>&1 &

# Интерактивный режим
./benchmark_menu.sh
```

## 🔍 Мониторинг

```bash
# Обновлять каждые 5 секунд
watch -n 5 './benchmark_status.sh'

# Или вручную
./benchmark_status.sh
```
