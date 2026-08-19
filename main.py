import os
import time
import threading
import string
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# --- ИНИЦИАЛИЗАЦИЯ И МИНИ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Токен твоего бота
TOKEN = "8957734826:AAGqRDleUdLICnkjuabbhWppz807q8JA9js"
bot = telebot.TeleBot(TOKEN)

# Потокобезопасные блокировки и хранилища
data_lock = threading.Lock()
user_data = {}
waiting_for_key = set()

# --- БАЗА КЛЮЧЕЙ ---
UNIVERSAL_KEY = "7879"

VALID_KEYS = {
    "47a9f2", "88b3c1", "12e4f5", "99h4g6", "33k2l9",
    "55z7x8", "19q3w2", "66e5r4", "77t8y1", "22u9i0",
    "44o1p3", "58a6s7", "39d2f1", "81g9h8", "73j4k5",
    "14l2z3", "95x6c7", "26v5b8", "67n1m2", "49q8w7",
    "31e2r3", "84t5y6", "52u1i9", "76o4p2", "18a3s4",
    "93d5f6", "25g7h8", "64j1k2", "41l3z2", "89x9c8",
    "17v4b5", "56n6m7", "38q1w9", "72e2r4", "11t7y8",
    "94u3i2", "28o5p6", "63a8s1", "45d4f3", "87g2h5",
    "59j6k7", "21l1z9", "74x4c3", "16v2b1", "98n8m9",
    "34q5w6", "69e7r8", "53t9y2", "82u4i1", "27o3p8"
}

USED_KEYS = set()

# --- ВАРИАНТЫ ОТВЕТОВ ---
YES_VARIANTS = ["да", "можно", "конечно", "разрешено"]
NO_VARIANTS = ["нет", "нельзя", "не можно", "запрещено"]

# --- БАЗА ВОПРОСОВ ---
GOV_QUESTIONS = [
    {"q": "Можно ли лидеру принимать или повышать игроков по дню блата выше установленных для его организации рангов?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено (это карается вплоть до снятия)."},
    {"q": "Разрешено ли сотрудникам просить администрацию или лидеров проверить их поданные заявления на перевод?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено."},
    {"q": "Можно ли использовать чат департамента для обсуждения каких-либо личных вопросов или споров?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено."},
    {"q": "Допускается ли создание собеседования через планшет (/addvacancy) всего за 10 минут до его начала?", "valid": NO_VARIANTS, "ans_text": "Нет, нельзя (минимум за 30 минут, максимум за 60)."},
    {"q": "Может ли заместитель организации производить увольнения или повышения по дню блата?", "valid": NO_VARIANTS, "ans_text": "Нет, этим занимается исключительно лидер."},
    {"q": "Разрешено ли не выполнять прямые указания и приказы вышестоящих лиц, например Губернатора, в чате департамента?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено."},
    {"q": "Обязательно ли указывать критерии и точное время проведения при подаче государственной волны для собеседования?", "valid": YES_VARIANTS, "ans_text": "Да, это строго обязательно."},
    {"q": "Можно ли создавать дублирующие или бессмысленные подразделения внутри государственной организации?", "valid": NO_VARIANTS, "ans_text": "Нет, каждое подразделение должно иметь четкую цель и функционал."},
    {"q": "Разрешено ли следящему администратору прервать день блата, если у лидера накопилось 2 и более нарушения?", "valid": YES_VARIANTS, "ans_text": "Да, имеет полное право."},
    {"q": "Может ли в одном подразделении состоять сразу 3 или 4 официальных заместителя?", "valid": NO_VARIANTS, "ans_text": "Нет, допускается максимум 2 заместителя."},
    {"q": "Разрешено ли переводиться в другую организацию человеку, если он не отработал более 7 дней после получения нового ранга?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено."},
    {"q": "Нужно ли делать скриншот (/c 60) созданной вакансии в планшете для отправки в специальную конференцию гос. волны?", "valid": YES_VARIANTS, "ans_text": "Да, обязательно."},
    {"q": "Имеет ли право лидер пытаться отговорить сотрудника от перевода в другую организацию?", "valid": YES_VARIANTS, "ans_text": "Да, разрешено попытаться отговорить, но оказывать давление нельзя."},
    {"q": "Можно ли проводить официальное собеседование в гос. волну ровно 15 минут вместо положенных?", "valid": NO_VARIANTS, "ans_text": "Нет, собеседование должно длиться строго 30 минут."},
    {"q": "Разрешено ли лидеру Медиацентра «Темп» принимать игроков по дню блата на 5 ранг?", "valid": NO_VARIANTS, "ans_text": "Нет, максимум до 3 ранга."},
    {"q": "Разрешено ли использовать чат департамента для отправки сообщений от имени всех госсруктур без нужного тега?", "valid": NO_VARIANTS, "ans_text": "Нет, нужно четко соблюдать правила пользования."},
    {"q": "Обязан ли начальник или заместитель подразделения публиковать приказы о назначении сотрудников на форуме?", "valid": YES_VARIANTS, "ans_text": "Да, все приказы должны быть опубликованы."},
    {"q": "Можно ли использовать ночные наборы для обычного обязательного ежедневного отчета фракции?", "valid": NO_VARIANTS, "ans_text": "Нет, данные наборы не идут в обычный отчет и проводятся по желанию."},
    {"q": "Разрешено ли провоцировать состав организации, из которой вы собираетесь перевестись?", "valid": NO_VARIANTS, "ans_text": "Нет, запрещено (лидер вправе отказать)."},
    {"q": "Нужно ли делать напоминание в гос. волну через 15 минут после начала собеседования?", "valid": YES_VARIANTS, "ans_text": "Да, это обязательный пункт правил."},
    {"q": "Можно ли лидеру Армии принимать людей по дню блата на 4 ранг?", "valid": NO_VARIANTS, "ans_text": "Нет, армиям разрешено только до 2 ранга."},
    {"q": "Разрешено ли игроку переводиться с целью намеренного «слива» чужого состава?", "valid": NO_VARIANTS, "ans_text": "Нет, за это выдается черный список навсегда."},
    {"q": "Обязан ли лидер после одобрения подразделения создать отдельную тему на форуме с описанием и составом?", "valid": YES_VARIANTS, "ans_text": "Да, это требование правил."},
    {"q": "Можно ли завершать собеседование через гос. волну позже 21:00 (например, в 21:30)?", "valid": YES_VARIANTS, "ans_text": "Да, после 21:00 разрешено ТОЛЬКО закончить начатое собеседование."}
]

