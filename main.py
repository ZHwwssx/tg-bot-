import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import telebot
from flask import Flask, request
from telebot import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN")
    or os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("BOT_TOKEN")
)
if not TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN in the Render environment variables.")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# A new cache filename ensures this clean bot starts with no earlier member list.
# Set ALL_MENTIONS_CACHE_FILE to a persistent-disk path to keep it across deploys.
MEMBERS_FILE = Path(
    os.environ.get("ALL_MENTIONS_CACHE_FILE", "/tmp/all_bot_members.json")
)
MAX_MESSAGE_UNITS = 3500
ALL_PATTERN = re.compile(r"(?<![\w@])@all(?!\w)", re.IGNORECASE)
MEMBERS_LOCK = threading.RLock()
MEMBERS = {}


def load_members():
    try:
        with MEMBERS_FILE.open("r", encoding="utf-8") as cache_file:
            saved = json.load(cache_file)
        if isinstance(saved, dict):
            for chat_id, users in saved.items():
                if isinstance(users, dict):
                    MEMBERS[str(chat_id)] = {
                        str(user_id): user
                        for user_id, user in users.items()
                        if isinstance(user, dict) and user.get("id")
                    }
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        logger.exception("Could not load the group member cache; starting empty")


def save_members():
    temporary_file = MEMBERS_FILE.with_name(MEMBERS_FILE.name + ".tmp")
    try:
        MEMBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with temporary_file.open("w", encoding="utf-8") as cache_file:
            json.dump(MEMBERS, cache_file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_file, MEMBERS_FILE)
    except OSError:
        logger.exception("Could not save the group member cache")
        try:
            temporary_file.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove the temporary group member cache")


def user_record(user):
    user_id = getattr(user, "id", None)
    if not user_id or getattr(user, "is_bot", True):
        return None
    first_name = " ".join((getattr(user, "first_name", None) or "").split())
    if not first_name:
        first_name = "Участник"
    return {
        "id": int(user_id),
        "is_bot": False,
        "first_name": first_name,
        "last_name": getattr(user, "last_name", None),
        "username": getattr(user, "username", None),
    }


def remember_user(chat_id, user):
    record = user_record(user)
    if record is None:
        return False
    chat_members = MEMBERS.setdefault(str(chat_id), {})
    key = str(record["id"])
    if chat_members.get(key) == record:
        return False
    chat_members[key] = record
    return True


def forget_user(chat_id, user):
    user_id = getattr(user, "id", None)
    if not user_id:
        return False
    chat_members = MEMBERS.get(str(chat_id), {})
    removed = chat_members.pop(str(user_id), None) is not None
    if not chat_members:
        MEMBERS.pop(str(chat_id), None)
    return removed


def utf16_units(value):
    return len(value.encode("utf-16-le")) // 2


def display_name(user):
    username = user.get("username")
    if username:
        return "@" + username
    name = " ".join(
        part for part in (user.get("first_name"), user.get("last_name")) if part
    )
    return " ".join(name.split()) or "Участник"


def build_mention_chunks(users):
    prefix = "📣 @All\n"
    prefix_units = utf16_units(prefix)
    chunks = []
    text = prefix
    entities = []
    current_units = prefix_units

    for user_data in users:
        label = display_name(user_data)
        line = label + "\n"
        label_units = utf16_units(label)
        line_units = utf16_units(line)
        if entities and current_units + line_units > MAX_MESSAGE_UNITS:
            chunks.append((text, entities))
            text = prefix
            entities = []
            current_units = prefix_units

        entities.append(
            types.MessageEntity(
                type="text_mention",
                offset=current_units,
                length=label_units,
                user=types.User.de_json(user_data),
            )
        )
        text += line
        current_units += line_units

    if entities:
        chunks.append((text, entities))
    return chunks


def handle_group_message(message):
    chat = getattr(message, "chat", None)
    if not chat or getattr(chat, "type", None) not in ("group", "supergroup"):
        return

    changed = False
    with MEMBERS_LOCK:
        sender = getattr(message, "from_user", None)
        if sender is not None:
            changed = remember_user(chat.id, sender) or changed

        for new_member in getattr(message, "new_chat_members", None) or []:
            changed = remember_user(chat.id, new_member) or changed

        left_member = getattr(message, "left_chat_member", None)
        if left_member is not None:
            changed = forget_user(chat.id, left_member) or changed

        if changed:
            save_members()

        text = getattr(message, "text", None) or ""
        if not ALL_PATTERN.search(text):
            return
        users = sorted(
            MEMBERS.get(str(chat.id), {}).values(),
            key=lambda user: (display_name(user).casefold(), int(user["id"])),
        )

    if not users:
        bot.send_message(
            chat.id,
            "Пока некого отметить: я ещё не видел участников этой группы.",
            parse_mode="",
            reply_to_message_id=message.message_id,
        )
        return

    try:
        for index, (chunk_text, entities) in enumerate(build_mention_chunks(users)):
            bot.send_message(
                chat.id,
                chunk_text,
                entities=entities,
                parse_mode="",
                reply_to_message_id=message.message_id if index == 0 else None,
            )
    except Exception:
        logger.exception("Could not send all @all mentions")


@bot.message_handler(commands=["start"])
def start_message(message):
    if getattr(getattr(message, "chat", None), "type", None) != "private":
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    username = getattr(bot.get_me(), "username", None)
    if username:
        keyboard.add(
            types.InlineKeyboardButton(
                "➕ Добавить в группу",
                url="https://t.me/" + username + "?startgroup=add",
            )
        )
    bot.send_message(
        message.chat.id,
        "Привет! Добавь меня в группу и напиши там @all — я отмечу участников, которых уже видел.\n\n"
        "Чтобы я видел обычные сообщения, отключи Privacy Mode у @BotFather через /setprivacy → Disable, "
        "затем заново добавь меня в группу. Также можно выдать мне права администратора.\n\n"
        "Telegram не показывает ботам полный список участников: я смогу отметить только тех, "
        "кто напишет в группе или вступит после добавления бота.",
        reply_markup=keyboard,
        parse_mode="",
    )


@bot.message_handler(content_types=["text", "new_chat_members", "left_chat_member"])
def group_message_handler(message):
    handle_group_message(message)


def configure_bot_commands():
    bot.set_my_commands([types.BotCommand("start", "Добавить бота в группу")])


@app.get("/")
def health_check():
    return "@all bot is alive"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200
    except Exception:
        logger.exception("Telegram webhook update failed")
        return "Webhook error", 500


def run_web_server():
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


load_members()

if __name__ == "__main__":
    try:
        bot_info = bot.get_me()
        logger.info("Telegram authentication successful: @%s", bot_info.username)
    except Exception:
        logger.exception("Telegram authentication failed. Check TELEGRAM_BOT_TOKEN in Render.")
        raise

    configure_bot_commands()
    webhook_base_url = os.environ.get("TELEGRAM_WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if webhook_base_url:
        webhook_url = webhook_base_url.rstrip("/") + "/telegram-webhook"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url, allowed_updates=["message"])
        logger.info("Bot is starting in webhook mode")
        run_web_server()
    else:
        bot.remove_webhook()
        time.sleep(1)
        threading.Thread(target=run_web_server, daemon=True).start()
        logger.info("Bot is starting in polling mode")
        while True:
            try:
                bot.infinity_polling(skip_pending=True, allowed_updates=["message"])
            except Exception:
                logger.exception("Polling failed; retrying in 5 seconds")
                time.sleep(5)
