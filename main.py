import logging
import os
import threading
from html import escape as html_escape

import telebot
from flask import Flask, request
from telebot import types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Flask нужен для Render, внешнего сигнала и Telegram webhook.
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is alive and running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200
    except Exception:
        logger.exception("Ошибка обработки Telegram webhook")
        return "Webhook error", 500


def run_flask():
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


TOKEN = os.environ["BOT_TOKEN"]
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


def read_optional_int(name):
    value = os.environ.get(name, "").strip()
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        logger.warning("Некорректное значение %s", name)
        return 0


APPLICATION_GROUP_ID = read_optional_int("APPLICATION_GROUP_ID")
LEADER_ID = read_optional_int("LEADER_ID")
DEPUTY_ID = read_optional_int("DEPUTY_ID")

APPLICATION_QUESTIONS = [
    ("Твой NickName", "Напиши свой NickName.", "text"),
    ("Твой LvL", "Напиши свой игровой уровень.", "text"),
    ("Твое Имя", "Как тебя зовут?", "text"),
    ("Твой возраст", "Сколько тебе лет?", "text"),
    ("Есть ли дискорд", "Напиши свой Discord или ответь «нет».", "text"),
    ("Имеется ли донат?", "Если да, напиши какой. Если нет — напиши «нет».", "text"),
    ("Ежедневный онлайн", "Сколько времени ты обычно проводишь в игре ежедневно?", "text"),
    ("Стаж игры", "Как давно ты играешь?", "text"),
    ("Запиши голосовое сообщение", "Например, скажи своё имя и NickName.", "voice"),
]

WELCOME_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "sk_welcome.jpg")
WELCOME_TEXT = (
    "<b>SK CLAN</b>\n\n"
    "Приветствую тебя в анкете на вступление в клан <b>SK</b>.\n\n"
    "Заполни все пункты честно и не забудь отправить голосовое сообщение.\n\n"
    "<i>Удачи на отборе!</i>"
)
FINAL_TEXT = (
    "<b>Анкета завершена</b>\n\n"
    "Твоя анкета передана Лидеру и Со-лидеру клана <b>SK</b>.\n"
    "Ожидай ответа.\n\n"
    "✅"
)
VOICE_WARNING = (
    "<b>Важно:</b> Голосовое сообщение нужно для подтверждения возраста, "
    "а также чтобы заметить тебя при повторном входе в клан с другого аккаунта."
)


# Состояние хранится в памяти процесса.
data_lock = threading.Lock()
application_states = {}
application_by_message = {}
pending_replies = {}
conversation_requests = {}
conversation_sessions = {}
conversation_group_messages = {}
CONVERSATION_CONTENT_TYPES = [
    "text", "voice", "photo", "video", "document", "audio",
    "sticker", "animation", "contact", "location", "venue", "poll", "dice",
]


def clean_text(value):
    return html_escape(str(value), quote=False)


def style_text(text):
    text = str(text)
    if text.startswith("<b>SK</b>") or text.startswith("<b>SK CLAN</b>"):
        return text
    return f"<b>SK</b>\n\n{text}"


def safe_send(chat_id, text, **kwargs):
    try:
        kwargs.setdefault("parse_mode", "HTML")
        kwargs.setdefault("disable_web_page_preview", True)
        return bot.send_message(chat_id, style_text(text), **kwargs)
    except Exception:
        logger.exception("Ошибка отправки сообщения в чат %s", chat_id)
        return None


def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        logger.debug("Не удалось удалить сообщение %s в чате %s", message_id, chat_id)


def conversation_request_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Принять", callback_data=f"conversation_accept:{user_id}"),
        InlineKeyboardButton("Отклонить", callback_data=f"conversation_decline:{user_id}"),
    )
    return keyboard


def conversation_user_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Закончить беседу", callback_data="conversation_end_user"))
    return keyboard


def conversation_group_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Закончить беседу", callback_data=f"conversation_end_group:{user_id}"))
    return keyboard


def remove_inline_keyboard(chat_id, message_id):
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
    except Exception:
        logger.debug("Не удалось убрать кнопки сообщения %s", message_id)


