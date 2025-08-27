#!/usr/bin/env python3
"""
Скрипт инициализации Telegram бота для Foodgram
"""

import os
import json
from pathlib import Path

def create_bot_files():
    """Создает необходимые файлы для бота"""
    
    # Создаем папку bot если её нет
    bot_dir = Path("bot")
    bot_dir.mkdir(exist_ok=True)
    
    # Создаем файл токенов если его нет
    tokens_file = bot_dir / "bot_user_tokens.json"
    if not tokens_file.exists():
        tokens_file.write_text("{}", encoding="utf-8")
        print("✅ Создан файл bot_user_tokens.json")
    
    # Создаем .env если его нет
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# Django settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram_db
DB_USER=foodgram_user
DB_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# API settings
API_PAGE_SIZE=10

# Media and Static
MEDIA_URL=/media/
STATIC_URL=/static/
"""
        env_file.write_text(env_content, encoding="utf-8")
        print("✅ Создан файл .env")
        print("⚠️  Не забудьте настроить TELEGRAM_BOT_TOKEN в .env")
    
    print("\n🎯 Файлы бота созданы!")
    print("📝 Следующие шаги:")
    print("1. Получите токен бота у @BotFather")
    print("2. Добавьте токен в .env файл")
    print("3. Запустите: docker-compose up -d")

def check_docker_compose():
    """Проверяет наличие docker-compose.yml"""
    if not Path("docker-compose.yml").exists():
        print("❌ Файл docker-compose.yml не найден!")
        print("Убедитесь, что вы находитесь в корне проекта Foodgram")
        return False
    return True

def main():
    print("🤖 Инициализация Telegram бота для Foodgram")
    print("=" * 50)
    
    if not check_docker_compose():
        return
    
    create_bot_files()
    
    print("\n🎉 Инициализация завершена!")
    print("Теперь вы можете запустить бота командой:")
    print("docker-compose up -d")

if __name__ == "__main__":
    main()
