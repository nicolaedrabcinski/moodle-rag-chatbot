# 🚀 Быстрый старт: Запуск ВСЕХ бенчмарков

## 📋 Что включено

Система теперь тестирует модели по **4 бенчмаркам**:

1. **Speed** - скорость ответа и длина
2. **RAGAS** - Faithfulness, Relevancy, Context Precision/Recall (4 метрики)
3. **RGB** - Noise Robustness, Negative Rejection, Information Integration (3 метрики)
4. **Multi-Hop** - Hop Accuracy, Reasoning Quality, Completeness (3 метрики)

**Итого: 11 метрик на модель + Overall RAG Score**

---

## ⚡ Быстрый старт (3 команды)

```bash
# 1. Скачать топовые модели (автоматически)
./benchmark_quick_setup.sh

# 2. Запустить ВСЕ бенчмарки для ВСЕХ моделей
./benchmark_master.sh

# 3. Посмотреть результаты
python3 benchmark_merge_results.py
```

**Время**: ~45 минут на модель × количество моделей

---

## 📦 Шаг 1: Скачать модели

### Автоматически (TOP-10):
```bash
./benchmark_quick_setup.sh
```

Скачает 10 лучших моделей (~100GB, ~60 минут):
- Qwen2.5-7B-Instruct
- Llama-3.1-8B-Instruct
- Mistral-7B-Instruct
- Gemma-2-9B
- Phi-3.5-mini-instruct
- DeepSeek-Coder-6.7B
- Yi-1.5-9B
- Qwen2.5-3B-Instruct
- Gemma-2-2B
- CodeQwen1.5-7B

### Выборочно (интерактивное меню):
```bash
./benchmark_download_models.sh
```

Выбрать из 45+ моделей вручную.

### Посмотреть все доступные:
```bash
./models_for_benchmark.sh
```

---

## 🎯 Шаг 2: Запустить бенчмарки

### ВАРИАНТ А: Все модели × Все бенчмарки (автоматически)

```bash
./benchmark_master.sh
```

**Что происходит:**
1. Остановка текущей vLLM
2. Запуск новой модели в Docker
3. Обновление конфигурации backend
4. Перезапуск backend
5. Запуск Speed бенчмарка
6. Запуск RAGAS бенчмарка
7. Запуск RGB бенчмарка
8. Запуск Multi-Hop бенчмарка
9. Объединение результатов
10. Переход к следующей модели

**Результаты после каждой модели:**
- `benchmark_results/MODEL_speed.json`
- `benchmark_results/MODEL_ragas.json`
- `benchmark_results/MODEL_rgb.json`
- `benchmark_results/MODEL_multihop.json`
- `benchmark_results/MODEL_all_rag.json`

**Объединенные результаты:**
- `benchmark_results/benchmark_merged_results.csv`
- `benchmark_results/benchmark_merged_results.md`

### ВАРИАНТ Б: Только конкретные бенчмарки

#### Speed бенчмарк (11 вопросов):
```bash
./benchmark_run.sh
```

#### RAGAS бенчмарк (30 вопросов):
```bash
python3 benchmark_ragas.py
```

#### RGB бенчмарк (надежность):
```bash
python3 benchmark_rgb.py
```

#### Multi-Hop бенчмарк (reasoning):
```bash
python3 benchmark_multihop.py
```

#### Все RAG бенчмарки для текущей модели:
```bash
python3 benchmark_all_rag.py "MODEL_NAME"
```

---

## 📊 Шаг 3: Посмотреть результаты

### Объединенная таблица (все бенчмарки):
```bash
python3 benchmark_merge_results.py
```

**Вывод:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ОБЪЕДИНЕННАЯ ТАБЛИЦА БЕНЧМАРКОВ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

№   Модель                     Time    Len    RAGAS   RGB     M-Hop   Overall  Status
1   Qwen2.5-7B-Instruct        18.2s   1234   0.892   0.867   0.834   0.864    🥇 Отлично
2   Llama-3.1-8B-Instruct      21.5s   1456   0.878   0.845   0.823   0.849    🥈 Хорошо
...
```

### Детальные метрики:
```
📈 ДЕТАЛЬНЫЕ МЕТРИКИ

🔹 Qwen2.5-7B-Instruct
  ⏱️  SPEED: avg=18.2s, median=17.8s, range=12.3s-25.4s, len=1234 chars
  📚 RAGAS: Faithfulness=0.923, Relevancy=0.889, Precision=0.891, Recall=0.865 → Score=0.892
  🛡️  RGB: Noise=0.890, Rejection=0.856, Integration=0.856 → Score=0.867
  🔗 M-HOP: Accuracy=0.845, Quality=0.834, Complete=0.823 → Score=0.834
  🎯 OVERALL RAG SCORE: 0.864
```

### Только RAGAS анализ:
```bash
python3 benchmark_ragas_analyze.py
```

### Файлы результатов:
- **CSV**: `benchmark_results/benchmark_merged_results.csv` - для Excel/Google Sheets
- **Markdown**: `benchmark_results/benchmark_merged_results.md` - читаемый отчет
- **JSON**: `benchmark_results/MODEL_*.json` - сырые данные

---

## 🔧 Настройка моделей

### Выбрать модели для тестирования

Открыть `benchmark_master.sh` и раскомментировать нужные модели:

```bash
# === QWEN 2.5 ===
QWEN_MODELS=(
    "Qwen/Qwen2.5-7B-Instruct"           # ✅ Включена
    "Qwen/Qwen2.5-3B-Instruct"           # ✅ Включена
    # "Qwen/Qwen2.5-1.5B-Instruct"       # ❌ Выключена
)

