# 🎯 ДЕТАЛЬНЫЙ ПЛАН РАЗВИТИЯ ПРОЕКТА
## Образовательная RAG-платформа по Философии

> **Статус:** Benchmark 18/24 моделей завершено (14 часов работы)  
> **Контекст:** Образовательная платформа, домен - философия и методички  
> **Цель:** Интеллектуальный ассистент-преподаватель для студентов

---

## ЭТАП 0: Завершение Текущего Benchmark ⏳

**Статус:** В процессе (осталось ~2-3 часа)
- ✅ Завершено: 18/24 моделей
- 🔄 В процессе: Llama 3.1 70B (CPU, медленно)
- ⏳ Осталось: Qwen 2.5 72B (последняя CPU модель)

**Действия:**
- Дождаться завершения всех 24 моделей
- Собрать результаты в единую таблицу

---

## ЭТАП 1: Анализ Результатов Benchmark 📊

**Приоритет:** 🔴 КРИТИЧЕСКИЙ  
**Время:** 2-3 часа  
**Цель:** Выбрать оптимальные модели для продакшена

### Задача 1.1: Создать сводную таблицу результатов

**Файл:** `scripts/analysis/analyze_benchmark_results.py`

```python
# Собрать все результаты из benchmark_results/*_adaptive.json
# Создать сводную таблицу с метриками:
# - Model name
# - Device (GPU/CPU)
# - Quantization
# - Exact Match %
# - F1 Score
# - Retrieval Precision %
# - Avg generation time (s)
# - Total time (s)
# - Memory usage
```

**Выходы:**
- `docs/results/BENCHMARK_SUMMARY.md` - таблица в Markdown
- `docs/results/benchmark_summary.csv` - для анализа
- `docs/results/benchmark_plots.png` - графики метрик

### Задача 1.2: Выбрать ТОП-3 модели для продакшена

**Критерии выбора:**
1. **Для продакшена (GPU):**
   - F1 Score > 0.3 (если возможно)
   - Retrieval Precision > 70%
   - Скорость < 5 секунд на вопрос
   - Memory < 15 GB

2. **Для экспериментов (CPU):**
   - Лучшие метрики среди 70B+ моделей
   - Для offline анализа

**Выход:**
- `docs/results/SELECTED_MODELS.md` - обоснование выбора

### Задача 1.3: Анализ ошибок

**Файл:** `scripts/analysis/error_analysis.py`

Проанализировать детальные результаты:
- Какие типы вопросов дают низкий F1?
- Где retrieval не находит релевантные документы?
- Паттерны неправильных ответов

**Выход:**
- `docs/results/ERROR_PATTERNS.md`

---

## ЭТАП 2: Быстрые Победы (Quick Wins) 🚀

**Приоритет:** 🟠 ВЫСОКИЙ  
**Время:** 1-2 дня  
**Цель:** Улучшить качество на 50-70% БЕЗ fine-tuning

### Задача 2.1: Улучшенный системный промпт

**Файл:** `config/prompts/educational_philosophy_prompt.py`

**Текущий промпт (простой):**
```python
prompt = f"""Context: {context}

Question: {question}

Answer based on the context above:"""
```

**Новый промпт (образовательный):**
```python
SYSTEM_PROMPT = """Вы - опытный преподаватель философии в университете. 
Ваша задача - помогать студентам понимать философские концепции через 
структурированные и понятные объяснения.

При ответе на вопросы следуйте этой структуре:
1. **Определение**: Дайте четкое определение понятия
2. **Исторический контекст**: Кто, когда, в каком контексте
3. **Ключевые аспекты**: Разбейте на основные компоненты
4. **Примеры**: Конкретные примеры для понимания
5. **Источники**: Укажите источники из предоставленных материалов

Правила:
- Используйте ТОЛЬКО информацию из предоставленного контекста
- Если информации недостаточно, честно скажите об этом
- Используйте философскую терминологию точно и корректно
- Объясняйте сложные концепции доступным языком
- Всегда ссылайтесь на источники (автор, произведение)"""

USER_PROMPT = """Контекст из учебных материалов:
{context}

Вопрос студента: {question}

Пожалуйста, ответьте на вопрос, используя структуру выше."""
```

