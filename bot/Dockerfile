FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода бота
COPY . .

# Создание файла для токенов если его нет
RUN touch bot_user_tokens.json

# Запуск бота
CMD ["python", "bot.py"]
