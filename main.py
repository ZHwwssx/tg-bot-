import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

TOKEN = "9158246587:AAEJM7FKR1AcL18K00FyT-qbTu-KppcDpNs"
bot = telebot.TeleBot(TOKEN)

# 1. Главная постоянная клавиатура (снизу)
main_reply_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_reply_keyboard.row(KeyboardButton("🏠 О магазине"))
main_reply_keyboard.row(KeyboardButton("👨‍💻 Условия использования"))
main_reply_keyboard.row(KeyboardButton("👤 Профиль"))


# Команда /start
@bot.message_handler(commands=["start"])
def cmd_start(message):
  bot.send_message(
      message.chat.id,
      "👋 Добро пожаловать в 𝐆𝐚𝐦𝐛𝐢𝐨 𝐒𝐡𝐨𝐩!\nВыберите нужный пункт в меню ниже 👇",
      reply_markup=main_reply_keyboard,
  )


# Обработка текстовых кнопок снизу
@bot.message_handler(content_types=["text"])
def handle_text(message):
  if message.text == "🏠 О магазине":
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📢 Посмотреть канал", url="https://t.me/Gambio_mk")
    )
    text = (
        "🏠 Магазин: 𝐆𝐚𝐦𝐛𝐢𝐨 𝐒𝐡𝐨𝐩\n"
        "⏰ Дата создания: 2026-10-27\n"
        "📢 Канал: Нажмите кнопку ниже, чтобы перейти в канал."
    )
    bot.send_message(
        message.chat.id, text, reply_markup=keyboard, parse_mode="HTML"
    )

  elif message.text == "👨‍💻 Условия использования":
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            "Жми", url="https://telegra.ph/Usloviya-ispolzovaniya-i-vozvrata-05-19"
        )
    )
    bot.send_message(
        message.chat.id,
        "Нажмите на кнопку ниже, чтобы ознакомиться с условиями использования и"
        " возврата:",
        reply_markup=keyboard,
    )

  elif message.text == "👤 Профиль":
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    user_balance = 0

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🛒 История заказов", callback_data="history_orders"),
        InlineKeyboardButton(
            "💸 История пополнения", callback_data="history_topups"
        ),
        InlineKeyboardButton("💰 Пополнить баланс", callback_data="topup_balance"),
    )

    text = (
        f"👤 Профиль\n\n"
        f"🥷 Имя: {user_name}\n"
        f"🔑 ID: <code>{user_id}</code>\n"
        f"💰 Ваш баланс: {user_balance} руб."
    )
    bot.send_message(
        message.chat.id, text, reply_markup=keyboard, parse_mode="HTML"
    )


# Обработка инлайн-кнопок в профиле
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  chat_id = call.message.chat.id
  message_id = call.message.message_id

  back_kb = InlineKeyboardMarkup()
  back_kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile"))

  if call.data == "history_orders":
    total_orders = 0
    orders_text = "➖➖➖➖➖➖➖➖➖➖➖➖\nУ Вас пока нет заказов."
    text = (
        f"🛒 История заказов\nВсего у Вас Заказов:"
        f" {total_orders}\n{orders_text}"
    )
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=back_kb,
        parse_mode="HTML",
    )

  elif call.data == "history_topups":
    total_topups = 0
    text = f"💸 История пополнения\nВсего у Вас пополнений: {total_topups}"
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=back_kb,
        parse_mode="HTML",
    )

  elif call.data == "topup_balance":
    text = "💰 Пополнить баланс\n\nДанный раздел пока не доступен. Терпения 😘"
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=back_kb,
        parse_mode="HTML",
    )

  elif call.data == "back_to_profile":
    user_name = call.from_user.full_name
    user_id = call.from_user.id
    user_balance = 0

    profile_kb = InlineKeyboardMarkup(row_width=1)
    profile_kb.add(
        InlineKeyboardButton("🛒 История заказов", callback_data="history_orders"),
        InlineKeyboardButton(
            "💸 История пополнения", callback_data="history_topups"
        ),
        InlineKeyboardButton("💰 Пополнить баланс", callback_data="topup_balance"),
    )

    text = (
        f"👤 Профиль\n\n"
        f"🥷 Имя: {user_name}\n"
        f"🔑 ID: <code>{user_id}</code>\n"
        f"💰 Ваш баланс: {user_balance} руб."
    )
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=profile_kb,
        parse_mode="HTML",
    )

  bot.answer_callback_query(call.id)


# Запуск бота
print("Бот запущен!")
bot.infinity_polling()