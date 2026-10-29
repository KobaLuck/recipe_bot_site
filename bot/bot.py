import os
import json
import base64
import aiohttp
from pathlib import Path
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# FSM states
(
    AUTH_CHOICE,        # выбор: login / register / anonymous
    AUTH_LOGIN_EMAIL,
    AUTH_LOGIN_PASS,
    AUTH_REGISTER_EMAIL,
    AUTH_REGISTER_USERNAME,
    AUTH_REGISTER_FIRST,
    AUTH_REGISTER_LAST,
    AUTH_REGISTER_PASS,
    RECIPE_NAME,
    RECIPE_DESC,
    COOK_TIME,
    ING_LETTER,         # выбрать букву
    ING_PAGE,           # навигация страниц ингредиентов
    ING_SELECT,         # выбрать конкретный ингредиент
    ING_QTY,
    ING_CONFIRM_CHOOSE,  # добавить ещё или готово
    TAGS_CHOOSE,        # выбрать теги (пагинация)
    IMAGE_STEP,
    URL_STEP,
    CONFIRM_STEP,
) = range(20)

# Config from env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SITE_API_BASE = os.getenv(
    "SITE_API_BASE", "http://localhost:8000/api/"
).rstrip("/") + "/"
API_PAGE_SIZE = int(os.getenv("API_PAGE_SIZE", 10))
TOKENS_FILE = Path("bot_user_tokens.json")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в окружении")


if not SITE_API_BASE:
    raise RuntimeError("SITE_API_BASE не задан в окружении")

# placeholder 1x1 transparent png (data-uri)
PLACEHOLDER_PNG_DATAURI = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAe0lEQVR4nO3PQQ0AIBDAsPOvDxH8MYAIHg3Jkgno5uz1dcMFDWhBA1rQgBY0oAUNaEEDWtCAFjSgBQ1oQQNa0IAWNKAFDWhBA1rQgBY0oAUNaEEDWtCAFjSgBQ1oQQNa0IAWNKAFDWhBA1rQgBY0oAUNaEEDWtCAFjx2AdXk8ndJ+FMbAAAAAElFTkSuQmCC'

# --------------------------
# API клиент (aiohttp)
# --------------------------
async def api_request(method: str, path: str, token: Optional[str] = None,
                      params: dict = None, json_data: dict = None, timeout=20):
    url = SITE_API_BASE.rstrip("/") + "/" + path.lstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    
    async with aiohttp.ClientSession() as sess:
        func = getattr(sess, method.lower())
        async with func(url, params=params, json=json_data, headers=headers, timeout=timeout) as resp:
            text = await resp.text()
            try:
                data = await resp.json()
            except Exception:
                data = None
            return resp.status, data or text

async def api_get(path: str, params: dict = None, token: Optional[str] = None):
    return await api_request("get", path, token=token, params=params)

async def api_post(path: str, json_data: dict = None, token: Optional[str] = None):
    return await api_request("post", path, token=token, json_data=json_data)

# --------------------------
# Управление токенами пользователей
# --------------------------
def save_token_local(telegram_id: int, token: str):
    data = {}
    if TOKENS_FILE.exists():
        try:
            data = json.loads(TOKENS_FILE.read_text(encoding="utf-8") or "{}")
        except Exception:
            data = {}
    data[str(telegram_id)] = token
    TOKENS_FILE.write_text(json.dumps(data), encoding="utf-8")

def load_token_local(telegram_id: int) -> Optional[str]:
    if not TOKENS_FILE.exists():
        return None
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return data.get(str(telegram_id))

def del_token_local(telegram_id: int):
    if not TOKENS_FILE.exists():
        return
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return
    data.pop(str(telegram_id), None)
    TOKENS_FILE.write_text(json.dumps(data), encoding="utf-8")

