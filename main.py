import html
import logging
import os

import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gambio_bot")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing required environment variable: TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

STORE_CHANNEL_URL = "https://t.me/Gambio_mk"
TERMS_URL = "https://telegra.ph/Usloviya-ispolzovaniya-i-vozvrata-05-19"
PRODUCT_VIDEO_FILE_ID = os.environ.get("PRODUCT_VIDEO_FILE_ID", "").strip()
PRODUCT_DESCRIPTION = [
    "Длинные автослайды в бок",
    "Длинные вперед",
    "Фаст вперед",
    "Зажим",
    "Орп",
    "+с",
    "Отводы",
]

# Keep the currently displayed bot message per chat so navigation can edit or
# remove it instead of leaving a stack of old menus in the conversation.
bot_messages_by_chat: dict[int, list[int]] = {}
current_page_by_chat: dict[int, str] = {}


def main_inline_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        ("🛍️Каталог", "catalog"),
        ("🏠 О магазине", "about"),
        ("👨‍💻 Условия использования", "terms"),
        ("👤 Профиль", "profile"),
    )


def inline_keyboard(*buttons: tuple[str, str]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for label, callback_data in buttons:
        keyboard.add(InlineKeyboardButton(label, callback_data=callback_data))
    return keyboard


def profile_text(user) -> str:
    user_name = html.escape(user.full_name or "Пользователь")
    user_id = user.id
    return (
        "👤 <b>Профиль</b>\n\n"
        f"🥷 Имя: {user_name}\n"
        f"🔑 ID: <code>{user_id}</code>\n"
        "💰 Ваш баланс: 0 руб."
    )


def page_content(page: str, user=None):
    if page == "home":
        return (
            "👋 Добро пожаловать в 𝐆𝐚𝐦𝐛𝐢𝐨 𝐒𝐡𝐨𝐩!\nВыберите нужный пункт в меню ниже 👇",
            main_inline_keyboard(),
            None,
        )

    if page == "catalog":
        page = "product_loka"

    if page == "product_loka":
        description = "\n".join(f"• {item}" for item in PRODUCT_DESCRIPTION)
        return (
            "🛍️ <b>Лока сборка</b>\n\n"
            "Создатель: Gambio\n\n"
            f"Описание:\n{description}\n\n"
            "💰 Цена: 100₽ // 150⭐️",
            inline_keyboard(("🔙 Назад", "back:home")),
            "HTML",
        )

    if page == "about":
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("📢 Посмотреть канал", url=STORE_CHANNEL_URL))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back:home"))
        return (
            "🏠 Магазин: 𝐆𝐚𝐦𝐛𝐢𝐨 𝐒𝐡𝐨𝐩\n"
            "⏰ Дата создания: 2026-10-27\n"
            "📢 Нажмите кнопку ниже, чтобы перейти в канал.",
            keyboard,
            None,
        )

    if page == "terms":
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("Открыть условия", url=TERMS_URL))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back:home"))
        return (
            "Нажмите кнопку ниже, чтобы ознакомиться с условиями использования и возврата:",
            keyboard,
            None,
        )

    if page == "profile":
        return (
            profile_text(user),
            inline_keyboard(
                ("🛒 История заказов", "history_orders"),
                ("💸 История пополнения", "history_topups"),
                ("💰 Пополнить баланс", "topup_balance"),
                ("🔙 Назад", "back:home"),
            ),
            "HTML",
        )

    if page == "history_orders":
        return (
            "🛒 <b>История заказов</b>\nВсего у Вас заказов: 0\n\nУ Вас пока нет заказов.",
            inline_keyboard(("🔙 Назад", "back:profile")),
            "HTML",
        )

    if page == "history_topups":
        return (
            "💸 <b>История пополнения</b>\nВсего у Вас пополнений: 0",
            inline_keyboard(("🔙 Назад", "back:profile")),
            "HTML",
        )

    if page == "topup_balance":
        return (
            "💰 Пополнить баланс\n\nДанный раздел пока не доступен.",
            inline_keyboard(("🔙 Назад", "back:profile")),
            None,
        )

    raise ValueError(f"Unknown page: {page}")


def remember_bot_message(chat_id: int, message_id: int) -> None:
    messages = bot_messages_by_chat.setdefault(chat_id, [])
    if message_id not in messages:
        messages.append(message_id)
    current_page_by_chat.setdefault(chat_id, "home")


def cleanup_bot_messages(chat_id: int, keep_message_id: int | None = None) -> None:
    old_ids = bot_messages_by_chat.get(chat_id, [])
    remaining = []
    for message_id in old_ids:
        if message_id == keep_message_id:
            remaining.append(message_id)
            continue
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            logger.info("Could not remove an earlier bot message; continuing.")
    if keep_message_id is not None and keep_message_id not in remaining:
        remaining.append(keep_message_id)
    if remaining:
        bot_messages_by_chat[chat_id] = remaining
    else:
        bot_messages_by_chat.pop(chat_id, None)


