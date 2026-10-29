import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# Веб-сервер для Webhook и пингов
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PASSWORD = os.getenv("PASSWORD", "7374")
DB_PATH = os.getenv("DB_PATH", "applications.db")

# Render автоматически выдает переменную RENDER_EXTERNAL_URL
# (например, https://tg-bot-k8kg.onrender.com)
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://tg-bot-k8kg.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
router = Router()

# ============ БАЗА ДАННЫХ ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            nickname TEXT,
            lvl TEXT,
            donate TEXT,
            previous_clans TEXT,
            shooting_test TEXT,
            rules_accept TEXT,
            real_name TEXT,
            age TEXT,
            experience TEXT,
            why_us TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_application(user_id, username, data: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications
        (user_id, username, nickname, lvl, donate, previous_clans,
         shooting_test, rules_accept, real_name, age, experience, why_us, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, username,
        data.get("nickname"), data.get("lvl"), data.get("donate"),
        data.get("previous_clans"), data.get("shooting_test"),
        data.get("rules_accept"), data.get("real_name"),
        data.get("age"), data.get("experience"), data.get("why_us"),
        datetime.utcnow().isoformat()
    ))
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return app_id

def get_all_pending():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE status = 'pending' ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_by_id(app_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    conn.close()
    return row

def set_status(app_id, status: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    conn.commit()
    conn.close()

# ============ СОСТОЯНИЯ ============
class Form(StatesGroup):
    nickname = State()
    lvl = State()
    donate = State()
    previous_clans = State()
    shooting_test = State()
    rules_accept = State()
    real_name = State()
    age = State()
    experience = State()
    why_us = State()

class AdminAuth(StatesGroup):
    waiting_password = State()

# ============ КЛАВИАТУРЫ ============
def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Подать анкету")], [KeyboardButton(text="Анкеты")]],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True)

def back_next_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back"),
        InlineKeyboardButton(text="Далее ➡️", callback_data="next"),
    ]])

def approve_reject_kb(app_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{app_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{app_id}"),
    ]])

# ============ ХЕНДЛЕРЫ (БЕЗ ИЗМЕНЕНИЙ) ============
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    name = message.from_user.username or message.from_user.first_name
    await message.answer(f"Привет! ({name})\nТы тут чтобы поспать в клан NS!", reply_markup=main_menu_kb())

@router.message(F.text == "Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Заполнение анкеты отменено.", reply_markup=main_menu_kb())

@router.message(F.text == "Подать анкету")
async def start_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Твой Nickname:", reply_markup=cancel_kb())
    await state.set_state(Form.nickname)

@router.message(Form.nickname)
async def form_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer("Твой Lvl:")
    await state.set_state(Form.lvl)

@router.message(Form.lvl)
async def form_lvl(message: Message, state: FSMContext):
    await state.update_data(lvl=message.text)
    await message.answer("Есть что-то по донату? (подробно):")
    await state.set_state(Form.donate)

@router.message(Form.donate)
async def form_donate(message: Message, state: FSMContext):
    await state.update_data(donate=message.text)
    await message.answer("Был ли ранее в кланах? Если да, то почему ушёл (если нет: -):")
    await state.set_state(Form.previous_clans)

@router.message(Form.previous_clans)
async def form_prev(message: Message, state: FSMContext):
    await state.update_data(previous_clans=message.text)
    await message.answer("Готов пройти проверку на стрельбу?:")
    await state.set_state(Form.shooting_test)

@router.message(Form.shooting_test)
async def form_shoot(message: Message, state: FSMContext):
    await state.update_data(shooting_test=message.text)
    await message.answer("Принимаешь ли правила клана?")
    await state.set_state(Form.rules_accept)

@router.message(Form.rules_accept)
async def form_rules(message: Message, state: FSMContext):
    await state.update_data(rules_accept=message.text)
    await message.answer("Часть 1 заполнена. Нажми «Далее» чтобы продолжить.", reply_markup=back_next_kb())

