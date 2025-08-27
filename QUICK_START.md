# 🚀 Быстрый запуск Foodgram + Telegram Bot

## 📋 Предварительные требования

- Docker и Docker Compose
- Python 3.9+
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

## ⚡ Быстрый старт (5 минут)

### 1. Клонирование и настройка

```bash
# Клонируйте проект
git clone <your-repo-url>
cd foodgram

# Инициализируйте бота
python init_bot.py
```

### 2. Настройка токена

Отредактируйте `.env` файл:
```bash
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
```

### 3. Запуск

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps
```

### 4. Проверка

- **Сайт:** http://localhost:7000
- **API:** http://localhost:8000/api/
- **Бот:** найдите в Telegram по имени

## 🔧 Основные команды

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f

# Перезапуск бота
docker-compose restart bot

# Статус сервисов
docker-compose ps
```

## 🚨 Если что-то не работает

1. **Проверьте токен бота** в `.env`
2. **Пересоберите образы:** `docker-compose up --build -d`
3. **Проверьте логи:** `docker-compose logs -f`
4. **Очистите Docker:** `docker-compose down -v --rmi all && docker-compose up --build -d`

## 📚 Подробная документация

- [Документация бота](bot/README.md)
- [Основной README](README.md)

---

**🎉 Готово!** Теперь у вас есть полностью интегрированный проект Foodgram с Telegram ботом.