**Реализация:**
```python
# Создать новый файл benchmark_rag_educational.py
# С улучшенными промптами для философии
```

**Тестирование:**
- Протестировать на ТОП-3 моделях
- Сравнить метрики: старый vs новый промпт
- Документировать улучшение

**Выход:**
- `scripts/benchmarks/benchmark_rag_educational.py`
- `docs/results/PROMPT_IMPROVEMENT_RESULTS.md`

### Задача 2.2: Few-shot примеры

**Файл:** `config/prompts/few_shot_examples.py`

Добавить 3-5 примеров хороших ответов:

```python
FEW_SHOT_EXAMPLES = [
    {
        "question": "Что такое категорический императив?",
        "context": "...",
        "good_answer": """
Категорический императив - это центральное понятие этики Иммануила Канта.

**Определение**: Безусловное моральное требование, которое действует 
независимо от личных желаний и целей.

**Формулировка** (Кант, "Критика практического разума"): 
"Поступай только согласно такой максиме, руководствуясь которой ты 
в то же время можешь пожелать, чтобы она стала всеобщим законом".

**Ключевые аспекты**:
1. Безусловность - в отличие от гипотетических императивов
2. Всеобщность - правило должно быть применимо ко всем
3. Практическое применение - проверка максим через универсализацию

**Пример**: Ложь не может быть категорическим императивом, так как 
если все будут лгать, институт обещаний разрушится.

Источник: Кант И., "Критика практического разума" (1788)
"""
    },
    # еще 2-4 примера
]
```

### Задача 2.3: Улучшенная обработка ответов

**Файл:** `scripts/benchmarks/post_processing.py`

- Добавить форматирование с markdown
- Структурированный вывод (определение, контекст, примеры)
- Автоматическое выделение ключевых терминов
- Добавление ссылок на источники

---

## ЭТАП 3: Улучшение RAG Компонента 🔍

**Приоритет:** 🟠 ВЫСОКИЙ  
**Время:** 3-5 дней  
**Цель:** Улучшить Retrieval Precision с 75% до 90%+

### Задача 3.1: Замена TF-IDF на Sentence Embeddings

**Файл:** `scripts/rag/embedding_retrieval.py`

**Текущая проблема:**
```python
# TF-IDF - не понимает семантику
vectorizer = TfidfVectorizer()
```

**Решение:**
```python
from sentence_transformers import SentenceTransformer

# Модель для русского языка
model = SentenceTransformer('cointegrated/rubert-tiny2')
# или 'ai-forever/sbert_large_nlu_ru'

class EmbeddingRAG:
    def __init__(self, documents):
        self.model = SentenceTransformer('cointegrated/rubert-tiny2')
        self.documents = documents
        self.embeddings = self.model.encode(documents)
    
    def retrieve(self, query, top_k=3):
        query_embedding = self.model.encode([query])
        scores = cosine_similarity(query_embedding, self.embeddings)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [(self.documents[i], float(scores[i])) for i in top_indices]
```

**Тестирование:**
- Сравнить TF-IDF vs Embeddings на 100 вопросах
- Метрика: Retrieval Precision

**Выход:**
- `scripts/rag/embedding_retrieval.py`
- `docs/results/RETRIEVAL_COMPARISON.md`

### Задача 3.2: Гибридный поиск (BM25 + Embeddings)

**Файл:** `scripts/rag/hybrid_retrieval.py`