def send_page(chat_id: int, page: str, user=None, remove_reply_keyboard: bool = False):
    if page == "catalog":
        page = "product_loka"
    if page == "home":
        remove_reply_keyboard = True
    cleanup_bot_messages(chat_id)
    text, keyboard, parse_mode = page_content(page, user)
    removal_message = None

    if remove_reply_keyboard:
        removal_message = bot.send_message(
            chat_id,
            "Открываю раздел…",
            reply_markup=ReplyKeyboardRemove(),
        )

    if page == "product_loka" and PRODUCT_VIDEO_FILE_ID:
        sent = bot.send_video(
            chat_id,
            PRODUCT_VIDEO_FILE_ID,
            caption=text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
        )
    else:
        sent = bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard,
            parse_mode=parse_mode,
        )
    remember_bot_message(chat_id, sent.message_id)
    current_page_by_chat[chat_id] = page

    if removal_message is not None:
        try:
            bot.delete_message(chat_id, removal_message.message_id)
        except Exception:
            logger.info("Could not remove the temporary keyboard update message.")
            remember_bot_message(chat_id, removal_message.message_id)

    return sent


def edit_page(chat_id: int, message_id: int, page: str, user=None):
    if page == "catalog":
        page = "product_loka"
    if page == "home":
        remember_bot_message(chat_id, message_id)
        return send_page(chat_id, "home", user)

    if PRODUCT_VIDEO_FILE_ID and page == "product_loka":
        remember_bot_message(chat_id, message_id)
        cleanup_bot_messages(chat_id)
        return send_page(chat_id, page, user)

    if PRODUCT_VIDEO_FILE_ID and current_page_by_chat.get(chat_id) == "product_loka":
        remember_bot_message(chat_id, message_id)
        cleanup_bot_messages(chat_id)
        return send_page(chat_id, page, user)

    text, keyboard, parse_mode = page_content(page, user)
    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=keyboard,
            parse_mode=parse_mode,
        )
    except Exception as error:
        if "message is not modified" not in str(error).lower():
            logger.warning("Could not edit a bot page; replacing it.")
            remember_bot_message(chat_id, message_id)
            return send_page(chat_id, page, user, remove_reply_keyboard=True)

    cleanup_bot_messages(chat_id, keep_message_id=message_id)
    current_page_by_chat[chat_id] = page
    return message_id


def page_before(page: str) -> str:
    return {
        "catalog": "home",
        "product_loka": "home",
        "about": "home",
        "terms": "home",
        "profile": "home",
        "history_orders": "profile",
        "history_topups": "profile",
        "topup_balance": "profile",
    }.get(page, "home")


@bot.message_handler(commands=["start"])
def cmd_start(message):
    send_page(message.chat.id, "home", message.from_user)


@bot.message_handler(commands=["back"])
def cmd_back(message):
    chat_id = message.chat.id
    current_page = current_page_by_chat.get(chat_id, "home")
    target_page = page_before(current_page)
    message_id = bot_messages_by_chat.get(chat_id, [])
    last_message_id = message_id[-1] if message_id else None

    if target_page == "home" or last_message_id is None:
        send_page(
            chat_id,
            target_page,
            message.from_user,
            remove_reply_keyboard=target_page != "home",
        )
    else:
        edit_page(chat_id, last_message_id, target_page, message.from_user)


@bot.message_handler(content_types=["video"])
def handle_video_upload(message):
    if message.chat.type != "private" or not message.video:
        return

    file_id = html.escape(message.video.file_id)
    bot.reply_to(
        message,
        "Добавьте в Render переменную <code>PRODUCT_VIDEO_FILE_ID</code> "
        "со значением ниже, затем перезапустите Background Worker:\n\n"
        f"<code>{file_id}</code>",
        parse_mode="HTML",
    )


@bot.message_handler(content_types=["text"])
def handle_text(message):
    pages = {
        "🛍️Каталог": "product_loka",
        "🏠 О магазине": "about",
        "👨‍💻 Условия использования": "terms",
        "👤 Профиль": "profile",
    }
    page = pages.get(message.text or "")
    if page is not None:
        send_page(message.chat.id, page, message.from_user, remove_reply_keyboard=True)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        pages = {
            "catalog": "product_loka",
            "product:loka": "product_loka",
            "about": "about",
            "terms": "terms",
            "profile": "profile",
            "history_orders": "history_orders",
            "history_topups": "history_topups",
            "topup_balance": "topup_balance",
            "back_to_profile": "profile",
        }

        if call.data == "back:catalog":
            page = "home"
        elif call.data.startswith("back:"):
            page = call.data.split(":", 1)[1]
        else:
            page = pages.get(call.data)

        allowed_pages = {
            "home",
            "catalog",
            "product_loka",
            "about",
            "terms",
            "profile",
            "history_orders",
            "history_topups",
            "topup_balance",
        }
        if page not in allowed_pages:
            try:
                bot.answer_callback_query(call.id, "Кнопка устарела. Нажмите /start.", show_alert=True)
            except Exception:
                logger.info("Could not acknowledge an expired bot button.")
            return

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            logger.info("Could not acknowledge a bot button; continuing.")

        edit_page(
            call.message.chat.id,
            call.message.message_id,
            page,
            call.from_user,
        )
    except Exception:
        logger.exception("Failed to handle a bot button.")


if __name__ == "__main__":
    logger.info("Bot started.")
    bot.infinity_polling()
