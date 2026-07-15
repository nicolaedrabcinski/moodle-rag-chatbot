# 📊 Мониторинг загрузки документов

## Что происходит при загрузке?

Когда вы загружаете документы через веб-интерфейс, происходит следующее:

1. **📤 Загрузка файлов** → Файлы сохраняются на диск
2. **📄 Чтение контента** → Система читает текст из файлов
3. **✂️ Разбиение на chunks** → Текст делится на фрагменты (~1000 символов)
4. **🧮 Генерация embeddings** → Каждый фрагмент превращается в вектор (1024 измерения)
5. **💾 Индексация в Qdrant** → Векторы сохраняются в базу данных

---

## 🔍 Как следить за процессом?

### Вариант 1: Простой мониторинг (рекомендуется)
```bash
cd /home/nicolaedrabcinski/llm_else
./watch_upload.sh
```
Обновляется каждые 2 секунды, показывает ключевые события.

### Вариант 2: Реальное время
```bash
cd /home/nicolaedrabcinski/llm_else
./monitor_upload.sh
```
Показывает события по мере их возникновения.

### Вариант 3: Прямой просмотр логов
```bash
tail -f logs/backend_with_progress.log
```
Все логи без фильтрации.

### Вариант 4: Фильтрованный просмотр
```bash
tail -f logs/backend_with_progress.log | grep -E "📤|💾|📄|✂️|🧮|✅"
```
Только важные события с эмодзи.

---

## 📝 Что вы увидите в логах?

### Начало загрузки:
```
📤 Starting document upload
   course_id: MY-COURSE
   files_count: 3
   total_size_mb: 2.5
```

### Сохранение файлов:
```
💾 Saving 3 files to disk...
   [1/3] Saving: lecture1.txt
   ✅ Saved: lecture1.txt (125.3 KB)
   [2/3] Saving: lecture2.txt
   ✅ Saved: lecture2.txt (89.7 KB)
```

### Обработка файлов:
```
🔄 Starting document processing...
📁 Found 3 files to process (total size: 215.0 KB)
📄 [1/3] Processing: lecture1.txt (125.3 KB)
   📖 Read 128457 characters
   ✂️  Split into 23 chunks
   🧮 Generating embeddings for 23 chunks...
      Embedding chunk 1/23
      Embedding chunk 10/23
      Embedding chunk 20/23
   💾 Uploading 23 vectors to Qdrant...
   ✅ File processed successfully (23 chunks)
```

### Завершение:
```
✅ Documents processed successfully!
   course_id: MY-COURSE
   files: 3
   chunks: 67
```

---

## ⏱️ Сколько времени занимает?

Время обработки зависит от:
- **Размера файлов**: ~10 сек на 100KB текста
- **Количества chunks**: ~1-2 сек на chunk (embedding + индексация)
- **CPU/GPU нагрузки**: Embeddings генерируются на GPU

**Примерное время:**
- 1 файл (100KB, ~20 chunks) → ~30-40 секунд
- 10 файлов (1MB, ~200 chunks) → ~5-7 минут
- 100 файлов (10MB, ~2000 chunks) → ~50-70 минут

---

## 🚀 Оптимизация

Если загрузка идет медленно:

1. **Проверьте GPU**: Embeddings должны генерироваться на GPU
   ```bash
   nvidia-smi
   ```

2. **Проверьте нагрузку**:
   ```bash
   htop
   ```

3. **Увеличьте batch size** (для больших объемов):
   Отредактируйте `.env`:
   ```
   EMBEDDINGS_BATCH_SIZE=64  # вместо 32
   ```

---

## ❌ Что делать при ошибках?

Если что-то пошло не так:

1. **Проверьте логи**:
   ```bash
   tail -50 logs/backend_with_progress.log
   ```

2. **Проверьте статус сервисов**:
   ```bash
   curl http://localhost:8888/health
   ```

3. **Перезапустите backend**:
   ```bash
   pkill -f start_backend
   python start_backend.py > logs/backend_new.log 2>&1 &
   ```

---

**Готово!** Теперь вы можете следить за всем процессом загрузки в реальном времени 🎉