# --------------------------
# Вспомогательные функции
# --------------------------
def format_api_errors(err_obj) -> str:
    """Форматирование ошибок от Django REST Framework"""
    if not err_obj:
        return "Неизвестная ошибка на сервере."
    if isinstance(err_obj, dict):
        parts = []
        for k, v in err_obj.items():
            if isinstance(v, (list, tuple)):
                parts.append(f"{k}: {', '.join(str(x) for x in v)}")
            else:
                parts.append(f"{k}: {v}")
        return "\n".join(parts) if parts else "Ошибка валидации."
    if isinstance(err_obj, list):
        return "\n".join(str(x) for x in err_obj)
    return str(err_obj)

async def download_photo_as_datauri(file_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Скачивает фото из Telegram и конвертирует в data-uri"""
    try:
        f = await context.bot.get_file(file_id)
        b = await f.download_as_bytearray()
        ext = "jpeg"
        if f.file_path and "." in f.file_path:
            ext = f.file_path.rsplit(".", 1)[1]
        b64 = base64.b64encode(bytes(b)).decode("ascii")
        return f"data:image/{ext};base64,{b64}"
    except Exception:
        return PLACEHOLDER_PNG_DATAURI

# --------------------------
# Обработчики аутентификации
# --------------------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение и выбор способа аутентификации"""
    user = update.effective_user
    text = (
        f"Привет, {user.first_name or user.username or 'друг'}!\n\n"
        "Я — бот для работы с рецептами на сайте Foodgram. Выберите, как продолжить:\n\n"
        "• Войти (email + пароль)\n"
        "• Зарегистрироваться\n"
        "• Продолжить как аноним (только просмотр)\n\n"
        "При входе рецепты будут создаваться под вашим аккаунтом."
    )
    kb = [
        [InlineKeyboardButton("Войти", callback_data="auth:login")],
        [InlineKeyboardButton("Регистрация", callback_data="auth:register")],
        [InlineKeyboardButton("Аноним", callback_data="auth:anon")],
    ]
    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    return AUTH_CHOICE

async def auth_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data.split(":", 1)[1]
    if action == "login":
        await q.message.reply_text("Введите email для входа:")
        return AUTH_LOGIN_EMAIL
    if action == "register":
        await q.message.reply_text("Регистрация — введите email:")
        return AUTH_REGISTER_EMAIL
    if action == "anon":
        del_token_local(q.from_user.id)
        await q.message.reply_text("Вы продолжаете как аноним. Создание рецептов недоступно.")
        return ConversationHandler.END
    await q.message.reply_text("Неизвестный выбор.")
    return ConversationHandler.END

# Логин
async def auth_login_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["auth_email"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Введите пароль:")
    return AUTH_LOGIN_PASS

async def auth_login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = context.user_data.pop("auth_email", None)
    password = update.effective_message.text.strip()
    
    # Djoser token login
    payload = {"email": email, "password": password}
    status, data = await api_post("auth/token/login/", json_data=payload)
    
    if status in (200, 201) and isinstance(data, dict) and data.get("auth_token"):
        token = data["auth_token"]
        save_token_local(update.effective_user.id, token)
        await update.effective_message.reply_text("✅ Успешный вход! Теперь вы можете создавать рецепты.")
        return ConversationHandler.END
    
    msg = format_api_errors(data)
    await update.effective_message.reply_text(f"❌ Ошибка входа: {msg}")
    return AUTH_LOGIN_EMAIL

# Регистрация
async def auth_register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_email"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Введите желаемый username:")
    return AUTH_REGISTER_USERNAME

async def auth_register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_username"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Имя (first_name):")
    return AUTH_REGISTER_FIRST

async def auth_register_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_first"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Фамилия (last_name):")
    return AUTH_REGISTER_LAST

async def auth_register_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_last"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Пароль:")
    return AUTH_REGISTER_PASS