```python
from rank_bm25 import BM25Okapi

class HybridRAG:
    def __init__(self, documents):
        # BM25 для keyword matching
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Embeddings для semantic matching
        self.embedding_rag = EmbeddingRAG(documents)
    
    def retrieve(self, query, top_k=3, alpha=0.5):
        # BM25 scores
        bm25_scores = self.bm25.get_scores(tokenize(query))
        
        # Embedding scores
        emb_scores = self.embedding_rag.get_scores(query)
        
        # Weighted combination
        final_scores = alpha * bm25_scores + (1-alpha) * emb_scores
        
        # Rank fusion
        return self._rank_fusion(bm25_results, emb_results)
```

### Задача 3.3: Reranking с Cross-Encoder

**Файл:** `scripts/rag/reranking.py`

```python
from sentence_transformers import CrossEncoder

class RerankerRAG:
    def __init__(self, base_rag):
        self.base_rag = base_rag
        # Cross-encoder для русского
        self.reranker = CrossEncoder('amberoad/bert-multilingual-passage-reranking-msmarco')
    
    def retrieve(self, query, top_k=3, rerank_top_k=10):
        # Получить top-10 кандидатов
        candidates = self.base_rag.retrieve(query, top_k=rerank_top_k)
        
        # Rerank с cross-encoder
        pairs = [[query, doc] for doc, _ in candidates]
        scores = self.reranker.predict(pairs)
        
        # Вернуть top-k после reranking
        reranked = sorted(zip(candidates, scores), 
                         key=lambda x: x[1], reverse=True)
        return reranked[:top_k]
```

### Задача 3.4: Улучшенный Chunking

**Файл:** `scripts/rag/smart_chunking.py`

**Текущая проблема:**
- Документы разбиваются просто по размеру
- Теряется контекст

**Решение:**
```python
class SemanticChunker:
    def chunk_by_paragraphs(self, text, max_tokens=512, overlap=50):
        # Разбивка по параграфам
        # Сохранение контекста между чанками (overlap)
        # Умные границы (не разрывать предложения)
        pass
    
    def chunk_by_topics(self, text):
        # Использовать NLP для определения границ топиков
        # Каждый чанк = законченная мысль/концепция
        pass
```

### Задача 3.5: Создать новый benchmark с улучшенным RAG

**Файл:** `scripts/benchmarks/benchmark_rag_v2.py`

Протестировать ВСЕ улучшения:
- Embeddings
- Hybrid search
- Reranking
- Smart chunking
- Улучшенные промпты

На ТОП-3 моделях из ЭТАП 1.

**Выход:**
- Сравнительная таблица метрик
- `docs/results/RAG_V2_RESULTS.md`

---

## ЭТАП 4: Подготовка к Fine-tuning 🎓

**Приоритет:** 🟡 СРЕДНИЙ  
**Время:** 1-2 недели  
**Цель:** Подготовить датасет и инфраструктуру для обучения

### Задача 4.1: Создание датасета для fine-tuning

**Файл:** `datasets/philosophy_educational_dataset.json`

**Структура:**
```json
[
  {
    "instruction": "Ты - преподаватель философии. Объясни концепцию студенту.",
    "input": "Контекст: <отрывок из методички>\n\nВопрос: Что такое трансцендентальная апперцепция?",
    "output": "Трансцендентальная апперцепция - это...\n\n[Структурированный ответ с определением, контекстом, примерами]",
    "metadata": {
      "source": "Кант И., Критика чистого разума",
      "difficulty": "advanced",
      "topic": "гносеология"
    }
  }
]
```

**Источники данных:**
1. Ручная аннотация (500 примеров):
   - Преподаватели составляют "идеальные ответы"
   - Разные форматы: определения, сравнения, примеры
   - Разные уровни сложности

2. Генерация с помощью GPT-4/Claude:
   - Использовать лучшую модель для генерации примеров
   - Ручная проверка и корректировка

3. Реальные вопросы студентов:
   - Собрать из платформы
   - Аннотировать преподавателями

**Целевой размер:** 1000-2000 примеров

**Скрипты:**
```python
# scripts/dataset/create_training_dataset.py
# scripts/dataset/validate_dataset.py
# scripts/dataset/augment_dataset.py
```

