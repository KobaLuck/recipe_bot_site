#  Foodgram

Социальная сеть для создания и обмена рецептами. Позволяет добавлять рецепты в корзину для автоматического формирования списка покупок.


##  Сайт проекта

Рабочая версия доступна по адресу: [https://vikathebest.ddns.net](https://vikathebest.ddns.net)

---

##  Автор

**Казанцев Никита Игоревич**
**GitHub:** [https://github.com/KobaLuck](https://github.com/KobaLuck)

---

##  Технологический стек

* **Backend:** Python 3, Django 3.2.3, Django REST Framework 3.12.4, Djoser 2.1.0, django-filter 2.4.0, PyYAML 6.0, webcolors 1.11.1, Pillow 9.0.0, Gunicorn 20.1.0, psycopg2-binary 2.9.3
* **Frontend:** React 17.0.1 (SPA на Create React App)
* **База данных:** PostgreSQL 13
* **Сервер:** Nginx, Gunicorn
* **Контейнеризация:** Docker, Docker Compose
* **CI/CD:** GitHub Actions, DockerHub, автоматический деплой по SSH
* **Volumes:** pg\_data, static, media
* **Telegram Bot:** python-telegram-bot, aiohttp, интеграция с Django API

---

##  CI/CD Pipeline

GitHub Actions на каждом `push` в репозиторий:

1. Проверка синтаксиса и линтинг — flake8
2. Юнит-тесты (при необходимости)
3. Сборка и пуш Docker-образов для backend, frontend и gateway на DockerHub
4. Автоматический деплой на удалённый сервер по SSH (для ветки `main`):

   * копирование `docker-compose.production.yml`
   * pull, down/up контейнеров
   * миграции и сбор статики
   * уведомления в Telegram при успехе и при сбое

---

##  Локальное развертывание через Docker

### 1. Клонирование репозитория

```bash
git clone https://github.com/KobaLuck/foodgram.git
cd foodgram
```

### 2. Подготовка `.env`

Создайте файл `.env` на основе `env.example`:

```bash
cp env.example .env
```

Пример содержимого `env.example`:

```ini
# Django settings
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
```

### 3. Подъем контейнеров

```bash
docker-compose up --build -d
```

### 4. Подготовка базы и загрузка данных

```bash
docker-compose exec backend python manage.py migrate
```

Создание суперпользователя:

```bash
docker-compose exec backend python manage.py createsuperuser
```

Загрузка фикстур:

```bash
docker-compose exec backend python manage.py loaddata ingredients.json
```

### 5. Сбор статики

```bash
docker-compose exec backend python manage.py collectstatic --noinput
```

### 6. Доступ к приложению

* **Frontend:** [http://localhost](http://localhost)
* **API-документация:** [http://localhost/api/docs/](http://localhost/api/docs/)
* **Telegram Bot:** настройте токен в `.env` и перезапустите контейнеры

### 7. Настройка Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен и добавьте в `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
3. Перезапустите контейнеры:
   ```bash
   docker-compose down && docker-compose up -d
   ```
4. Бот автоматически запустится и будет доступен в Telegram

### 8. Управление проектом

```bash
# Запуск сервисов
docker-compose up -d

# Остановка сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f

# Перезапуск бота
docker-compose restart bot

# Применение миграций
docker-compose exec backend python manage.py migrate

# Создание суперпользователя
docker-compose exec backend python manage.py createsuperuser

# Загрузка данных
docker-compose exec backend python manage.py loaddata ingredients.json

# Сбор статических файлов
docker-compose exec backend python manage.py collectstatic --noinput
```

---

##  Локальное развертывание **без Docker**

### 1. Клонирование репозитория

```bash
git clone https://github.com/KobaLuck/foodgram.git
cd foodgram
```

### 2. Создание и активация виртуального окружения

```bash
python -m venv venv
source venv/bin/activate    # или Windows: venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 4. Подготовка `.env`

```bash
cp env.example .env
```

### 5. Миграции и суперпользователь

```bash
python backend/manage.py migrate
python backend/manage.py createsuperuser
```

### 6. Импорт данных

```bash
python backend/manage.py loaddata ingredients.json
```

### 7. Запуск сервера

```bash
cd backend
python manage.py runserver
```

* **Backend (API):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Frontend:** запустите отдельным `npm start` в папке `frontend` по инструкции React
* **API-документация:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)

---

##  Документация API

После запуска доступна спецификация:

* **Redoc:** [http://localhost/api/docs/](http://localhost/api/docs/)

---

## Telegram Bot

Проект включает в себя Telegram бота для работы с рецептами. Бот интегрирован с Django API и позволяет:

### Возможности бота

- 🔐 **Аутентификация** - вход и регистрация через бота
- 🍳 **Создание рецептов** - пошаговое создание с выбором ингредиентов
- 🏷️ **Управление тегами** - выбор существующих тегов для рецептов
- 📸 **Загрузка фото** - автоматическая конвертация в формат для Django
- 🔗 **Источники** - добавление ссылок на источники рецептов

### Архитектура

- **Без собственной БД** - все данные хранятся в основной PostgreSQL
- **API-first подход** - бот работает исключительно через Django REST API
- **Асинхронность** - использует aiohttp для HTTP запросов
- **FSM** - конечный автомат для управления состояниями создания рецепта

### Команды бота

- `/start` - начало работы, выбор способа аутентификации
- `/help` - справка по командам
- `/add` - создание нового рецепта
- `/recipes` - просмотр списка рецептов
- `/cancel` - отмена текущей операции

Подробная документация по боту: [bot/README.md](bot/README.md)

---

*Спасибо за использование Foodgram!*
