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

WELCOME_TEXT = (
    "Приветствую. Ты тут что бы подать анкету на вступ в клан SK.\n\n"
    "Удачи.\n"
    "by. tt:SK_Kitezz"
)
FINAL_TEXT = "На этом все. Анкета передана Лидеру и Заместителю клана SK."
VOICE_WARNING = (
    "⚠️ <b>WARNING:</b> Голосовое сообщение нужно для подтверждения возраста, "
    "а также чтобы заметить тебя при повторном входе в клан с другого аккаунта."
)


# Состояние хранится в памяти процесса.
data_lock = threading.Lock()
application_states = {}
application_by_message = {}
pending_replies = {}


def clean_text(value):
    return html_escape(str(value), quote=False)


def safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception:
        logger.exception("Ошибка отправки сообщения в чат %s", chat_id)
        return None


def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        logger.debug("Не удалось удалить сообщение %s в чате %s", message_id, chat_id)


def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Заполнить анкету", callback_data="open_application"))
    return keyboard


def back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="user_back"))
    return keyboard


def application_back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="application_back"))
    return keyboard


def review_keyboard(message_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Ответить", callback_data=f"answer_application:{message_id}"))
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"back_application:{message_id}"))
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
        return "заместителя клана SK"
    return "Лидера или заместителя клана SK"


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
                    caption="Голосовое сообщение кандидата",
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
    reply_text = f"💬 <b>Сообщение от {label}</b>\n\n{clean_text(text)}"
    sent = safe_send(pending["user_chat_id"], reply_text, reply_markup=back_keyboard())
    if sent:
        edit_review_buttons(pending["message_id"], review_keyboard(pending["message_id"]))
        safe_send(group_id, "Ответ отправлен пользователю.")
    else:
        safe_send(group_id, "Не удалось отправить ответ пользователю. Возможно, он заблокировал бота.")


@bot.message_handler(commands=["start"])
def send_welcome(message):
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
        if not is_reviewer(call.from_user.id):
            try:
                bot.answer_callback_query(call.id, "Ответить может только лидер или заместитель.", show_alert=True)
            except Exception:
                logger.debug("Не удалось показать предупреждение о правах")
            return
        try:
            source_message_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with data_lock:
            user_chat_id = application_by_message.get((chat_id, source_message_id))
            if user_chat_id:
                pending_replies[(chat_id, call.from_user.id)] = {
                    "user_chat_id": user_chat_id,
                    "message_id": source_message_id,
                }
        if not user_chat_id:
            safe_send(chat_id, "Анкета не найдена или бот был перезапущен.")
            return
        edit_review_buttons(source_message_id, waiting_keyboard(source_message_id))
        safe_send(chat_id, "Напишите ответ одним сообщением. Он будет отправлен пользователю.", reply_to_message_id=source_message_id)
        return

    if data.startswith("back_application:"):
        try:
            source_message_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        with data_lock:
            pending_replies.pop((chat_id, call.from_user.id), None)
        edit_review_buttons(source_message_id, review_keyboard(source_message_id))


@bot.message_handler(func=lambda message: message.chat.id in application_states)
def handle_application_input(message):
    chat_id = message.chat.id
    with data_lock:
        state = application_states.get(chat_id)
        if not state:
            return
        index = state["index"]
        title, prompt, kind = APPLICATION_QUESTIONS[index]

    if kind == "voice":
        if not message.voice:
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
        and (message.chat.id, getattr(message.from_user, "id", 0)) in pending_replies
    )
)
def handle_reviewer_reply(message):
    if not message.text or not message.text.strip():
        safe_send(message.chat.id, "Пожалуйста, напиши ответ текстом.")
        return
    if not is_reviewer(message.from_user.id):
        return
    send_reviewer_reply(message.chat.id, message.from_user.id, message.text.strip())


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if external_url:
        webhook_url = f"{external_url.rstrip('/')}/telegram-webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info("Telegram webhook включён: %s", webhook_url)
    else:
        logger.info("RENDER_EXTERNAL_URL не найден, запускаем polling")
        bot.infinity_polling(skip_pending=True)