### Задача 4.2: Выбор модели для fine-tuning

На основе результатов бенчмарка выбрать:
- **Qwen 2.5 7B** - отличный для русского, быстрый
- **Qwen 2.5 14B** - баланс качества/скорости
- **Llama 3.1 8B** - хорошая базовая модель

### Задача 4.3: Setup инфраструктуры для обучения

**Файлы:**
```
finetuning/
├── train_lora.py           # LoRA fine-tuning
├── train_full.py           # Full fine-tuning (если нужно)
├── config/
│   ├── lora_config.yaml
│   └── training_args.yaml
├── evaluation/
│   └── eval_finetuned.py
└── README.md
```

**Технологии:**
- 🔥 **PyTorch + HuggingFace Transformers**
- ⚡ **LoRA** (эффективное обучение)
- 🎯 **DeepSpeed** (для больших моделей)
- 📊 **Weights & Biases** (мониторинг)

### Задача 4.4: Пилотное обучение

**Цель:** Проверить pipeline на маленьком датасете

```bash
# 100 примеров, 1 эпоха
python finetuning/train_lora.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset datasets/philosophy_pilot_100.json \
  --epochs 1 \
  --output models/qwen-7b-philosophy-pilot
```

**Оценка:**
- Сравнить с базовой моделью на тестовом сете
- Проверить что модель не переобучилась

---

## ЭТАП 5: Production-Ready Система 🚢

**Приоритет:** 🟢 НОРМАЛЬНЫЙ  
**Время:** 1-2 недели  
**Цель:** Готовая к деплою система

### Задача 5.1: API Сервис

**Файл:** `api/main.py`

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Question(BaseModel):
    text: str
    context_ids: Optional[List[str]] = None  # опционально конкретные документы

class Answer(BaseModel):
    answer: str
    sources: List[Dict]
    confidence: float
    retrieval_docs: List[Dict]

@app.post("/ask")
async def ask_question(question: Question) -> Answer:
    # RAG pipeline
    # LLM generation
    # Post-processing
    return Answer(...)

@app.get("/health")
async def health():
    return {"status": "ok", "model": "qwen-7b-philosophy"}
```

### Задача 5.2: Docker контейнеры

```dockerfile
# Dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

RUN pip install -r requirements.txt

# Оптимизация: кэшировать модели в образе
COPY models/ /app/models/

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

### Задача 5.3: Мониторинг и логирование

```python
# Prometheus метрики
# Grafana дашборды
# Логирование всех запросов для анализа

from prometheus_client import Counter, Histogram

request_count = Counter('rag_requests_total', 'Total requests')
latency = Histogram('rag_latency_seconds', 'Request latency')
```

### Задача 5.4: A/B тестирование

```python
# Система для сравнения разных моделей/промптов
# Сбор фидбэка от пользователей
# Метрики: полезность ответа, точность, релевантность
```

---

## ЭТАП 6: Continuous Improvement 📈

**Приоритет:** 🔵 ДОЛГОСРОЧНЫЙ  
**Время:** Постоянно  

### Задача 6.1: Сбор обратной связи

- Интеграция кнопок "👍 / 👎" для ответов
- Сбор комментариев студентов
- Анализ сложных вопросов

### Задача 6.2: Расширение датасета

- Регулярное добавление новых примеров
- Переобучение модели раз в месяц/квартал

### Задача 6.3: Добавление новых источников

- Интеграция новых методичек
- Добавление видео-лекций (транскрипты)
- Философские первоисточники

### Задача 6.4: Advanced фичи

- **Multi-turn диалоги** - поддержка контекста разговора
- **Personalization** - адаптация под уровень студента
- **Визуализация** - диаграммы философских концепций
- **Квизы** - автоматическая генерация вопросов для проверки

---

## ЭТАП 7: Документация и Передача 📚

### Задача 7.1: Техническая документация

