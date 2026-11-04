#!/usr/bin/env bash
set -e

echo "=============================================="
echo "🚀 Развертывание Price Tracker Bot в Docker"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден! Установите Docker одной командой:"
    echo "curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Create data directory for persistent SQLite database
mkdir -p data

# Rebuild and run container in background
echo "📦 Сборка и запуск контейнера..."
docker compose up -d --build

echo ""
echo "✅ Бот успешно запущен в фоновом режиме!"
echo "📋 Статус:"
docker compose ps
echo ""
echo "💡 Полезные команды:"
echo "   Посмотреть логи:      docker compose logs -f"
echo "   Остановить бота:      docker compose down"
echo "   Перезапустить бота:   docker compose restart"
