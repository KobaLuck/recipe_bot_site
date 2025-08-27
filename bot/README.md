# Foodgram Telegram Bot

Telegram бот для работы с рецептами на сайте Foodgram.

## Возможности

- 🔐 Аутентификация через Django API (Djoser)
- 👤 Регистрация новых пользователей
- 🍳 Создание рецептов через бота
- 🏷️ Выбор тегов и ингредиентов
- 📸 Загрузка фотографий рецептов
- 🔗 Добавление ссылок на источники

## Настройка

### Переменные окружения

Создайте файл `.env` в корне проекта:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# API настройки
SITE_API_BASE=http://localhost:8000/api/
API_PAGE_SIZE=10
```

### Запуск

1. Убедитесь, что Django backend запущен
2. Запустите бота:

```bash
# Локально
python bot.py
```

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/add` - Создать новый рецепт
- `/recipes` - Посмотреть рецепты
- `/cancel` - Отменить текущую операцию

## Архитектура

Бот работает исключительно через Django REST API, не имеет собственной базы данных. Все данные хранятся в основной БД Django проекта.

### Основные компоненты

- **API клиент** - асинхронные HTTP запросы к Django API
- **FSM (Finite State Machine)** - управление состояниями создания рецепта
- **Обработчики команд** - обработка команд и callback-запросов
- **Управление токенами** - локальное хранение токенов аутентификации

## Интеграция с Django

Бот использует следующие Django API endpoints:

- `POST /api/auth/users/` - регистрация пользователей
- `POST /api/auth/token/login/` - получение токена аутентификации
- `GET /api/ingredients/` - получение списка ингредиентов
- `GET /api/tags/` - получение списка тегов
- `POST /api/recipes/` - создание рецептов

## Разработка

### Структура файлов

```
bot/
├── bot.py              # Основной код бота
├── requirements.txt    # Python зависимости
├── Dockerfile         # Docker образ
└── README.md          # Документация
```

### Зависимости

- `python-telegram-bot==20.7` - Telegram Bot API
- `aiohttp==3.9.1` - HTTP клиент
- `python-dotenv==1.0.0` - управление переменными окружения

## Docker

Бот интегрирован в основной `docker-compose.yml` проекта и автоматически запускается вместе с backend'ом.

```yaml
bot:
  build: ./bot
  environment:
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - SITE_API_BASE=http://backend:8000/api/
  depends_on:
    - backend
```
