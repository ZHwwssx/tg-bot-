"""Group @all mentions for the existing Telegram bot.

Telegram does not provide bots with an API to enumerate every chat member. This
module stores people seen in group messages or join service messages and tags
that known set when someone writes @all.
"""

import json
import logging
import os
import re
import threading
from pathlib import Path

from telebot import types

logger = logging.getLogger(__name__)

_STORE_PATH = Path(
    os.environ.get(
        "ALL_MENTIONS_STORE",
        str(Path(__file__).resolve().parent / "group_members.json"),
    )
)
_MAX_MESSAGE_UNITS = 3500
_ALL_PATTERN = re.compile(r"(?<![\w@])@all(?!\w)", re.IGNORECASE)
_LOCK = threading.RLock()
_MEMBERS = {}


def _load_members():
    try:
        with _STORE_PATH.open("r", encoding="utf-8") as store_file:
            saved = json.load(store_file)
        if isinstance(saved, dict):
            for chat_id, users in saved.items():
                if isinstance(users, dict):
                    _MEMBERS[str(chat_id)] = {
                        str(user_id): user
                        for user_id, user in users.items()
                        if isinstance(user, dict) and user.get("id")
                    }
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        logger.exception("Could not load the @all member cache")


def _save_members():
    temporary_path = _STORE_PATH.with_name(_STORE_PATH.name + ".tmp")
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as store_file:
            json.dump(_MEMBERS, store_file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_path, _STORE_PATH)
    except OSError:
        logger.exception("Could not save the @all member cache")
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove a temporary @all member cache")


def _user_record(user):
    user_id = getattr(user, "id", None)
    if not user_id or getattr(user, "is_bot", True):
        return None
    first_name = (getattr(user, "first_name", None) or "").strip()
    if not first_name:
        first_name = "Участник"
    return {
        "id": int(user_id),
        "is_bot": False,
        "first_name": first_name,
        "last_name": getattr(user, "last_name", None),
        "username": getattr(user, "username", None),
    }


def _remember(chat_id, user):
    record = _user_record(user)
    if record is None:
        return False
    chat_key = str(chat_id)
    user_key = str(record["id"])
    chat_members = _MEMBERS.setdefault(chat_key, {})
    if chat_members.get(user_key) == record:
        return False
    chat_members[user_key] = record
    return True


def _forget(chat_id, user):
    user_id = getattr(user, "id", None)
    if not user_id:
        return False
    chat_members = _MEMBERS.get(str(chat_id), {})
    removed = chat_members.pop(str(user_id), None) is not None
    if not chat_members:
        _MEMBERS.pop(str(chat_id), None)
    return removed


def _utf16_units(value):
    return len(value.encode("utf-16-le")) // 2


def _display_name(user):
    username = user.get("username")
    if username:
        return "@" + username
    name = " ".join(part for part in (user.get("first_name"), user.get("last_name")) if part)
    return name or "Участник"


def _build_mention_chunks(users):
    prefix = "📣 @All\n"
    prefix_units = _utf16_units(prefix)
    chunks = []
    text = prefix
    entities = []
    current_units = prefix_units

    for user_data in users:
        label = _display_name(user_data)
        line = label + "\n"
        label_units = _utf16_units(label)
        line_units = _utf16_units(line)

        if entities and current_units + line_units > _MAX_MESSAGE_UNITS:
            chunks.append((text, entities))
            text = prefix
            entities = []
            current_units = prefix_units

        user = types.User.de_json(user_data)
        entities.append(
            types.MessageEntity(
                type="text_mention",
                offset=current_units,
                length=label_units,
                user=user,
            )
        )
        text += line
        current_units += line_units

    if entities:
        chunks.append((text, entities))
    return chunks


def _handle_group_message(bot, message):
    chat = getattr(message, "chat", None)
    if not chat or getattr(chat, "type", None) not in ("group", "supergroup"):
        return

    changed = False
    with _LOCK:
        sender = getattr(message, "from_user", None)
        if sender is not None:
            changed = _remember(chat.id, sender) or changed

        for new_member in getattr(message, "new_chat_members", None) or []:
            changed = _remember(chat.id, new_member) or changed

        left_member = getattr(message, "left_chat_member", None)
        if left_member is not None:
            changed = _forget(chat.id, left_member) or changed

        if changed:
            _save_members()

        message_text = getattr(message, "text", None) or ""
        if not _ALL_PATTERN.search(message_text):
            return
        users = sorted(
            _MEMBERS.get(str(chat.id), {}).values(),
            key=lambda user: (_display_name(user).casefold(), int(user["id"])),
        )

    if not users:
        bot.send_message(
            chat.id,
            "Пока некого отметить: я ещё не видел участников этой группы.",
            parse_mode="",
            reply_to_message_id=message.message_id,
        )
        return

    for index, (text, entities) in enumerate(_build_mention_chunks(users)):
        bot.send_message(
            chat.id,
            text,
            entities=entities,
            parse_mode="",
            reply_to_message_id=message.message_id if index == 0 else None,
        )


def register_group_mentions(bot):
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
        keyboard.add(
            types.InlineKeyboardButton("📖 Открыть меню бота", callback_data="menu:home")
        )
        bot.send_message(
            message.chat.id,
            "Привет! Добавь меня в группу и напиши там @all — я отмечу участников, которых уже видел.\n\n"
            "Чтобы я видел обычные сообщения, отключи Privacy Mode у @BotFather через /setprivacy → Disable, "
            "затем заново добавь меня в группу. Также можно выдать мне права администратора.\n\n"
            "Telegram не показывает ботам полный список участников: я смогу отметить только тех, "
            "кто напишет в группе или вступит после добавления бота.",
            reply_markup=keyboard,
            parse_mode=None,
        )

    bot.message_handler(content_types=["text", "new_chat_members", "left_chat_member"])(
        lambda message: _handle_group_message(bot, message)
    )


_load_members()