# === LLAMA 3.1 ===
LLAMA_MODELS=(
    "meta-llama/Meta-Llama-3.1-8B-Instruct"    # ✅ Включена
    # "meta-llama/Llama-3.3-70B-Instruct-AWQ"  # ❌ Выключена (требует больше VRAM)
)
```

**По умолчанию включены:**
- Qwen2.5-7B-Instruct
- Qwen2.5-3B-Instruct
- Llama-3.1-8B-Instruct
- Mistral-7B-Instruct-v0.3
- Gemma-2-9B

**Всего доступно: 45+ моделей**

---

## 📖 Подробная документация

### О бенчмарках:
- `RAG_BENCHMARKS.md` - описание всех RAG метрик, что они измеряют, как интерпретировать
- `BENCHMARK_README.md` - общая документация по системе

### О моделях:
- `models_for_benchmark.sh` - список всех 45+ моделей с характеристиками

### Вопросы для тестирования:
- `benchmark_questions.json` - 11 вопросов для Speed (simple, medium, complex, RAG)
- `benchmark_rag_questions.json` - 30 вопросов для RAG (factual, inferential, comparative, synthesis)

---

## 🎯 Интерпретация результатов

### Overall RAG Score (0-1):
- **≥0.85** 🥇 **Отлично** - Топовая модель для RAG, рекомендуется
- **≥0.75** 🥈 **Хорошо** - Хорошая модель, подходит для продакшена
- **≥0.65** 🥉 **Средне** - Приемлемо, но есть лучше
- **<0.65** ⚠️ **Низко** - Не рекомендуется для RAG

### RAGAS Score (0-1):
- **Faithfulness** (≥0.9) - не галлюцинирует, точно использует контекст
- **Answer Relevancy** (≥0.8) - отвечает на вопрос, не уходит в сторону
- **Context Precision** (≥0.7) - находит правильные документы
- **Context Recall** (≥0.8) - использует достаточно контекста

### RGB Score (0-1):
- **Noise Robustness** - насколько хорошо игнорирует шум и нерелевантный контекст
- **Negative Rejection** - умеет сказать "не знаю" когда информации нет
- **Information Integration** - объединяет информацию из нескольких документов

### Multi-Hop Score (0-1):
- **Hop Accuracy** - правильно связывает факты из разных документов
- **Reasoning Quality** - качество логических цепочек
- **Completeness** - использует все необходимые документы

### Speed:
- **<15s** ⚡ Быстро
- **15-25s** ✅ Нормально
- **25-40s** ⚠️ Медленно
- **>40s** 🐌 Очень медленно

---

## 🔍 Пример использования

```bash
# 1. Скачать ТОП-3 модели
./benchmark_quick_setup.sh
# Выбрать "3" (только Qwen-7B, Llama-8B, Mistral-7B)

# 2. Отредактировать список в benchmark_master.sh
nano benchmark_master.sh
# Оставить только эти 3 модели раскомментированными

# 3. Запустить
./benchmark_master.sh

# 4. Подождать ~2 часа (3 модели × 45 минут)

# 5. Посмотреть результаты
python3 benchmark_merge_results.py

# 6. Открыть CSV в Excel/Google Sheets
# Файл: benchmark_results/benchmark_merged_results.csv
```

---

## 💡 Советы

### Экономия времени:
1. **Сначала 2-3 модели** - протестировать систему
2. **Затем добавить больше** - если все работает
3. **Запустить на ночь** - для всех 45+ моделей

### Экономия места:
- Каждая модель: ~5-15GB
- TOP-10: ~100GB
- Все 45: ~400GB
- Можно удалять после тестирования: `rm -rf /models/MODEL_NAME`

### Мониторинг:
```bash
# GPU память
watch -n 1 nvidia-smi

# Docker контейнер
docker logs -f vllm_gpu_server

# Backend логи
tail -f ~/llm_else/backend.log

# Прогресс бенчмарка
watch -n 5 ls -lht benchmark_results/
```

---

## 🆘 Troubleshooting

### Модель не запускается:
```bash
# Проверить VRAM
nvidia-smi

# Остановить все Docker
docker stop $(docker ps -aq)

# Попробовать снова
./benchmark_master.sh
```

### Backend не отвечает:
```bash
# Перезапустить вручную
cd ~/llm_else
source .venv/bin/activate
pkill -f "uvicorn"
nohup uvicorn app:app --host 0.0.0.0 --port 8888 &

# Проверить
curl http://localhost:8888/health
```

### Отсутствуют зависимости:
```bash
# Установить недостающие
cd ~/llm_else
source .venv/bin/activate
pip install ragas datasets pandas
```

### Бенчмарк завис:
```bash
# Ctrl+C для остановки
# Посмотреть частичные результаты
python3 benchmark_merge_results.py

# Продолжить с определенной модели (отредактировать MODELS[] в benchmark_master.sh)
```

---

## 📧 Дополнительная помощь

Подробная документация:
- `RAG_BENCHMARKS.md` - описание метрик
- `BENCHMARK_README.md` - полная документация
- `models_for_benchmark.sh` - список моделей

**Готово! Запускайте бенчмарки! 🚀**