@router.callback_query(F.data == "next")
async def go_next(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("Имя:")
    await state.set_state(Form.real_name)
    await call.answer()

@router.callback_query(F.data == "back")
async def go_back(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("Хорошо, начнём заново.\n\nТвой Nickname:")
    await state.set_state(Form.nickname)
    await call.answer()

@router.message(Form.real_name)
async def form_name(message: Message, state: FSMContext):
    await state.update_data(real_name=message.text)
    await message.answer("Возраст:")
    await state.set_state(Form.age)

@router.message(Form.age)
async def form_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Стаж игры:")
    await state.set_state(Form.experience)

@router.message(Form.experience)
async def form_exp(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await message.answer("Почему именно к нам?")
    await state.set_state(Form.why_us)

@router.message(Form.why_us)
async def form_finish(message: Message, state: FSMContext):
    await state.update_data(why_us=message.text)
    data = await state.get_data()
    await state.clear()

    user = message.from_user
    username = f"@{user.username}" if user.username else f"(id: {user.id})"
    app_id = save_application(user.id, username, data)

    await message.answer("Анкета отправлена на проверку. Терпения 😘", reply_markup=main_menu_kb())

    try:
        await message.bot.send_message(ADMIN_ID, f"📨 Новая анкета #{app_id} от {username}\nЗайди в раздел «Анкеты» в боте.")
    except Exception as e:
        logging.warning(f"Не удалось уведомить админа: {e}")

@router.message(F.text == "Анкеты")
async def admin_section(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ только для администратора.")
        return
    await message.answer("Введите пароль:")
    await state.set_state(AdminAuth.waiting_password)

@router.message(AdminAuth.waiting_password)
async def check_password(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    if message.text.strip() != PASSWORD:
        await state.clear()
        await message.answer("❌ Неверный пароль.", reply_markup=main_menu_kb())
        return

    await state.clear()
    apps = get_all_pending()
    if not apps:
        await message.answer("📭 Новых анкет нет.", reply_markup=main_menu_kb())
        return

    await message.answer(f"🔓 Авторизация успешна. Анкет: {len(apps)}")
    for app in apps:
        await send_application_card(message.bot, message.chat.id, app)

async def send_application_card(bot: Bot, chat_id: int, app):
    (app_id, user_id, username, nickname, lvl, donate, prev_clans,
     shooting, rules, real_name, age, exp, why_us, status, created) = app

    text = (
        f"📋 <b>Анкета #{app_id}</b>\n"
        f"👤 {username} (id: <code>{user_id}</code>)\n"
        f"🕒 {created}\n\n"
        f"<b>Часть 1</b>\n"
        f"• Nickname: {nickname}\n"
        f"• Lvl: {lvl}\n"
        f"• Донат: {donate}\n"
        f"• Был в кланах: {prev_clans}\n"
        f"• Проверка стрельбы: {shooting}\n"
        f"• Правила: {rules}\n\n"
        f"<b>Часть 2</b>\n"
        f"• Имя: {real_name}\n"
        f"• Возраст: {age}\n"
        f"• Стаж: {exp}\n"
        f"• Почему к нам: {why_us}"
    )
    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=approve_reject_kb(app_id))

@router.callback_query(F.data.startswith("approve:"))
async def approve_app(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    app_id = int(call.data.split(":")[1])
    app = get_by_id(app_id)
    if not app:
        await call.answer("Анкета не найдена", show_alert=True)
        return

    set_status(app_id, "approved")
    try:
        await call.bot.send_message(app[1], "Вашу анкету одобрили. Ожидайте пока лидер вам отпишет в личку. С уважением клан NS 🫶")
    except Exception as e:
        logging.warning(f"Не смог написать {app[1]}: {e}")

    await call.message.edit_text(call.message.html_text + "\n\n✅ <b>ОДОБРЕНО</b>", parse_mode="HTML")
    await call.answer("Одобрено")

@router.callback_query(F.data.startswith("reject:"))
async def reject_app(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    app_id = int(call.data.split(":")[1])
    app = get_by_id(app_id)
    if not app:
        await call.answer("Анкета не найдена", show_alert=True)
        return

    set_status(app_id, "rejected")
    try:
        await call.bot.send_message(app[1], "К сожалению, вашу анкету отклонили. Спасибо за интерес к клану NS.")
    except Exception as e:
        logging.warning(f"Не смог написать {app[1]}: {e}")

    await call.message.edit_text(call.message.html_text + "\n\n❌ <b>ОТКЛОНЕНО</b>", parse_mode="HTML")
    await call.answer("Отклонено")


# ============ ЗАПУСК ВЕБ-СЕРВЕРА И БОТА ============
async def on_startup(bot: Bot):
    # Устанавливаем Webhook при запуске
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    # Удаляем Webhook при выключении
    await bot.delete_webhook()
    logging.info("Webhook удален")

async def handle_ping(request):
    # Этот ответ увидит UptimeRobot и поймет, что сервис жив
    return web.Response(text="Bot is alive!")

def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ Не задан BOT_TOKEN в Environment Variables")
    if ADMIN_ID == 0:
        raise SystemExit("❌ Не задан ADMIN_ID в Environment Variables")

    init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Настройка событий запуска/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаем веб-приложение aiohttp
    app = web.Application()

    # Регистрируем путь для Webhook от Telegram
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Регистрируем путь для пингов UptimeRobot (главная страница)
    app.router.add_get("/", handle_ping)

    # Связываем aiogram и aiohttp
    setup_application(app, dp, bot=bot)

    # Render автоматически передает порт в переменную PORT
    port = int(os.getenv("PORT", 8080))
    
    logging.info(f"Запуск веб-сервера на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()