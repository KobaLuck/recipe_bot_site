# Recipes + Telegram · быстрый запуск

```bash
git clone https://github.com/KobaLuck/recipe_bot_site.git
cd recipe_bot_site
cp env.example .env
```

Заполните настройки PostgreSQL, Django и `TELEGRAM_BOT_TOKEN` в `.env`.
Адрес API для бота в Docker задаётся через `SITE_API_BASE` и должен указывать
на доступный из контейнера backend.

```bash
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --noinput
docker compose exec backend python manage.py createsuperuser
```

Откройте `http://localhost:7000`. Добавьте теги и ингредиенты через админку,
затем отправьте боту `/start`. Для просмотра состояния: `docker compose ps`.
Для диагностики: `docker compose logs --tail=100 backend bot`.
Остановить сервисы с сохранением томов: `docker compose down`.

[Основной README](README.md) · [Документация бота](bot/README.md)