async def auth_register_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = context.user_data.pop("reg_email", None)
    username = context.user_data.pop("reg_username", None)
    first = context.user_data.pop("reg_first", "")
    last = context.user_data.pop("reg_last", "")
    password = update.effective_message.text.strip()
    
    payload = {
        "email": email,
        "username": username,
        "first_name": first,
        "last_name": last,
        "password": password,
    }
    
    # Создание пользователя
    status, data = await api_post("auth/users/", json_data=payload)
    if status in (200, 201):
        # Автоматический вход после регистрации
        status2, data2 = await api_post("auth/token/login/", json_data={"email": email, "password": password})
        if status2 in (200, 201) and isinstance(data2, dict) and data2.get("auth_token"):
            save_token_local(update.effective_user.id, data2["auth_token"])
            await update.effective_message.reply_text("✅ Регистрация и вход успешно выполнены!")
            return ConversationHandler.END
        await update.effective_message.reply_text("Регистрация выполнена, но автологин не удался. Попробуйте войти вручную.")
        return ConversationHandler.END
    
    await update.effective_message.reply_text("❌ Ошибка регистрации: " + format_api_errors(data))
    return AUTH_REGISTER_EMAIL

# --------------------------
# Создание рецепта
# --------------------------
async def start_add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск создания рецепта"""
    q = update.callback_query
    if q:
        await q.answer()
    
    context.user_data.clear()
    await (q.message if q else update.effective_message).reply_text(
        "🍳 Создание рецепта — введите название:"
    )
    return RECIPE_NAME

async def recipe_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Введите описание рецепта:")
    return RECIPE_DESC

async def recipe_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("⏱️ Укажите время приготовления в минутах:")
    return COOK_TIME

async def recipe_cook_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.effective_message.text.strip()
    if not txt.isdigit() or int(txt) < 1:
        await update.effective_message.reply_text("❌ Время должно быть целым числом ≥ 1. Попробуйте ещё раз:")
        return COOK_TIME
    
    context.user_data["cooking_time"] = int(txt)
    context.user_data["ingredients"] = []
    
    # Выбор буквы для ингредиентов
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
    kb = []
    row = []
    for i, ch in enumerate(letters):
        row.append(InlineKeyboardButton(ch, callback_data=f"ing_letter:{ch}"))
        if (i + 1) % 6 == 0:
            kb.append(row); row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("✅ Готово (к тегам)", callback_data="ing_done")])
    
    await update.effective_message.reply_text(
        "🔤 Выберите первую букву ингредиента:",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ING_LETTER

# Выбор ингредиентов
async def ing_letter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    letter = q.data.split(":", 1)[1]
    context.user_data.setdefault("ing_browser", {})["letter"] = letter
    
    status, data = await api_get("ingredients/", params={"name": letter, "page": 1})
    if status != 200:
        await q.message.reply_text("❌ Ошибка получения ингредиентов: " + format_api_errors(data))
        return ING_LETTER
    
    context.user_data["ing_browser"]["page"] = 1
    await show_ingredient_page(q.message, data, letter, 1)
    return ING_PAGE

async def show_ingredient_page(message, resp_json, letter, page):
    """Отображение страницы ингредиентов"""
    results = resp_json.get("results") if isinstance(resp_json, dict) else resp_json
    buttons = []
    
    for item in results:
        buttons.append([InlineKeyboardButton(
            f"{item['name']} ({item.get('measurement_unit','')})", 
            callback_data=f"ing_select:{item['id']}"
        )])
    
    # Навигация
    nav = []
    if isinstance(resp_json, dict) and resp_json.get("previous"):
        nav.append(InlineKeyboardButton("‹ Назад", callback_data=f"ing_page:{letter}:{page-1}"))
    if isinstance(resp_json, dict) and resp_json.get("next"):
        nav.append(InlineKeyboardButton("Вперёд ›", callback_data=f"ing_page:{letter}:{page+1}"))
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("🔤 Назад к буквам", callback_data="ing_back_letters")])
    await message.reply_text("Выберите ингредиент:", reply_markup=InlineKeyboardMarkup(buttons))

async def ing_page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, letter, page_s = q.data.split(":", 2)
    page = int(page_s)
    
    status, data = await api_get("ingredients/", params={"name": letter, "page": page})
    if status != 200:
        await q.message.reply_text("❌ Ошибка получения ингредиентов: " + format_api_errors(data))
        return ING_LETTER
    
    context.user_data["ing_browser"]["page"] = page
    await show_ingredient_page(q.message, data, letter, page)
    return ING_PAGE

async def ing_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, ing_id = q.data.split(":", 1)
    context.user_data["selected_ing"] = int(ing_id)
    await q.message.reply_text("📊 Введите количество:")
    return ING_QTY

async def ing_qty_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.effective_message.text.strip()
    if not txt.isdigit() or int(txt) < 1:
        await update.effective_message.reply_text("❌ Количество должно быть ≥ 1. Попробуйте ещё раз:")
        return ING_QTY
    
    ing_id = context.user_data.pop("selected_ing")
    ingredients = context.user_data.setdefault("ingredients", [])
    for ingredient in ingredients:
        if ingredient["id"] == ing_id:
            ingredient["amount"] += int(txt)
            break
    else:
        ingredients.append({"id": ing_id, "amount": int(txt)})
    
    kb = [
        [InlineKeyboardButton("➕ Добавить ещё", callback_data="ing_back_letters")],
        [InlineKeyboardButton("✅ Готово — к тегам", callback_data="ing_done")],
    ]
    await update.effective_message.reply_text("✅ Ингредиент добавлен!", reply_markup=InlineKeyboardMarkup(kb))
    return ING_CONFIRM_CHOOSE

async def ing_confirm_choose_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "ing_back_letters":
        # Показать буквы заново
        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
        kb = []
        row = []
        for i, ch in enumerate(letters):
            row.append(InlineKeyboardButton(ch, callback_data=f"ing_letter:{ch}"))
            if (i + 1) % 6 == 0:
                kb.append(row); row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("✅ Готово (к тегам)", callback_data="ing_done")])
        await q.message.reply_text("🔤 Выберите букву:", reply_markup=InlineKeyboardMarkup(kb))
        return ING_LETTER
    
    if q.data == "ing_done":
        if not context.user_data.get("ingredients"):
            await q.message.reply_text("Добавьте хотя бы один ингредиент.")
            return ING_LETTER
        return await tags_start(q.message, context)

# Выбор тегов
async def tags_start(message, context: ContextTypes.DEFAULT_TYPE):
    status, data = await api_get("tags/", params={"page": 1})
    if status != 200:
        await message.reply_text("❌ Ошибка получения тегов: " + format_api_errors(data))
        return TAGS_CHOOSE
    
    context.user_data["tags_browser"] = {"page": 1}
    await show_tags_page(message, data, 1)
    return TAGS_CHOOSE

async def show_tags_page(message, resp_json, page):
    results = resp_json.get("results") if isinstance(resp_json, dict) else resp_json
    buttons = []
    
    for t in results:
        buttons.append([InlineKeyboardButton(t["name"], callback_data=f"tag_select:{t['id']}")])
    
    nav = []
    if isinstance(resp_json, dict) and resp_json.get("previous"):
        nav.append(InlineKeyboardButton("‹ Назад", callback_data=f"tag_page:{page-1}"))
    if isinstance(resp_json, dict) and resp_json.get("next"):
        nav.append(InlineKeyboardButton("Вперёд ›", callback_data=f"tag_page:{page+1}"))
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("✅ Готово (далее)", callback_data="tags_done")])
    await message.reply_text("🏷️ Выберите теги:", reply_markup=InlineKeyboardMarkup(buttons))

async def tag_page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, page_s = q.data.split(":", 1)
    page = int(page_s)
    
    status, data = await api_get("tags/", params={"page": page})
    if status != 200:
        await q.message.reply_text("❌ Ошибка получения тегов: " + format_api_errors(data))
        return TAGS_CHOOSE
    
    context.user_data["tags_browser"]["page"] = page
    await show_tags_page(q.message, data, page)
    return TAGS_CHOOSE

async def tag_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, tag_id_s = q.data.split(":", 1)
    tag_id = int(tag_id_s)
    
    sel = context.user_data.setdefault("selected_tags", set())
    if tag_id in sel:
        sel.remove(tag_id)
        await q.message.reply_text("❌ Тег убран из выбора.")
    else:
        sel.add(tag_id)
        await q.message.reply_text("✅ Тег добавлен.")
    
    return TAGS_CHOOSE

async def tags_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    tags = list(context.user_data.get("selected_tags", []))
    if not tags:
        await q.message.reply_text("❌ Нужно выбрать хотя бы один тег. Выберите тег.")
        return TAGS_CHOOSE
    
    context.user_data["tags"] = tags
    await q.message.reply_text(
        "📸 Пришлите фото рецепта (или нажмите Пропустить):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_image")]])
    )
    return IMAGE_STEP

# Обработка фото
async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "skip_image":
            context.user_data["image_datauri"] = None
    else:
        photo = update.effective_message.photo
        if not photo:
            await update.effective_message.reply_text("❌ Ожидалось фото. Повторите или нажмите Пропустить.")
            return IMAGE_STEP
        
        file_id = photo[-1].file_id
        context.user_data["image_file_id"] = file_id
    
    await update.effective_message.reply_text(
        "🔗 Добавьте ссылку на источник (или нажмите Пропустить):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_url")]])
    )
    return URL_STEP

# Обработка URL
async def url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "skip_url":
            context.user_data["source_url"] = None
    else:
        context.user_data["source_url"] = update.effective_message.text.strip()

    # Сводка для подтверждения
    data = context.user_data
    ing_text = "\n".join(f"- {i['id']} × {i['amount']}" for i in data.get("ingredients", []))
    tags_text = ", ".join(str(t) for t in data.get("tags", []))
    
    summary = (
        f"📋 Проверьте рецепт:\n\n"
        f"Название: {data.get('name')}\n"
        f"Описание: {data.get('description')}\n"
        f"Время: {data.get('cooking_time')} мин\n"
        f"Ингредиенты:\n{ing_text or '-'}\n"
        f"Теги: {tags_text}\n"
        f"Фото: {'✅ есть' if data.get('image_file_id') else '❌ нет'}\n"
        f"Ссылка: {data.get('source_url') or '-'}\n\n"
        "Нажмите Подтвердить для отправки на сайт."
    )
    
    kb = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_send")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    
    await (update.callback_query.message if update.callback_query else update.effective_message).reply_text(
        summary, reply_markup=InlineKeyboardMarkup(kb)
    )
    return CONFIRM_STEP

# Отправка рецепта
async def confirm_send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    token = load_token_local(q.from_user.id)
    if not token:
        await q.message.reply_text("❌ Вы не вошли в систему. Для создания рецепта нужно войти (/start → Войти).")
        return ConversationHandler.END

    data = context.user_data
    
    # Обработка фото
    if data.get("image_file_id"):
        image_datauri = await download_photo_as_datauri(data["image_file_id"], context)
    else:
        image_datauri = PLACEHOLDER_PNG_DATAURI

    # Объединение описания и ссылки
    text = data.get("description", "")
    if data.get("source_url"):
        text = text + "\n\nСсылка на источник: " + data["source_url"]

    payload = {
        "name": data.get("name"),
        "text": text,
        "cooking_time": int(data.get("cooking_time")),
        "ingredients": [{"id": i["id"], "amount": i["amount"]} for i in data.get("ingredients", [])],
        "tags": data.get("tags", []),
        "image": image_datauri,
    }
    
    # POST /api/recipes/
    status, resp = await api_post("recipes/", json_data=payload, token=token)
    if status in (200, 201) and isinstance(resp, dict):
        await q.message.reply_text("🎉 Рецепт успешно создан на сайте!")
        return ConversationHandler.END
    
    await q.message.reply_text("❌ Ошибка при создании: " + format_api_errors(resp))
    return ConversationHandler.END

# Отмена
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("❌ Операция отменена.")
    else:
        await update.effective_message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END

# --------------------------
# Основные команды
# --------------------------
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = """
🤖 Доступные команды:

