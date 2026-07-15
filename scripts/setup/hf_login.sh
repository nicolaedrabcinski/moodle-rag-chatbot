#!/bin/bash

# ═══════════════════════════════════════════════════════════════════
# Быстрая настройка HuggingFace (только логин)
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

source "$PROJECT_ROOT/.venv/bin/activate"

cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════╗
║           🔐 ВХОД В HUGGINGFACE                                   ║
╚═══════════════════════════════════════════════════════════════════╝

1. Получите токен: https://huggingface.co/settings/tokens
2. Создайте токен с 'Write' доступом
3. Вставьте токен в запрос ниже

═══════════════════════════════════════════════════════════════════

EOF

# Проверка текущего статуса
if huggingface-cli whoami &>/dev/null; then
    echo "✓ Вы уже залогинены:"
    huggingface-cli whoami
    echo ""
    read -p "Перелогиниться? (y/n): " relogin
    if [[ ! $relogin =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "Выполните вход:"
huggingface-cli login

if huggingface-cli whoami &>/dev/null; then
    echo ""
    echo "✓ Успешно залогинены!"
    echo ""
    echo "Теперь запросите доступ к gated моделям:"
    echo "  bash scripts/setup/setup_huggingface.sh"
else
    echo ""
    echo "✗ Не удалось войти"
    exit 1
fi
