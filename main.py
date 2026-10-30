import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==== НАСТРОЙКИ ====
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
ADMIN_PASSWORD = "7374"
ANKETY_FILE = "ankety.json"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==== СОСТОЯНИЯ ====
class Anketa(StatesGroup):
    nick = State()
    name = State()
    age = State()
    lvl = State()
    time_in_game = State()
    donate = State()
    microphone = State()
    why_us = State()
    what_do = State()
    qualities = State()
    pvp = State()
    other_clans = State()


class AdminCheck(StatesGroup):
    password = State()


# ==== КЛАВИАТУРЫ ====
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Заполнить анкету")],
        [KeyboardButton(text="📂 Анкеты")],
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)


# ==== ХРАНИЛИЩЕ ====
def load_ankety():
    if os.path.exists(ANKETY_FILE):
        with open(ANKETY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_anketa(data: dict):
    ankety = load_ankety()
    ankety.append(data)
    with open(ANKETY_FILE, "w", encoding="utf-8") as f:
        json.dump(ankety, f, ensure_ascii=False, indent=2)


# ==== СТАРТ ====
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в <b>NaSofte</b>!\n\n"
        "Нажми кнопку ниже, чтобы заполнить анкету.",
        parse_mode="HTML",
        reply_markup=main_kb
    )