def start_conversation_request(chat_id, user):
    if not is_configured():
        safe_send(chat_id, "Беседа пока недоступна: не указана APPLICATION_GROUP_ID.", reply_markup=back_keyboard())
        return

    user_id = user.id
    with data_lock:
        if user_id in conversation_sessions:
            safe_send(chat_id, "У тебя уже есть активная беседа.", reply_markup=conversation_user_keyboard())
            return
        if user_id in conversation_requests:
            safe_send(chat_id, "Твой запрос уже отправлен лидерскому составу.", reply_markup=back_keyboard())
            return

    display_name = clean_text(user.full_name or user.username or str(user_id))
    username = f"@{clean_text(user.username)}" if user.username else "не указан"
    request_text = (
        "<b>Запрос на беседу с лидерским составом</b>\n\n"
        f"Пользователь: <b>{display_name}</b>\n"
        f"Username: {username}\n"
        f"ID: <code>{user_id}</code>\n\n"
        "Выберите действие ниже."
    )
    sent = safe_send(
        APPLICATION_GROUP_ID,
        request_text,
        reply_markup=conversation_request_keyboard(user_id),
    )
    if not sent:
        safe_send(chat_id, "Не удалось отправить запрос в группу. Попробуй позже.", reply_markup=back_keyboard())
        return

    with data_lock:
        conversation_requests[user_id] = {
            "group_id": APPLICATION_GROUP_ID,
            "message_id": sent.message_id,
        }
    safe_send(
        chat_id,
        "Запрос отправлен лидерскому составу. Ожидай принятия беседы.",
        reply_markup=back_keyboard(),
    )


def accept_conversation(group_id, message_id, reviewer_id, user_id):
    with data_lock:
        if user_id in conversation_sessions:
            return "active"
        conversation_requests.pop(user_id, None)
        conversation_sessions[user_id] = {
            "user_chat_id": user_id,
            "group_id": group_id,
            "request_message_id": message_id,
            "reviewer_id": reviewer_id,
        }

    remove_inline_keyboard(group_id, message_id)
    try:
        bot.edit_message_reply_markup(
            group_id,
            message_id,
            reply_markup=conversation_group_keyboard(user_id),
        )
    except Exception:
        logger.debug("Не удалось добавить кнопку завершения беседы")
    safe_send(
        user_id,
        "Беседа принята. Можешь написать сообщение лидерскому составу.",
        reply_markup=conversation_user_keyboard(),
    )
    safe_send(
        group_id,
        "Беседа открыта. Ответьте на сообщение пользователя, чтобы начать диалог.",
        reply_markup=conversation_group_keyboard(user_id),
    )
    return "accepted"


def decline_conversation(group_id, message_id, user_id):
    with data_lock:
        conversation_requests.pop(user_id, None)
        active = user_id in conversation_sessions
    if active:
        return "active"
    remove_inline_keyboard(group_id, message_id)
    safe_send(user_id, "Запрос на беседу отклонён лидерским составом.", reply_markup=back_keyboard())
    safe_send(group_id, "Запрос на беседу отклонён.")
    return "declined"


def close_conversation(user_id, ended_by, source_group_id=None):
    with data_lock:
        session = conversation_sessions.pop(user_id, None)
        if not session:
            return False
        conversation_requests.pop(user_id, None)
        stale_keys = [
            key for key, target_user_id in conversation_group_messages.items()
            if target_user_id == user_id
        ]
        for key in stale_keys:
            conversation_group_messages.pop(key, None)

    group_id = session["group_id"]
    if ended_by == "user":
        safe_send(user_id, "Беседа завершена пользователем.", reply_markup=back_keyboard())
        safe_send(group_id, "Пользователь завершил беседу.")
    else:
        safe_send(user_id, "Беседа завершена лидерским составом.", reply_markup=back_keyboard())
        safe_send(group_id, "Беседа завершена лидерским составом.")
    return True


def conversation_user_for_group_message(message):
    if message.chat.id != APPLICATION_GROUP_ID:
        return 0
    reply_to = getattr(message, "reply_to_message", None)
    reply_message_id = getattr(reply_to, "message_id", None)
    with data_lock:
        if reply_message_id:
            user_id = conversation_group_messages.get((message.chat.id, reply_message_id))
            if user_id in conversation_sessions:
                return user_id
        active_users = [
            user_id
            for user_id, session in conversation_sessions.items()
            if session["group_id"] == message.chat.id
        ]
    return active_users[0] if len(active_users) == 1 else 0


