# 📊 Полная система RAG бенчмарков (6 бенчмарков)

## 🎯 Обзор

Система включает **6 специализированных RAG бенчмарков**:

| № | Бенчмарк | Метрики | Что проверяет |
|---|----------|---------|---------------|
| 1 | **RAGAS** | 4 метрики | Точность RAG: Faithfulness, Relevancy, Precision, Recall |
| 2 | **RGB** | 3 метрики | Надежность: Noise Robustness, Negative Rejection, Info Integration |
| 3 | **Multi-Hop** | 3 метрики | Рассуждения: Hop Accuracy, Reasoning Quality, Completeness |
| 4 | **Citation** | 3 метрики | Цитирование: Citation Accuracy, Source Relevance, No Hallucination |
| 5 | **Retrieval** | 5 метрик | Поиск: Precision, Recall, F1, MRR, NDCG |
| 6 | **Contextual** | 4 метрики | Понимание: Depth, Concept Coverage, Coherence, Context Utilization |

**Итого: 22 метрики + Overall RAG Score**

---

## 📋 Детальное описание бенчмарков

### 1. RAGAS (Retrieval Augmented Generation Assessment)

**Цель**: Оценить качество RAG-системы по индустриальным стандартам

**Метрики**:
- **Faithfulness** (0-1): Насколько ответ точен относительно контекста (нет галлюцинаций)
  - ≥0.9 - отлично, модель не выдумывает
  - <0.7 - плохо, много галлюцинаций
- **Answer Relevancy** (0-1): Насколько ответ релевантен вопросу
  - ≥0.8 - отлично, точно отвечает
  - <0.6 - плохо, уходит от темы
- **Context Precision** (0-1): Точность поиска релевантных документов
  - ≥0.7 - хорошо находит нужное
  - <0.5 - плохо, много шума
- **Context Recall** (0-1): Полнота найденного контекста
  - ≥0.8 - достаточно информации
  - <0.6 - мало контекста

**Вопросы**: 30 вопросов (factual, inferential, comparative, synthesis)

**Формула**: `RAGAS Score = (Faithfulness + Relevancy + Precision + Recall) / 4`

---

### 2. RGB (Retrieval with Generative Bias)

**Цель**: Проверить надежность модели при сложных условиях

**Метрики**:
- **Noise Robustness** (0-1): Устойчивость к шумящему контексту
  - Добавляет 50% нерелевантного текста
  - Проверяет, игнорирует ли модель шум
- **Negative Rejection** (0-1): Умение признавать незнание
  - Задает невозможные вопросы
  - Проверяет, скажет ли "не знаю"
- **Information Integration** (0-1): Объединение из нескольких источников
  - Требует синтез из 3+ документов
  - Проверяет комплексное понимание

**Вопросы**: 15 специальных тестов

**Формула**: `RGB Score = (Noise + Rejection + Integration) / 3`

---

### 3. Multi-Hop Reasoning

**Цель**: Проверить способность к многошаговым рассуждениям

**Метрики**:
- **Hop Accuracy** (0-1): Правильность связывания фактов
  - Пример: "Платон был учителем Аристотеля" + "Аристотель учил логике" → связь
- **Reasoning Quality** (0-1): Качество логических цепочек
  - Проверяет "потому что", "следовательно" и т.д.
- **Completeness** (0-1): Использованы ли все необходимые документы
  - Все ли шаги рассуждения присутствуют

**Вопросы**: 15 вопросов (2-hop и 3-hop reasoning)

**Формула**: `Multi-Hop Score = (Accuracy + Quality + Completeness) / 3`

---

### 4. Citation Accuracy

**Цель**: Проверить точность цитирования и обнаружение галлюцинаций

**Метрики**:
- **Citation Accuracy** (0-1): Правильность ссылок на источники
  - Есть ли [1], [2] в тексте
  - Соответствуют ли номера реальным источникам
- **Source Relevance** (0-1): Релевантность использованных источников
  - Действительно ли источники содержат информацию для ответа