```
docs/
├── ARCHITECTURE.md       - Архитектура системы
├── API_REFERENCE.md      - API документация
├── DEPLOYMENT.md         - Деплой инструкции
├── MODELS.md            - Описание моделей
└── EVALUATION.md        - Метрики и оценка
```

### Задача 7.2: Пользовательская документация

- Как задавать вопросы
- Примеры хороших вопросов
- FAQ

### Задача 7.3: Обучение команды

- Презентация результатов
- Воркшоп для преподавателей
- Документация для разработчиков

---

## Приоритизация задач

### 🔴 КРИТИЧЕСКИЕ (делать сразу после benchmark):
1. Анализ результатов бенчмарка (ЭТАП 1)
2. Улучшение промптов (ЭТАП 2.1, 2.2)
3. Замена TF-IDF на embeddings (ЭТАП 3.1)

### 🟠 ВЫСОКИЕ (следующие 1-2 недели):
4. Гибридный поиск + reranking (ЭТАП 3.2, 3.3)
5. Создание датасета для fine-tuning (ЭТАП 4.1)
6. API сервис (ЭТАП 5.1)

### 🟡 СРЕДНИЕ (1-2 месяца):
7. Fine-tuning модели (ЭТАП 4.4)
8. Docker + деплой (ЭТАП 5.2, 5.3)

### 🟢 НОРМАЛЬНЫЕ (долгосрочно):
9. A/B тестирование (ЭТАП 5.4)
10. Advanced фичи (ЭТАП 6.4)

---

## Ожидаемые результаты

### Метрики (прогноз):

| Этап | F1 Score | Retrieval | Latency | Описание |
|------|----------|-----------|---------|----------|
| Baseline (сейчас) | 0.03 | 75% | 3-5s | TF-IDF + простой промпт |
| ЭТАП 2 (промпты) | 0.15-0.25 | 75% | 3-5s | +50-70% от улучшенных промптов |
| ЭТАП 3 (RAG v2) | 0.25-0.40 | 90%+ | 4-6s | Embeddings + reranking |
| ЭТАП 4 (fine-tuned) | 0.40-0.60 | 90%+ | 3-5s | + Специализация на философию |
| Production | 0.50-0.70 | 90%+ | <3s | Оптимизация + опыт |

---

## Бюджет ресурсов

### Вычислительные ресурсы:
- **Benchmark:** ✅ Завершается (24 GPU часа)
- **Fine-tuning:** ~40-80 GPU часов (LoRA на 7B модели)
- **Production:** 1x GPU для inference

### Время команды:
- **Этапы 1-2:** 1 разработчик × 1 неделя
- **Этап 3:** 1 разработчик × 1 неделя
- **Этап 4:** 1 разработчик + 1 аннотатор × 2 недели
- **Этап 5:** 1 разработчик × 1 неделя

**Итого:** ~6 недель для полного цикла до production

---

## Метрики успеха проекта

### Технические:
- ✅ F1 Score > 0.5
- ✅ Retrieval Precision > 90%
- ✅ Latency < 3 секунды
- ✅ Uptime > 99%

### Бизнес:
- ✅ Студенты используют систему регулярно
- ✅ Положительный фидбэк (>80% 👍)
- ✅ Снижение нагрузки на преподавателей
- ✅ Улучшение понимания материала (опросы)

---

## Следующий шаг ПРЯМО СЕЙЧАС

После завершения benchmark (~2 часа):

```bash
# 1. Собрать результаты
python scripts/analysis/analyze_benchmark_results.py

# 2. Создать сводную таблицу
python scripts/analysis/create_summary_table.py

# 3. Выбрать ТОП-3 модели
python scripts/analysis/select_best_models.py

# 4. Начать с улучшения промптов
vim config/prompts/educational_philosophy_prompt.py
```

---

**Автор плана:** AI Assistant  
**Дата:** 2026-01-08  
**Версия:** 1.0  
**Статус:** DRAFT → Требует review команды