CRIME_QUESTIONS = [
    {"q": "Можно ли грабителям инкассаторов состоять в разных фракциях при совершении одного ограбления?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Допускается ли нападение на военную базу группой из 4 человек?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли похитить лидера организации два раза за один день?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Разрешено ли во время «капта» (войны за территории) использовать стороннее ПО?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли совершить нападение на фуру с материалами прямо на территории склада?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Обязаны ли все участники ограбления инкассаторов быть в масках?", "valid": YES_VARIANTS, "ans_text": "Да"},
    {"q": "Разрешено ли убить заложника после получения выкупа при похищении?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли находиться на военной базе без маски, если ты член нелегальной организации?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Имеет ли право третья ОПГ вмешиваться в войну за территорию между двумя другими бандами?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли похитить гражданского человека?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Разрешено ли нападать на ВЧ в 3 часа ночи?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Нужно ли отыгрывать РП-действия при нападении на военный конвой?", "valid": YES_VARIANTS, "ans_text": "Да"},
    {"q": "Можно ли сбивать анимацию аптечки или употребления еды во время войны за территории?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Разрешено ли похищать людей в зеленых зонах?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Может ли в похищении участвовать игрок, который не состоит в ОПГ?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли использовать вертолет для занятия высоток во время войны за территорию?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Допускается ли нападение на фуру с материалами в местах, не предусмотренных правилами?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли использовать аптечку в бою во время войны за территорию?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Обязательно ли иметь при себе огнестрельное оружие при ограблении инкассаторов?", "valid": YES_VARIANTS, "ans_text": "Да"},
    {"q": "Можно ли похищать одновременно трех человек?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли стрелять по заложнику во время похищения?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Разрешено ли сотрудникам армии находиться на территории военной части без формы?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли использовать для нападения на фуру личный транспорт, не относящийся к фракции или семье?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Можно ли убивать игроков, которые просто проезжают мимо места проведения войны за территорию и не участвуют в ней?", "valid": NO_VARIANTS, "ans_text": "Нет"},
    {"q": "Требуется ли наличие игрока не ниже 6-го ранга среди грабителей инкассаторов?", "valid": YES_VARIANTS, "ans_text": "Да"}
]

# --- КЛАВИАТУРЫ ---
def get_rules_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📜 Правила ввода ответа", callback_data="show_rules"))
    return keyboard

