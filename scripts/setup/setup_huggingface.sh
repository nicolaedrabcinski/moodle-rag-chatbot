#!/bin/bash

# ═══════════════════════════════════════════════════════════════════
# Настройка HuggingFace и доступ к gated моделям
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Активация venv
source "$PROJECT_ROOT/.venv/bin/activate"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🔐 НАСТРОЙКА HUGGINGFACE                                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Проверка текущего статуса
echo -e "${YELLOW}Проверка текущего статуса...${NC}"
if huggingface-cli whoami &>/dev/null; then
    echo -e "${GREEN}✓ Вы уже залогинены в HuggingFace:${NC}"
    huggingface-cli whoami
    echo ""
    read -p "Перелогиниться? (y/n): " relogin
    if [[ ! $relogin =~ ^[Yy]$ ]]; then
        echo "Используем текущую авторизацию"
    else
        echo ""
        echo -e "${YELLOW}Выполните вход заново:${NC}"
        huggingface-cli login
    fi
else
    echo -e "${RED}✗ Вы не залогинены${NC}"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  ШАГ 1: ПОЛУЧЕНИЕ ACCESS TOKEN${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "1. Откройте в браузере: https://huggingface.co/settings/tokens"
    echo "2. Нажмите 'New token'"
    echo "3. Выберите 'Write' access"
    echo "4. Скопируйте созданный токен"
    echo ""
    read -p "Готовы продолжить? (y/n): " ready
    if [[ ! $ready =~ ^[Yy]$ ]]; then
        echo "Отменено"
        exit 0
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  ШАГ 2: ВХОД В СИСТЕМУ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    huggingface-cli login
fi

# Проверка успешности логина
if ! huggingface-cli whoami &>/dev/null; then
    echo ""
    echo -e "${RED}✗ Не удалось войти в систему${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Успешно залогинены!${NC}"
echo ""

# Список gated моделей
declare -a GATED_MODELS=(
    "meta-llama/Meta-Llama-3.1-8B-Instruct"
    "google/gemma-2-9b-it"
    "google/gemma-2-2b-it"
    "CohereForAI/c4ai-command-r-v01"
)

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  ШАГ 3: ЗАПРОС ДОСТУПА К GATED МОДЕЛЯМ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Нужно запросить доступ к следующим моделям:"
echo ""

for model in "${GATED_MODELS[@]}"; do
    echo "  • $model"
done

echo ""
echo "Для каждой модели:"
echo "1. Откройте страницу модели на HuggingFace"
echo "2. Найдите кнопку 'Agree and access repository' или 'Request Access'"
echo "3. Согласитесь с условиями и отправьте запрос"
echo "4. Дождитесь одобрения (обычно автоматически, несколько минут)"
echo ""

echo -e "${YELLOW}Открыть страницы моделей в браузере? (требуется xdg-open)${NC}"
read -p "(y/n): " open_browser

if [[ $open_browser =~ ^[Yy]$ ]]; then
    for model in "${GATED_MODELS[@]}"; do
        url="https://huggingface.co/$model"
        echo "Открываю: $url"
        if command -v xdg-open &>/dev/null; then
            xdg-open "$url" 2>/dev/null &
            sleep 2
        else
            echo "  URL: $url"
        fi
    done
else
    echo ""
    echo "Откройте вручную следующие URL:"
    for model in "${GATED_MODELS[@]}"; do
        echo "  https://huggingface.co/$model"
    done
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  ОЖИДАНИЕ ОДОБРЕНИЯ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "После запроса доступа ко всем моделям, дождитесь одобрения."
echo "Обычно это происходит автоматически в течение нескольких минут."
echo ""
read -p "Нажмите Enter когда получите доступ ко всем моделям..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  ПРОВЕРКА ДОСТУПА${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

success_count=0
failed_count=0

for model in "${GATED_MODELS[@]}"; do
    echo -n "Проверка $model... "
    
    # Попытка получить информацию о модели
    if huggingface-cli download "$model" --info 2>/dev/null | grep -q "repo_id"; then
        echo -e "${GREEN}✓ Доступ есть${NC}"
        ((success_count++))
    else
        echo -e "${RED}✗ Нет доступа${NC}"
        ((failed_count++))
    fi
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"

if [ $failed_count -eq 0 ]; then
    echo -e "${GREEN}✓ Доступ ко всем моделям получен!${NC}"
    echo ""
    echo "Теперь можете скачать модели:"
    echo "  bash scripts/downloads/download_all_models.sh"
else
    echo -e "${YELLOW}⚠ Доступ получен к $success_count из ${#GATED_MODELS[@]} моделей${NC}"
    echo ""
    echo "Проверьте страницы моделей без доступа и повторите запрос."
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