- **No Hallucination** (0-1): Отсутствие выдуманных фактов
  - Проверка на известные факты
  - Признание незнания при отсутствии информации

**Вопросы**: 8 вопросов с проверяемыми фактами

**Формула**: `Citation Score = (Citation Acc + Source Rel + No Halluc) / 3`

---

### 5. Retrieval Quality (на основе BEIR)

**Цель**: Оценить качество поиска документов

**Метрики**:
- **Precision** (0-1): Доля релевантных среди найденных
  - `Precision = relevant_found / total_found`
- **Recall** (0-1): Доля найденных среди всех релевантных
  - `Recall = relevant_found / total_relevant`
- **F1-Score** (0-1): Гармоническое среднее Precision и Recall
  - `F1 = 2 * (P * R) / (P + R)`
- **MRR (Mean Reciprocal Rank)**: Позиция первого релевантного документа
  - `MRR = 1 / rank_first_relevant`
- **NDCG (Normalized DCG)**: Качество ранжирования
  - Учитывает порядок документов

**Вопросы**: 10 поисковых запросов

**Формула**: `Retrieval Score = (P + R + F1 + MRR + NDCG) / 5`

---

### 6. Contextual Understanding

**Цель**: Оценить глубину понимания контекста

**Метрики**:
- **Depth Score** (0-1): Глубина ответа
  - Наличие "потому что", "следовательно"
  - Длина и структура ответа
- **Concept Coverage** (0-1): Покрытие ожидаемых концептов
  - Присутствуют ли ключевые понятия
- **Coherence** (0-1): Связность и логичность
  - Использование "кроме того", "однако"
  - Структурированность текста
- **Context Utilization** (0-1): Использование контекста из источников
  - Насколько хорошо использованы найденные документы

**Вопросы**: 8 вопросов, требующих глубокого понимания

**Формула**: `Contextual Score = (Depth + Coverage + Coherence + Utilization) / 4`

---

## 🚀 Как запустить

### Все бенчмарки сразу:

```bash
python3 benchmark_all_rag.py MODEL_NAME
```

### По отдельности:

```bash
# RAGAS
python3 benchmark_ragas.py MODEL_NAME

# RGB
python3 benchmark_rgb.py MODEL_NAME

# Multi-Hop
python3 benchmark_multihop.py MODEL_NAME

# Citation
python3 benchmark_citation.py MODEL_NAME

# Retrieval
python3 benchmark_retrieval.py MODEL_NAME

# Contextual
python3 benchmark_contextual.py MODEL_NAME
```

---

## 📊 Интерпретация результатов

### Overall RAG Score (среднее всех 6 бенчмарков):

| Score | Оценка | Описание |
|-------|--------|----------|
| ≥0.85 | 🥇 Отлично | Топовая модель для RAG, рекомендуется |
| 0.75-0.84 | 🥈 Хорошо | Хорошая модель, подходит для продакшена |
| 0.65-0.74 | 🥉 Средне | Приемлемо, но есть лучше |
| <0.65 | ⚠️ Низко | Не рекомендуется для RAG |

### По категориям:

**1. Точность и надежность** (RAGAS + Citation):
- RAGAS ≥0.8 + Citation ≥0.8 = Надежная модель без галлюцинаций

**2. Устойчивость** (RGB):
- RGB ≥0.8 = Модель устойчива к шуму, умеет признавать незнание

**3. Рассуждения** (Multi-Hop):
- Multi-Hop ≥0.8 = Модель хорошо связывает факты

**4. Поиск** (Retrieval):
- Retrieval ≥0.8 = Отличное качество поиска документов

**5. Понимание** (Contextual):
- Contextual ≥0.8 = Глубокое понимание контекста

---

## 📁 Результаты

После запуска создаются файлы:

```
benchmark_results/
├── MODEL_ragas.json       # RAGAS метрики
├── MODEL_rgb.json         # RGB метрики
├── MODEL_multihop.json    # Multi-Hop метрики
├── MODEL_citation.json    # Citation метрики
├── MODEL_retrieval.json   # Retrieval метрики
├── MODEL_contextual.json  # Contextual метрики
└── MODEL_all_rag.json     # Объединенные результаты
```

### Объединенная таблица:

```bash
python3 benchmark_merge_results.py
```

Создает:
- `benchmark_merged_results.csv` - для Excel
- `benchmark_merged_results.md` - читаемый отчет

---

## 🎯 Примеры использования

### Пример 1: Найти лучшую модель для RAG

```bash
# Запустить все бенчмарки для топ-3 моделей
python3 benchmark_all_rag.py Qwen_Qwen2.5-7B-Instruct
python3 benchmark_all_rag.py meta-llama_Meta-Llama-3.1-8B-Instruct
python3 benchmark_all_rag.py mistralai_Mistral-7B-Instruct-v0.3

# Посмотреть сравнение
python3 benchmark_merge_results.py
```

### Пример 2: Проверить конкретные слабости модели

```bash
# Только Citation (проверка на галлюцинации)
python3 benchmark_citation.py MODEL_NAME

# Только Retrieval (качество поиска)
python3 benchmark_retrieval.py MODEL_NAME
```

### Пример 3: Автоматический запуск для всех моделей

```bash
# Использовать master script
./benchmark_master.sh
```

---

## 🔧 Настройка

### Изменить вопросы:

Каждый бенчмарк имеет свои вопросы в коде:
- `benchmark_ragas.py` → `RAGAS_QUESTIONS`
- `benchmark_rgb.py` → `RGB_QUESTIONS`
- `benchmark_multihop.py` → `MULTIHOP_QUESTIONS`
- `benchmark_citation.py` → `CITATION_QUESTIONS`
- `benchmark_retrieval.py` → `RETRIEVAL_QUESTIONS`
- `benchmark_contextual.py` → `CONTEXTUAL_QUESTIONS`

### Добавить свои метрики:

Можно расширить любой бенчмарк, добавив свои функции оценки.

---

## 💡 Рекомендации

### Для выбора модели:

1. **Если важна точность**: смотрите на RAGAS + Citation
2. **Если важна надежность**: смотрите на RGB
3. **Если нужны рассуждения**: смотрите на Multi-Hop
4. **Если важен поиск**: смотрите на Retrieval
5. **Если важно понимание**: смотрите на Contextual

### Оптимальные значения:

- **Для продакшена**: все метрики ≥0.75, Overall ≥0.80
- **Для экспериментов**: все метрики ≥0.65, Overall ≥0.70
- **Минимум**: все метрики ≥0.60, Overall ≥0.65

---

## 🆘 Troubleshooting

### Бенчмарк не запускается:

```bash
# Проверить API
curl http://localhost:8888/health

# Перезапустить backend
cd ~/llm_else
pkill -f uvicorn
source .venv/bin/activate
nohup uvicorn app:app --host 0.0.0.0 --port 8888 &
```

### Низкие оценки:

- **RAGAS низкий**: проверьте качество источников, возможно модель галлюцинирует
- **RGB низкий**: модель не устойчива к шуму, не умеет отказывать
- **Multi-Hop низкий**: модель плохо связывает факты
- **Citation низкий**: проблемы с цитированием, галлюцинации
- **Retrieval низкий**: плохое качество поиска, настройте порог RAG
- **Contextual низкий**: поверхностное понимание контекста

---

## 📚 Дополнительные материалы

- [RAG_BENCHMARKS.md](RAG_BENCHMARKS.md) - еще более подробное описание
- [BENCHMARK_QUICKSTART.md](BENCHMARK_QUICKSTART.md) - быстрый старт
- [BENCHMARK_README.md](BENCHMARK_README.md) - общая документация

**Готово! 6 RAG бенчмарков × 45+ моделей = Полная картина! 🎉**