def get_factions_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Правительство", callback_data="fact_Правительство"),
        InlineKeyboardButton("СГБ", callback_data="fact_СГБ"),
        InlineKeyboardButton("Полиция", callback_data="fact_Полиция"),
        InlineKeyboardButton("Больница", callback_data="fact_Больница"),
        InlineKeyboardButton("ТРК", callback_data="fact_ТРК"),
        InlineKeyboardButton("Армия", callback_data="fact_Армия"),
        InlineKeyboardButton("Служба Спасения", callback_data="fact_Служба Спасения"),
        InlineKeyboardButton("ОПГ Тамбовское", callback_data="fact_ОПГ Тамбовское"),
        InlineKeyboardButton("ОПГ Кавказское", callback_data="fact_ОПГ Кавказское"),
        InlineKeyboardButton("ОПГ Оффники", callback_data="fact_ОПГ Оффники"),
    )
    return keyboard

def get_start_exam_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("▶️ Начать", callback_data="start_test"),
        InlineKeyboardButton("🔄 Сменить фракцию", callback_data="change_faction")
    )
    return keyboard

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    with data_lock:
        user_data.pop(chat_id, None)
        waiting_for_key.add(chat_id)
    
    try:
        bot.send_message(chat_id, "🔐 Введите ключ доступа для запуска бота:")
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.chat.id in waiting_for_key)
def handle_key_input(message):
    chat_id = message.chat.id
    entered_key = message.text.strip()

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    with data_lock:
        if entered_key == UNIVERSAL_KEY:
            waiting_for_key.discard(chat_id)
            show_main_welcome(chat_id)
            return

        if entered_key in VALID_KEYS and entered_key not in USED_KEYS:
            USED_KEYS.add(entered_key)
            waiting_for_key.discard(chat_id)
            show_main_welcome(chat_id)
            return

    try:
        bot.send_message(chat_id, "❌ Неверный ключ или он уже был использован. Попробуйте еще раз:")
    except Exception:
        pass

def show_main_welcome(chat_id):
    text = "Приветствую. Данный бот создал Mike_Tysonn чтобы подготовить тебя к обзвону.\n\nПеред началом нужно ознакомится с правилами ввода ответа."
    
    try:
        try:
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(
                    chat_id, 
                    photo, 
                    caption=text, 
                    reply_markup=get_rules_keyboard()
                )
        except FileNotFoundError:
            bot.send_message(chat_id, text, reply_markup=get_rules_keyboard())
    except Exception:
        pass