/start - Начать работу с ботом
/help - Показать эту справку
/add - Создать новый рецепт
/recipes - Посмотреть рецепты
/login - Войти в аккаунт
/register - Зарегистрироваться
/cancel - Отменить текущую операцию

💡 Для создания рецептов необходимо войти в аккаунт
    """
    await update.effective_message.reply_text(help_text)

async def recipes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список рецептов"""
    status, data = await api_get("recipes/", params={"page": 1, "page_size": 5})
    
    if status != 200:
        await update.effective_message.reply_text("❌ Ошибка получения рецептов: " + format_api_errors(data))
        return
    
    results = data.get("results", data) if isinstance(data, dict) else data
    if not results:
        await update.effective_message.reply_text("📝 Рецептов пока нет.")
        return
    
    response = "🍽️ Последние рецепты:\n\n"
    for r in results[:5]:
        response += f"• {r.get('name', 'Без названия')} - {r.get('cooking_time', 0)} мин\n"
    
    if isinstance(data, dict) and data.get("next"):
        response += "\n📄 Для просмотра всех рецептов перейдите на сайт."
    
    await update.effective_message.reply_text(response)

# --------------------------
# Построение обработчиков
# --------------------------
def build_conv_handler():
    """Создание обработчика для создания рецептов"""
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_recipe, pattern="^add_recipe$"),
            CommandHandler("add", start_add_recipe),
            CommandHandler("addrecipe", start_add_recipe),
        ],
        states={
            RECIPE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_name)],
            RECIPE_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_desc)],
            COOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_cook_time)],
            ING_LETTER: [
                CallbackQueryHandler(ing_letter_handler, pattern="^ing_letter:"),
                CallbackQueryHandler(ing_confirm_choose_handler, pattern="^ing_done$"),
            ],
            ING_PAGE: [
                CallbackQueryHandler(ing_page_handler, pattern="^ing_page:"),
                CallbackQueryHandler(ing_select_handler, pattern="^ing_select:"),
                CallbackQueryHandler(ing_confirm_choose_handler, pattern="^(ing_back_letters|ing_done)$"),
            ],
            ING_SELECT: [CallbackQueryHandler(ing_select_handler, pattern="^ing_select:")],
            ING_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ing_qty_handler)],
            ING_CONFIRM_CHOOSE: [CallbackQueryHandler(ing_confirm_choose_handler, pattern="^(ing_back_letters|ing_done)$")],
            TAGS_CHOOSE: [
                CallbackQueryHandler(tag_page_handler, pattern="^tag_page:"),
                CallbackQueryHandler(tag_select_handler, pattern="^tag_select:"),
                CallbackQueryHandler(tags_done_handler, pattern="^tags_done$"),
            ],
            IMAGE_STEP: [
                MessageHandler(filters.PHOTO, image_handler),
                CallbackQueryHandler(image_handler, pattern="^skip_image$"),
            ],
            URL_STEP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, url_handler),
                CallbackQueryHandler(url_handler, pattern="^skip_url$"),
            ],
            CONFIRM_STEP: [
                CallbackQueryHandler(confirm_send_handler, pattern="^confirm_send$"),
                CallbackQueryHandler(cancel_handler, pattern="^cancel$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_handler, pattern="^cancel$"), 
            CommandHandler("cancel", cancel_handler)
        ],
        per_user=True,
        per_chat=True,
    )
    return conv

def build_auth_conv():
    """Создание обработчика для аутентификации"""
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_handler), 
            CallbackQueryHandler(auth_choice_handler, pattern="^auth:")
        ],
        states={
            AUTH_CHOICE: [CallbackQueryHandler(auth_choice_handler, pattern="^auth:")],
            AUTH_LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_login_email)],
            AUTH_LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_login_pass)],
            AUTH_REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_register_email)],
            AUTH_REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_register_username)],
            AUTH_REGISTER_FIRST: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_register_first)],
            AUTH_REGISTER_LAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_register_last)],
            AUTH_REGISTER_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_register_pass)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_user=True,
        per_chat=True,
    )
    return conv

# --------------------------
# Главная функция
# --------------------------
def main():
    """Основная функция запуска бота"""
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Обработчики
    auth_conv = build_auth_conv()
    add_conv = build_conv_handler()
    
    app.add_handler(auth_conv)
    app.add_handler(add_conv)
    
    # Основные команды
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("recipes", recipes_handler))
    
    # Обработчик отмены
    app.add_handler(CommandHandler("cancel", cancel_handler))
    
    print("🤖 Бот Foodgram запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