def send_conversation_message(message, target_chat_id, user_id, from_group):
    keyboard = conversation_user_keyboard() if from_group else conversation_group_keyboard(user_id)
    try:
        if message.content_type == "text":
            if from_group:
                heading = f"<b>Сообщение от {reviewer_label(message.from_user.id)}</b>"
            else:
                heading = "<b>Сообщение от пользователя</b>"
            return safe_send(
                target_chat_id,
                f"{heading}\n\n<blockquote>{clean_text(message.text)}</blockquote>",
                reply_markup=keyboard,
            )

        if message.content_type == "voice":
            if from_group:
                caption = f"<b>Голосовое сообщение от {reviewer_label(message.from_user.id)}</b>"
            else:
                caption = "<b>Голосовое сообщение от пользователя</b>"
            return bot.send_voice(
                target_chat_id,
                message.voice.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        return bot.copy_message(
            target_chat_id,
            message.chat.id,
            message.message_id,
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Не удалось переслать сообщение беседы")
        return None


def relay_user_conversation_message(message):
    with data_lock:
        session = conversation_sessions.get(message.chat.id)
    if not session:
        return
    sent = send_conversation_message(
        message,
        session["group_id"],
        message.chat.id,
        from_group=False,
    )
    if sent and getattr(sent, "message_id", None):
        with data_lock:
            conversation_group_messages[(session["group_id"], sent.message_id)] = message.chat.id
    if not sent:
        safe_send(message.chat.id, "Не удалось отправить сообщение лидерскому составу. Попробуй ещё раз.", reply_markup=conversation_user_keyboard())


def relay_group_conversation_message(message, user_id):
    with data_lock:
        session = conversation_sessions.get(user_id)
    if not session:
        return
    sent = send_conversation_message(
        message,
        user_id,
        user_id,
        from_group=True,
    )
    if not sent:
        safe_send(message.chat.id, "Не удалось отправить сообщение пользователю.", reply_markup=conversation_group_keyboard(user_id))


def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Заполнить анкету", callback_data="open_application"))
    keyboard.add(InlineKeyboardButton("Беседа с лидерским составом", callback_data="open_conversation"))
    return keyboard


def back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Назад", callback_data="user_back"))
    return keyboard


def application_back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Назад", callback_data="application_back"))
    return keyboard


def review_keyboard(message_id, user_chat_id=0):
      keyboard = InlineKeyboardMarkup(row_width=1)
      callback_target = f"{message_id}:{user_chat_id}" if user_chat_id else str(message_id)
      keyboard.add(InlineKeyboardButton("Ответить", callback_data=f"answer_application:{callback_target}"))
      keyboard.add(InlineKeyboardButton("Назад", callback_data=f"back_application:{message_id}"))
      return keyboard
    

def waiting_keyboard(message_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"back_application:{message_id}"))
    return keyboard


def is_configured():
    return APPLICATION_GROUP_ID != 0


def is_reviewer(user_id):
    if LEADER_ID and user_id == LEADER_ID:
        return True
    if DEPUTY_ID and user_id == DEPUTY_ID:
        return True
    if not is_configured():
        return False
    try:
        member = bot.get_chat_member(APPLICATION_GROUP_ID, user_id)
        return member.status in {"administrator", "creator"}
    except Exception:
        logger.exception("Не удалось проверить права пользователя %s", user_id)
        return False


def reviewer_label(user_id):
    if LEADER_ID and user_id == LEADER_ID:
        return "Лидера клана SK"
    if DEPUTY_ID and user_id == DEPUTY_ID:
        return "со-лидера клана SK"
    return "Лидера или со-лидера клана SK"


def send_question(chat_id):
    with data_lock:
        state = application_states.get(chat_id)
        if not state:
            return
        index = state["index"]
        title, prompt, kind = APPLICATION_QUESTIONS[index]
        previous_message_id = state.get("question_message_id")
        state["question_message_id"] = None

    if previous_message_id:
        safe_delete(chat_id, previous_message_id)

    text = (
        f"<b>Вопрос {index + 1}/{len(APPLICATION_QUESTIONS)}</b>\n\n"
        f"<b>{clean_text(title)}</b>\n"
        f"{clean_text(prompt)}"
    )
    if kind == "voice":
        text += f"\n\n{VOICE_WARNING}"

    sent = safe_send(chat_id, text, reply_markup=application_back_keyboard())
    if sent:
        with data_lock:
            state = application_states.get(chat_id)
            if state:
                state["question_message_id"] = sent.message_id


def start_application(chat_id):
    if not is_configured():
        safe_send(chat_id, "Анкета пока не настроена: укажите APPLICATION_GROUP_ID.", reply_markup=back_keyboard())
        return
    with data_lock:
        application_states[chat_id] = {"index": 0, "answers": [], "question_message_id": None}
    send_question(chat_id)


def format_application(answers):
    lines = ["<b>Анкета</b>", ""]
    for (title, _prompt, _kind), answer in zip(APPLICATION_QUESTIONS, answers):
        if isinstance(answer, dict) and answer.get("type") == "voice":
            value = "Голосовое сообщение прикреплено ниже."
        else:
            value = clean_text(answer)
        lines.append(f"<b>{clean_text(title)}:</b> {value}")
    return "\n".join(lines)


def edit_review_buttons(message_id, keyboard):
    try:
        bot.edit_message_reply_markup(APPLICATION_GROUP_ID, message_id, reply_markup=keyboard)
    except Exception:
        logger.debug("Не удалось обновить кнопки сообщения %s", message_id)


def finish_application(chat_id, answers):
    if not is_configured():
        safe_send(chat_id, "Не удалось передать анкету: не указана APPLICATION_GROUP_ID.", reply_markup=back_keyboard())
        return

    sent = safe_send(APPLICATION_GROUP_ID, format_application(answers))
    if not sent:
        safe_send(chat_id, "Не удалось передать анкету в группу. Попробуй позже.", reply_markup=back_keyboard())
        return

    with data_lock:
        application_by_message[(APPLICATION_GROUP_ID, sent.message_id)] = chat_id
    edit_review_buttons(sent.message_id, review_keyboard(sent.message_id))

    for answer in answers:
        if isinstance(answer, dict) and answer.get("type") == "voice":
            try:
                bot.send_voice(
                    APPLICATION_GROUP_ID,
                    answer["file_id"],
                    caption="<b>SK</b>\n\n<b>Голосовое сообщение кандидата</b>",
                    parse_mode="HTML",
                )
            except Exception:
                logger.exception("Не удалось отправить голосовое сообщение кандидата")

    safe_send(chat_id, FINAL_TEXT, reply_markup=back_keyboard())


def send_reviewer_reply(group_id, reviewer_id, text):
    with data_lock:
        pending = pending_replies.pop((group_id, reviewer_id), None)
    if not pending:
        return

    label = reviewer_label(reviewer_id)
    reply_text = (
        f"<b>Ответ от {label}</b>\n\n"
        f"<blockquote>{clean_text(text)}</blockquote>"
    )
    sent = safe_send(pending["user_chat_id"], reply_text, reply_markup=back_keyboard())
    if sent:
        edit_review_buttons(pending["message_id"], review_keyboard(pending["message_id"]))
        safe_send(group_id, "Ответ отправлен пользователю.")
    else:
        safe_send(group_id, "Не удалось отправить ответ пользователю. Возможно, он заблокировал бота.")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    try:
        with open(WELCOME_IMAGE_PATH, "rb") as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
    except FileNotFoundError:
        logger.exception("Файл приветственного изображения не найден")
        safe_send(message.chat.id, WELCOME_TEXT, reply_markup=main_menu_keyboard())
    except Exception:
        logger.exception("Не удалось отправить приветственное изображение")
        safe_send(message.chat.id, WELCOME_TEXT, reply_markup=main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data or ""
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        logger.debug("Не удалось подтвердить callback %s", call.id)

    if data == "open_conversation":
        safe_delete(chat_id, message_id)
        start_conversation_request(chat_id, call.from_user)
        return

    if data.startswith("conversation_accept:"):
        if chat_id != APPLICATION_GROUP_ID or not is_reviewer(call.from_user.id):
            safe_send(chat_id, "Только лидерский состав может принять запрос.")
            return
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        result = accept_conversation(chat_id, message_id, call.from_user.id, user_id)
        if result == "active":
            safe_send(chat_id, "У этого пользователя уже есть активная беседа.")
        return

    if data.startswith("conversation_decline:"):
        if chat_id != APPLICATION_GROUP_ID or not is_reviewer(call.from_user.id):
            safe_send(chat_id, "Только лидерский состав может отклонить запрос.")
            return
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        result = decline_conversation(chat_id, message_id, user_id)
        if result == "active":
            safe_send(chat_id, "Нельзя отклонить уже активную беседу.")
        return

    if data == "conversation_end_user":
        close_conversation(chat_id, "user")
        return

    if data.startswith("conversation_end_group:"):
        if chat_id != APPLICATION_GROUP_ID or not is_reviewer(call.from_user.id):
            safe_send(chat_id, "Только лидерский состав может закончить беседу.")
            return
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        close_conversation(user_id, "group", chat_id)
        return

    if data == "open_application":
        safe_delete(chat_id, message_id)
        start_application(chat_id)
        return

    if data == "user_back":
        safe_delete(chat_id, message_id)
        send_welcome(call.message)
        return

    if data == "application_back":
        with data_lock:
            state = application_states.get(chat_id)
            if not state or state["index"] == 0:
                application_states.pop(chat_id, None)
                return_to_menu = True
            else:
                state["index"] -= 1
                if state["answers"]:
                    state["answers"].pop()
                return_to_menu = False
        safe_delete(chat_id, message_id)
        if return_to_menu:
            send_welcome(call.message)
        else:
            send_question(chat_id)
        return

    if data.startswith("answer_application:"):
        if chat_id != APPLICATION_GROUP_ID:
            return
        parts = data.split(":")
        try:
            source_message_id = int(parts[1])
            callback_user_id = int(parts[2]) if len(parts) > 2 else 0
        except (IndexError, ValueError):
            return
        with data_lock:
            user_chat_id = application_by_message.get((chat_id, source_message_id))
            if not user_chat_id and callback_user_id:
                user_chat_id = callback_user_id
            if user_chat_id:
                pending_replies[(chat_id, call.from_user.id)] = {
                    "user_chat_id": user_chat_id,
                    "message_id": source_message_id,
                }
        if not user_chat_id:
            safe_send(chat_id, "Анкета не найдена. Начните новую анкету, если бот был перезапущен.")
            return
        edit_review_buttons(source_message_id, waiting_keyboard(source_message_id))
        safe_send(
            chat_id,
            "Нажмите «Ответить» на это сообщение и напишите ответ. Он будет отправлен пользователю.",
            reply_to_message_id=source_message_id,
            reply_markup=types.ForceReply(selective=False),
        )
        return
    if data.startswith("back_application:"):
        try:
            source_message_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with data_lock:
            pending_replies.pop((chat_id, call.from_user.id), None)
        edit_review_buttons(source_message_id, review_keyboard(source_message_id, application_by_message.get((chat_id, source_message_id), 0)))


@bot.message_handler(
    func=lambda message: message.chat.id in conversation_sessions,
    content_types=CONVERSATION_CONTENT_TYPES,
)
def handle_conversation_user_message(message):
    relay_user_conversation_message(message)


@bot.message_handler(
    func=lambda message: message.chat.id in application_states,
    content_types=["text", "voice"],
)
def handle_application_input(message):
    chat_id = message.chat.id
    with data_lock:
        state = application_states.get(chat_id)
        if not state:
            return
        index = state["index"]
        title, prompt, kind = APPLICATION_QUESTIONS[index]

    if kind == "voice":
        if not getattr(message, "voice", None):
            safe_send(chat_id, "Пожалуйста, отправь именно голосовое сообщение.", reply_markup=application_back_keyboard())
            return
        answer = {"type": "voice", "file_id": message.voice.file_id}
    else:
        if not message.text or not message.text.strip():
            safe_send(chat_id, "Пожалуйста, ответь текстом.", reply_markup=application_back_keyboard())
            return
        answer = message.text.strip()

    with data_lock:
        state = application_states.get(chat_id)
        if not state:
            return
        state["answers"].append(answer)
        state["index"] += 1
        finished = state["index"] >= len(APPLICATION_QUESTIONS)
        question_message_id = state.get("question_message_id")
        answers = list(state["answers"])
        if finished:
            application_states.pop(chat_id, None)

    if question_message_id:
        safe_delete(chat_id, question_message_id)
    if finished:
        finish_application(chat_id, answers)
    else:
        send_question(chat_id)


@bot.message_handler(
    func=lambda message: (
        message.chat.id == APPLICATION_GROUP_ID
        and conversation_user_for_group_message(message) != 0
    ),
    content_types=CONVERSATION_CONTENT_TYPES,
)
def handle_conversation_group_message(message):
    if not is_reviewer(getattr(message.from_user, "id", 0)):
        return
    user_id = conversation_user_for_group_message(message)
    if user_id:
        relay_group_conversation_message(message, user_id)


@bot.message_handler(
    func=lambda message: (
        message.chat.id == APPLICATION_GROUP_ID
        and (message.chat.id, getattr(message.from_user, "id", 0)) in pending_replies
    )
)
def handle_reviewer_reply(message):
    if not message.text or not message.text.strip():
        safe_send(message.chat.id, "Пожалуйста, напиши ответ текстом.")
        return
    send_reviewer_reply(message.chat.id, message.from_user.id, message.text.strip())


if __name__ == "__main__":
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if external_url:
        webhook_url = f"{external_url.rstrip('/')}/telegram-webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info("Telegram webhook включён: %s", webhook_url)
        # Render должен продолжать работать после установки webhook.
        run_flask()
    else:
        logger.info("RENDER_EXTERNAL_URL не найден, запускаем polling")
        threading.Thread(target=run_flask, daemon=True).start()
        bot.infinity_polling(skip_pending=True)