# Обработка обычной кнопки снизу «Правила ввода ответа»
@bot.message_handler(func=lambda message: message.text == "Правила ввода ответа")
def handle_rules_reply_button(message):
    chat_id = message.chat.id
    rules_text = (
        "📜 **Правила ввода ответа:**\n\n"
        "• Если ваш ответ **«нет»**, то ответ будет засчитан только так: **нет, нельзя, не можно, запрещено**. Другие бот засчитает как за ОШИБКУ.\n\n"
        "• Если ваш ответ **«да»**, то ответ будет засчитан только так: **Да, Можно, Конечно, Разрешено**.\n\n"
        "• Если ваш ответ осуществляется в числовых, то ответ будет засчитан только так: **2+, не менее 2, 2 и больше, 2, два**. Касается абсолютно всех чисел."
    )
    try:
        bot.send_message(chat_id, rules_text, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data

    # Обязательно гасим кружок загрузки на инлайн-кнопке
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if data == "show_rules":
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        rules_text = (
            "📌 **Правила ввода ответа:**\n\n"
            "• Если ваш ответ **«нет»**, то ответ будет засчитан только так: **нет, нельзя, не можно, запрещено**.\n"
            "• Если ваш ответ **«да»**, то ответ будет засчитан только так: **Да, Можно, Конечно, Разрешено**.\n"
            "• Если ваш ответ в числовых значениях: **2+, не менее 2, 2 и больше, 2, два**.\n\n"
            "👇 Нажмите кнопку ниже, чтобы перейти к выбору фракции:"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Перейти к фракциям", callback_data="go_to_factions"))
        try:
            bot.send_message(chat_id, rules_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif data in ["go_to_factions", "change_faction", "back_to_menu"]:
        with data_lock:
            user_data.pop(chat_id, None)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        try:
            bot.send_message(chat_id, "📁 Выберите фракцию для подготовки:", reply_markup=get_factions_keyboard())
        except Exception:
            pass

    elif data.startswith("fact_"):
        faction_name = data.split("_", 1)[1]
        faction_type = "gov" if faction_name in ["Правительство", "СГБ", "Полиция", "Больница", "ТРК", "Армия", "Служба Спасения"] else "crime"
        
        with data_lock:
            user_data[chat_id] = {
                "questions": GOV_QUESTIONS if faction_type == "gov" else CRIME_QUESTIONS,
                "index": 0,
                "errors": [],
                "last_question_msg_id": None,
                "started": False
            }
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        
        try:
            bot.send_message(
                chat_id, 
                f"Выбрана Фракция - {faction_name} Начинаем обзвон?", 
                reply_markup=get_start_exam_keyboard()
            )
        except Exception:
            pass

    elif data == "start_test":
        with data_lock:
            if chat_id not in user_data or user_data[chat_id].get("started"):
                return
            user_data[chat_id]["started"] = True
            
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        send_next_question(chat_id)

def send_next_question(chat_id):
    with data_lock:
        if chat_id not in user_data:
            return
        u_data = user_data[chat_id]
        idx = u_data["index"]
        questions = u_data["questions"]

    if idx < len(questions):
        q_text = questions[idx]["q"]
        try:
            sent_msg = bot.send_message(chat_id, f"Вопрос {idx+1}/{len(questions)}:\n{q_text}")
            with data_lock:
                if chat_id in user_data:
                    user_data[chat_id]["last_question_msg_id"] = sent_msg.message_id
        except Exception:
            pass
    else:
        finish_exam(chat_id)

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id].get("started"))
def handle_answer(message):
    chat_id = message.chat.id
    
    with data_lock:
        if chat_id not in user_data:
            return
        u_data = user_data[chat_id]
        idx = u_data["index"]
        questions = u_data["questions"]

    if not message.text:
        try:
            bot.send_message(chat_id, "Пожалуйста, отправьте текстовый ответ.")
        except Exception:
            pass
        return

    raw_text = message.text.lower().strip()
    user_clean = raw_text.strip(string.punctuation + " ")
    correct_variants = questions[idx]["valid"]

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    is_correct = any(cv == user_clean or cv == raw_text for cv in correct_variants)

    status_msg = None
    if is_correct:
        try:
            status_msg = bot.send_message(chat_id, "верно🟢, переходим дальше.")
        except Exception:
            pass
    else:
        err_info = {
            "question": questions[idx]["q"],
            "user_ans": message.text,
            "correct_ans": questions[idx]["ans_text"]
        }
        with data_lock:
            if chat_id in user_data:
                user_data[chat_id]["errors"].append(err_info)
        try:
            status_msg = bot.send_message(chat_id, "неверно🔴 Ошибка засчитана. Количество ошибок будет подсчитано в конце обзвона")
        except Exception:
            pass

    with data_lock:
        last_msg_id = user_data.get(chat_id, {}).get("last_question_msg_id")

    if last_msg_id:
        try:
            bot.delete_message(chat_id, last_msg_id)
        except Exception:
            pass

    time.sleep(1.2)

    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            pass

    with data_lock:
        if chat_id in user_data:
            user_data[chat_id]["index"] += 1
            
    send_next_question(chat_id)

@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    chat_id = message.chat.id
    if chat_id in waiting_for_key:
        return
    with data_lock:
        is_active = chat_id in user_data and user_data[chat_id].get("started")
    if not is_active and message.text != "Правила ввода ответа":
        try:
            bot.send_message(chat_id, "Для начала работы введите /start")
        except Exception:
            pass

def finish_exam(chat_id):
    with data_lock:
        u_data = user_data.pop(chat_id, None)
    if not u_data:
        return

    errors_count = len(u_data["errors"])

    if errors_count <= 1:
        verdict = "Вы прошли обзвон 🎉"
    elif errors_count in [2, 3]:
        verdict = "Чуть чуть не хватило"
    elif errors_count in [4, 5]:
        verdict = "Стоит подучить правила"
    else:
        verdict = "Тебе явно нужно на форум"

    report = f"{verdict}\nошибок - {errors_count}\n\n"

    for err in u_data["errors"]:
        report += f"• {err['question']}\n ваш ответ - {err['user_ans']}.\n\nэто не верно. Верный ответ - {err['correct_ans']}\n\n"

    report += "согласно форуму. с уважением Mike_Tysonn"

    try:
        bot.send_message(chat_id, report)
    except Exception:
        pass

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Выбрать другую фракцию", callback_data="back_to_menu"))
    try:
        bot.send_message(chat_id, "Хотите пройти тест еще раз?", reply_markup=markup)
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)
