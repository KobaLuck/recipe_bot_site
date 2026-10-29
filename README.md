# Recipes + Telegram

Сайт рецептов и Telegram-интерфейс для регистрации, входа и пошагового создания рецепта.

**Python · Django · React · PostgreSQL · python-telegram-bot**

## Быстрый старт

```bash
git clone https://github.com/KobaLuck/recipe_bot_site.git
cd recipe_bot_site
cp env.example .env
# Настройте БД, ключ Django и токен бота
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --noinput
```

Сайт доступен на `http://localhost:7000`; бот обращается к backend по адресу из `SITE_API_BASE`. Пошаговый запуск: [QUICK_START.md](QUICK_START.md).

## Структура

- `backend/` — серверная часть.
- `frontend/` — веб-интерфейс.
- `bot/` — telegram-бот.
- `docs/` — документация.
- `infra/` — конфигурация инфраструктуры.
- `postman_collection/` — коллекции запросов.

---

[Никита Казанцев](https://github.com/KobaLuck) · [Все публичные проекты](https://github.com/KobaLuck?tab=repositories)