# ==== ЗАПОЛНЕНИЕ АНКЕТЫ ====
@dp.message(F.text == "📝 Заполнить анкету")
async def start_anketa(message: Message, state: FSMContext):
    await state.set_state(Anketa.nick)
    await message.answer(
        "📋 <b>Анкета в клан NaSofte</b>\n\n"
        "• <b>Ник в игре:</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )


@dp.message(Anketa.nick)
async def a_nick(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(nick=message.text)
    await state.set_state(Anketa.name)
    await message.answer("• <b>Как зовут?</b>", parse_mode="HTML")


@dp.message(Anketa.name)
async def a_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Anketa.age)
    await message.answer("• <b>Сколько лет?</b>", parse_mode="HTML")


@dp.message(Anketa.age)
async def a_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(Anketa.lvl)
    await message.answer("• <b>LVL:</b>", parse_mode="HTML")


@dp.message(Anketa.lvl)
async def a_lvl(message: Message, state: FSMContext):
    await state.update_data(lvl=message.text)
    await state.set_state(Anketa.time_in_game)
    await message.answer(
        "• <b>Сколько времени уделяешь игре?</b>",
        parse_mode="HTML"
    )


@dp.message(Anketa.time_in_game)
async def a_time(message: Message, state: FSMContext):
    await state.update_data(time_in_game=message.text)
    await state.set_state(Anketa.donate)
    await message.answer(
        "• <b>Есть что-то по донату?</b> (если да, то что?)",
        parse_mode="HTML"
    )


@dp.message(Anketa.donate)
async def a_donate(message: Message, state: FSMContext):
    await state.update_data(donate=message.text)
    await state.set_state(Anketa.microphone)
    await message.answer(
        "• <b>Пользуешься микрофоном в игре?</b>",
        parse_mode="HTML"
    )


@dp.message(Anketa.microphone)
async def a_mic(message: Message, state: FSMContext):
    await state.update_data(microphone=message.text)
    await state.set_state(Anketa.why_us)
    await message.answer(
        "• <b>Почему именно к нам?</b>",
        parse_mode="HTML"
    )


@dp.message(Anketa.why_us)
async def a_why(message: Message, state: FSMContext):
    await state.update_data(why_us=message.text)
    await state.set_state(Anketa.what_do)
    await message.answer(
        "• <b>Чем в основном занимаешься в игре?</b> (подробно)",
        parse_mode="HTML"
    )


@dp.message(Anketa.what_do)
async def a_what(message: Message, state: FSMContext):
    await state.update_data(what_do=message.text)
    await state.set_state(Anketa.qualities)
    await message.answer(
        "• <b>Расскажи о своих качествах игры:</b>",
        parse_mode="HTML"
    )


@dp.message(Anketa.qualities)
async def a_qualities(message: Message, state: FSMContext):
    await state.update_data(qualities=message.text)
    await state.set_state(Anketa.pvp)
    await message.answer(
        "• <b>Готов ли пройти отбор по ПВП?</b>",
        parse_mode="HTML"
    )


@dp.message(Anketa.pvp)
async def a_pvp(message: Message, state: FSMContext):
    await state.update_data(pvp=message.text)
    await state.set_state(Anketa.other_clans)
    await message.answer(
        "• <b>Был в других кланах?</b> Если да — почему теперь один?",
        parse_mode="HTML"
    )


@dp.message(Anketa.other_clans)
async def a_other(message: Message, state: FSMContext):
    await state.update_data(other_clans=message.text)
    data = await state.get_data()

    # юзернейм и ID отправителя
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    user_id = message.from_user.id

    # сохраняем анкету
    record = {
        "user_id": user_id,
        "username": username,
        **data
    }
    save_anketa(record)

    # показываем пользователю итог
    text = (
        "✅ <b>Анкета отправлена!</b>\n\n"
        f"👤 Отправитель: {username}\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"🎮 Ник: {data['nick']}\n"
        f"🙋 Имя: {data['name']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"⭐ LVL: {data['lvl']}\n"
        f"⏱ Время в игре: {data['time_in_game']}\n"
        f"💰 Донат: {data['donate']}\n"
        f"🎤 Микрофон: {data['microphone']}\n"
        f"❓ Почему к нам: {data['why_us']}\n"
        f"🎯 Чем занимается: {data['what_do']}\n"
        f"💪 Качества: {data['qualities']}\n"
        f"⚔️ Готов к ПВП-отбору: {data['pvp']}\n"
        f"🏰 Другие кланы: {data['other_clans']}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_kb)
    await state.clear()


# ==== ПРОСМОТР АНКЕТ (С ПАРОЛЕМ) ====
@dp.message(F.text == "📂 Анкеты")
async def ask_password(message: Message, state: FSMContext):
    await state.set_state(AdminCheck.password)
    await message.answer(
        "🔒 Введите пароль для просмотра анкет:",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(AdminCheck.password)
async def check_password(message: Message, state: FSMContext):
    if message.text != ADMIN_PASSWORD:
        await message.answer(
            "❌ Неверный пароль.",
            reply_markup=main_kb
        )
        await state.clear()
        return

    ankety = load_ankety()
    await state.clear()

    if not ankety:
        await message.answer("📭 Анкет пока нет.", reply_markup=main_kb)
        return

    await message.answer(
        f"📂 <b>Всего анкет: {len(ankety)}</b>",
        parse_mode="HTML",
        reply_markup=main_kb
    )

    for i, a in enumerate(ankety, start=1):
        text = (
            f"<b>Анкета #{i}</b>\n"
            f"👤 Отправитель: {a.get('username', 'нет')}\n"
            f"🆔 ID: <code>{a.get('user_id', '?')}</code>\n\n"
            f"🎮 Ник: {a.get('nick', '-')}\n"
            f"🙋 Имя: {a.get('name', '-')}\n"
            f"🎂 Возраст: {a.get('age', '-')}\n"
            f"⭐ LVL: {a.get('lvl', '-')}\n"
            f"⏱ Время в игре: {a.get('time_in_game', '-')}\n"
            f"💰 Донат: {a.get('donate', '-')}\n"
            f"🎤 Микрофон: {a.get('microphone', '-')}\n"
            f"❓ Почему к нам: {a.get('why_us', '-')}\n"
            f"🎯 Чем занимается: {a.get('what_do', '-')}\n"
            f"💪 Качества: {a.get('qualities', '-')}\n"
            f"⚔️ ПВП-отбор: {a.get('pvp', '-')}\n"
            f"🏰 Другие кланы: {a.get('other_clans', '-')}"
        )
        await message.answer(text, parse_mode="HTML")


# ==== ЗАПУСК ====
async def main():
    print("Бот NaSofte запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())