import logging
import random
import os
import string
import threading
import time

import telebot
from flask import Flask, request
from telebot import types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# =========================
# Flask-сервер для Render
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is alive and running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """Принимает обновления Telegram через webhook и передаёт их боту."""
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


# =========================
# Telegram-бот
# =========================

# Токен НЕ вставляй прямо в код.
# На Render создай переменную окружения BOT_TOKEN.
TOKEN = os.environ["BOT_TOKEN"]

bot = telebot.TeleBot(TOKEN)


# =========================
# Хранилища
# =========================

data_lock = threading.Lock()

user_data = {}
waiting_for_key = set()
used_keys = set()


# =========================
# Ключи доступа
# =========================

UNIVERSAL_KEY = "7879"

VALID_KEYS = {
    "47a9f2",
    "88b3c1",
    "12e4f5",
    "99h4g6",
    "33k2l9",
    "55z7x8",
    "19q3w2",
    "66e5r4",
    "77t8y1",
    "22u9i0",
    "44o1p3",
    "58a6s7",
    "39d2f1",
    "81g9h8",
    "73j4k5",
    "14l2z3",
    "95x6c7",
    "26v5b8",
    "67n1m2",
    "49q8w7",
    "31e2r3",
    "84t5y6",
    "52u1i9",
    "76o4p2",
    "18a3s4",
    "93d5f6",
    "25g7h8",
    "64j1k2",
    "41l3z2",
    "89x9c8",
    "17v4b5",
    "56n6m7",
    "38q1w9",
    "72e2r4",
    "11t7y8",
    "94u3i2",
    "28o5p6",
    "63a8s1",
    "45d4f3",
    "87g2h5",
    "59j6k7",
    "21l1z9",
    "74x4c3",
    "16v2b1",
    "98n8m9",
    "34q5w6",
    "69e7r8",
    "53t9y2",
    "82u4i1",
    "27o3p8",
}


# =========================
# Варианты ответов
# =========================

YES_VARIANTS = {
    "да",
    "можно",
    "конечно",
    "разрешено",
}

NO_VARIANTS = {
    "нет",
    "нельзя",
    "не можно",
    "запрещено",
}


# =========================
# Вопросы государственных фракций
# =========================

GOV_QUESTIONS = [
    {
        "q": "Можно ли лидеру принимать или повышать игроков по дню блата выше установленных для его организации рангов?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено (это карается вплоть до снятия).",
    },
    {
        "q": "Разрешено ли сотрудникам просить администрацию или лидеров проверить их поданные заявления на перевод?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено.",
    },
    {
        "q": "Можно ли использовать чат департамента для обсуждения каких-либо личных вопросов или споров?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено.",
    },
    {
        "q": "Допускается ли создание собеседования через планшет (/addvacancy) всего за 10 минут до его начала?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, нельзя (минимум за 30 минут, максимум за 60).",
    },
    {
        "q": "Может ли заместитель организации производить увольнения или повышения по дню блата?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, этим занимается исключительно лидер.",
    },
    {
        "q": "Разрешено ли не выполнять прямые указания и приказы вышестоящих лиц, например Губернатора, в чате департамента?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено.",
    },
    {
        "q": "Обязательно ли указывать критерии и точное время проведения при подаче государственной волны для собеседования?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, это строго обязательно.",
    },
    {
        "q": "Можно ли создавать дублирующие или бессмысленные подразделения внутри государственной организации?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, каждое подразделение должно иметь четкую цель и функционал.",
    },
    {
        "q": "Разрешено ли следящему администратору прервать день блата, если у лидера накопилось 2 и более нарушения?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, имеет полное право.",
    },
    {
        "q": "Может ли в одном подразделении состоять сразу 3 или 4 официальных заместителя?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, допускается максимум 2 заместителя.",
    },
    {
        "q": "Разрешено ли переводиться в другую организацию человеку, если он не отработал более 7 дней после получения нового ранга?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено.",
    },
    {
        "q": "Нужно ли делать скриншот (/c 60) созданной вакансии в планшете для отправки в специальную конференцию гос. волны?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, обязательно.",
    },
    {
        "q": "Имеет ли право лидер пытаться отговорить сотрудника от перевода в другую организацию?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, разрешено попытаться отговорить, но оказывать давление нельзя.",
    },
    {
        "q": "Можно ли проводить официальное собеседование в гос. волну ровно 15 минут вместо положенных?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, собеседование должно длиться строго 30 минут.",
    },
    {
        "q": "Разрешено ли лидеру Медиацентра «Темп» принимать игроков по дню блата на 5 ранг?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, максимум до 3 ранга.",
    },
    {
        "q": "Разрешено ли использовать чат департамента для отправки сообщений от имени всех госсруктур без нужного тега?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, нужно четко соблюдать правила пользования.",
    },
    {
        "q": "Обязан ли начальник или заместитель подразделения публиковать приказы о назначении сотрудников на форуме?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, все приказы должны быть опубликованы.",
    },
    {
        "q": "Можно ли использовать ночные наборы для обычного обязательного ежедневного отчета фракции?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, данные наборы не идут в обычный отчет и проводятся по желанию.",
    },
    {
        "q": "Разрешено ли провоцировать состав организации, из которой вы собираетесь перевестись?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, запрещено (лидер вправе отказать).",
    },
    {
        "q": "Нужно ли делать напоминание в гос. волну через 15 минут после начала собеседования?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, это обязательный пункт правил.",
    },
    {
        "q": "Можно ли лидеру Армии принимать людей по дню блата на 4 ранг?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, армиям разрешено только до 2 ранга.",
    },
    {
        "q": "Разрешено ли игроку переводиться с целью намеренного «слива» чужого состава?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет, за это выдается черный список навсегда.",
    },
    {
        "q": "Обязан ли лидер после одобрения подразделения создать отдельную тему на форуме с описанием и составом?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, это требование правил.",
    },
    {
        "q": "Можно ли завершать собеседование через гос. волну позже 21:00, например в 21:30?",
        "valid": YES_VARIANTS,
        "ans_text": "Да, после 21:00 разрешено только закончить начатое собеседование.",
    },
]


# =========================
# Вопросы криминальных фракций
# =========================

CRIME_QUESTIONS = [
    {
        "q": "Можно ли грабителям инкассаторов состоять в разных фракциях при совершении одного ограбления?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Допускается ли нападение на военную базу группой из 4 человек?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли похитить лидера организации два раза за один день?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Разрешено ли во время «капта» использовать стороннее ПО?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли совершить нападение на фуру с материалами прямо на территории склада?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Обязаны ли все участники ограбления инкассаторов быть в масках?",
        "valid": YES_VARIANTS,
        "ans_text": "Да",
    },
    {
        "q": "Разрешено ли убить заложника после получения выкупа при похищении?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли находиться на военной базе без маски, если ты член нелегальной организации?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Имеет ли право третья ОПГ вмешиваться в войну за территорию между двумя другими бандами?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли похитить гражданского человека?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Разрешено ли нападать на ВЧ в 3 часа ночи?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Нужно ли отыгрывать РП-действия при нападении на военный конвой?",
        "valid": YES_VARIANTS,
        "ans_text": "Да",
    },
    {
        "q": "Можно ли сбивать анимацию аптечки или употребления еды во время войны за территории?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Разрешено ли похищать людей в зеленых зонах?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Может ли в похищении участвовать игрок, который не состоит в ОПГ?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли использовать вертолет для занятия высоток во время войны за территорию?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Допускается ли нападение на фуру с материалами в местах, не предусмотренных правилами?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли использовать аптечку в бою во время войны за территорию?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Обязательно ли иметь при себе огнестрельное оружие при ограблении инкассаторов?",
        "valid": YES_VARIANTS,
        "ans_text": "Да",
    },
    {
        "q": "Можно ли похищать одновременно трех человек?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли стрелять по заложнику во время похищения?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Разрешено ли сотрудникам армии находиться на территории военной части без формы?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли использовать для нападения на фуру личный транспорт, не относящийся к фракции или семье?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Можно ли убивать игроков, которые просто проезжают мимо места войны за территорию и не участвуют в ней?",
        "valid": NO_VARIANTS,
        "ans_text": "Нет",
    },
    {
        "q": "Требуется ли наличие игрока не ниже 6-го ранга среди грабителей инкассаторов?",
        "valid": YES_VARIANTS,
        "ans_text": "Да",
    },
]


# =========================
# Вспомогательные функции
# =========================

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as exc:
        logger.debug(
            "Не удалось удалить сообщение %s: %s",
            message_id,
            exc,
        )


def safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception:
        logger.exception(
            "Ошибка отправки сообщения в чат %s",
            chat_id,
        )
        return None


# =========================
# РП-термины
# =========================

RP_QUESTIONS = [
  {
      "q": "Что такое ДМ? (Deathmatch)",
      "valid": {"убийство без причины"},
      "ans_text": "Убийство без причины.",
  },
  {
      "q": "Что такое ДБ? (DriveBy)",
      "valid": {"убийство машиной или с водительского места", "убийство транспортом"},
      "ans_text": "Убийство машиной или с водительского места.",
  },
  {
      "q": "Что такое СК? (Spawn Kill)",
      "valid": {"убийство после появления", "убийство на спавне"},
      "ans_text": "Убийство после появления (на спавне).",
  },
  {
      "q": "Что такое ТК? (TeamKill)",
      "valid": {"убийство своих"},
      "ans_text": "Убийство своих.",
  },
  {
      "q": "Что такое РП? (RolePlay)",
      "valid": {"игра по ролям"},
      "ans_text": "Игра по ролям.",
  },
  {
      "q": "Что такое МГ? (MetaGaming)",
      "valid": {"использование реальной информации в игре"},
      "ans_text": "Использование реальной информации в игре.",
  },
  {
      "q": "Что такое ГМ? (GodMode)",
      "valid": {"неуязвимость", "режим бога"},
      "ans_text": "Неуязвимость.",
  },
  {
      "q": "Что такое ПГ? (PowerGaming)",
      "valid": {"воображение себя героем", "драка с толпой или без оружия против вооруженного"},
      "ans_text": "Воображение себя героем (драка с толпой или без оружия против вооруженного).",
  },
  {
      "q": "Что такое РК? (RevengeKill)",
      "valid": {"возвращение на место смерти", "месть"},
      "ans_text": "Возвращение на место смерти / месть.",
  },
  {
      "q": "Что такое БХ? (BunnyHop)",
      "valid": {"бег с прыжками для ускорения"},
      "ans_text": "Бег с прыжками для ускорения.",
  },
  {
      "q": "Что такое УК? (Уголовный Кодекс)",
      "valid": {"уголовный кодекс"},
      "ans_text": "Уголовный кодекс.",
  },
  {
      "q": "Что такое АК? (Академический/Административный Кодекс)",
      "valid": {"административный кодекс", "академический кодекс", "административный или академический кодекс"},
      "ans_text": "Административный или академический кодекс.",
  },
  {
      "q": "Что такое ЗЗ? (Зеленая Зона)",
      "valid": {"зеленая зона", "зеленая зона место где запрещено насилие"},
      "ans_text": "Зеленая зона (место, где запрещено насилие).",
  },
  {
      "q": "Что такое ФР? (FastReloading)",
      "valid": {"баг с быстрой перезарядкой"},
      "ans_text": "Баг с быстрой перезарядкой.",
  },
  {
      "q": "Что такое ФМ? (FastMoving)",
      "valid": {"баг с быстрым перемещением"},
      "ans_text": "Баг с быстрым перемещением.",
  },
  {
      "q": "Что такое СХ? (SpeedHack)",
      "valid": {"чит на скорость"},
      "ans_text": "Чит на скорость.",
  },
  {
      "q": "Что такое ФФ? (FriendlyFire)",
      "valid": {"урон по своим"},
      "ans_text": "Урон по своим.",
  },
  {
      "q": "Что такое ЦК? (CharacterKill)",
      "valid": {"убийство по рп с потерей персонажа", "рп убийство с потерей персонажа", "rp убийство с потерей персонажа"},
      "ans_text": "RP-убийство с потерей персонажа.",
  },
  {
      "q": "Что такое УРП? (UnRolePlay)",
      "valid": {"уход от ролевой игры", "уход от рп"},
      "ans_text": "Уход от ролевой игры.",
  },
  {
      "q": "Что такое ТДМ? (Team DeathMatch)",
      "valid": {"командный бой"},
      "ans_text": "Командный бой.",
  },
  {
      "q": "Что такое МДМ? (Mass DeathMatch)",
      "valid": {"массовое убийство без причины"},
      "ans_text": "Массовое убийство без причины.",
  },
  {
      "q": "Что такое ОРП? (OffRolePlay)",
      "valid": {"уход от рп", "уход от ролевой игры"},
      "ans_text": "Уход от РП.",
  },
  {
      "q": "Что такое ЕПП? (Exploiting Pathing)",
      "valid": {"езда по полям"},
      "ans_text": "Езда по полям.",
  },
  {
      "q": "Что такое ПК? (PlayerKill)",
      "valid": {"убийство по рп", "смерть игрока по правилам рп", "смерть игрока по правилам ролевой игры"},
      "ans_text": "Смерть игрока по правилам РП.",
  },
  {
      "q": "Что такое ФЦК? (FractionCharacterKill)",
      "valid": {"фракционное убийство персонажа"},
      "ans_text": "Фракционное убийство персонажа.",
  },
  {
      "q": "Что такое OOC? (Out Of Character)",
      "valid": {"реальный мир", "информация вне игры", "реальный мир информация вне игры"},
      "ans_text": "Реальный мир / информация вне игры.",
  },
  {
      "q": "Что такое IC? (In Character)",
      "valid": {"игровой мир", "информация в игре", "игровой мир информация в игре"},
      "ans_text": "Игровой мир / информация в игре.",
  },
]




# =========================
# Клавиатуры
# =========================

def get_rules_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "📜 Правила ввода ответа",
            callback_data="show_rules",
        ),
        InlineKeyboardButton(
            "📖 Посмотреть ответы",
            callback_data="show_answers",
        ),
    )
    return keyboard


def get_opg_answers_text():
    return (
        "📖 <b>Ответы: ОПГ</b>\n\n"
        "<b>1. Можно ли грабителям инкассаторов состоять в разных фракциях при совершении одного ограбления?</b>\n"
        "Ответ — Нет\n\n"
        "<b>2. Допускается ли нападение на военную базу группой из 4 человек?</b>\n"
        "Ответ — Нет\n\n"
        "<b>3. Можно ли похитить лидера организации два раза за один день?</b>\n"
        "Ответ — Нет\n\n"
        "<b>4. Разрешено ли во время «капта» (войны за территории) использовать стороннее ПО?</b>\n"
        "Ответ — Нет\n\n"
        "<b>5. Можно ли совершить нападение на фуру с материалами прямо на территории склада?</b>\n"
        "Ответ — Нет\n\n"
        "<b>6. Обязаны ли все участники ограбления инкассаторов быть в масках?</b>\n"
        "Ответ — Да\n\n"
        "<b>7. Разрешено ли убить заложника после получения выкупа при похищении?</b>\n"
        "Ответ — Нет\n\n"
        "<b>8. Можно ли находиться на военной базе без маски, если ты член нелегальной организации?</b>\n"
        "Ответ — Нет\n\n"
        "<b>9. Имеет ли право третья ОПГ вмешиваться в войну за территорию между двумя другими бандами?</b>\n"
        "Ответ — Нет\n\n"
        "<b>10. Можно ли похитить гражданского человека?</b>\n"
        "Ответ — Нет\n\n"
        "<b>11. Разрешено ли нападать на ВЧ в 3 часа ночи?</b>\n"
        "Ответ — Нет\n\n"
        "<b>12. Нужно ли отыгрывать РП-действия при нападении на военный конвой?</b>\n"
        "Ответ — Да\n\n"
        "<b>13. Можно ли сбивать анимацию аптечки или употребления еды во время войны за территории?</b>\n"
        "Ответ — Нет\n\n"
        "<b>14. Разрешено ли похищать людей в зеленых зонах?</b>\n"
        "Ответ — Нет\n\n"
        "<b>15. Может ли в похищении участвовать игрок, который не состоит в ОПГ?</b>\n"
        "Ответ — Нет\n\n"
        "<b>16. Можно ли использовать вертолет для занятия высоток во время войны за территорию?</b>\n"
        "Ответ — Нет\n\n"
        "<b>17. Допускается ли нападение на фуру с материалами в местах, не предусмотренных правилами?</b>\n"
        "Ответ — Нет\n\n"
        "<b>18. Можно ли использовать аптечку в бою во время войны за территорию?</b>\n"
        "Ответ — Нет\n\n"
        "<b>19. Обязательно ли иметь при себе огнестрельное оружие при ограблении инкассаторов?</b>\n"
        "Ответ — Да\n\n"
        "<b>20. Можно ли похищать одновременно трех человек?</b>\n"
        "Ответ — Нет\n\n"
        "<b>21. Можно ли стрелять по заложнику во время похищения?</b>\n"
        "Ответ — Нет\n\n"
        "<b>22. Разрешено ли сотрудникам армии находиться на территории военной части без формы?</b>\n"
        "Ответ — Нет\n\n"
        "<b>23. Можно ли использовать для нападения на фуру личный транспорт, не относящийся к фракции или семье?</b>\n"
        "Ответ — Нет\n\n"
        "<b>24. Можно ли убивать игроков, которые просто проезжают мимо места проведения войны за территорию и не участвуют в ней?</b>\n"
        "Ответ — Нет\n\n"
        "<b>25. Требуется ли наличие игрока не ниже 6-го ранга среди грабителей инкассаторов?</b>\n"
        "Ответ — 6+"
    )


def get_gov_answers_texts():
    return [
        ("<b>1. Можно ли лидеру правительства принимать игроков по дню блата на 5 ранг?</b>\nОтвет — Нет, нельзя (правительство и служба спасения — максимум до 4 ранга).\n\n"
        "<b>2. Разрешено ли сотруднику переводиться в другую организацию, если на него на форуме висит открытая жалоба?</b>\nОтвет — Нет, это является весомой причиной для лидера отказать в переводе.\n\n"
        "<b>3. Обязательно ли отправлять скриншот созданной вакансии в специальную конференцию «Государственная волна» в VK?</b>\nОтвет — Да, это строго необходимо по коду беседы.\n\n"
        "<b>4. Можно ли использовать чат департамента для обсуждения текущих ролевых (РП) ситуаций между фракциями?</b>\nОтвет — Да, это входит в разрешенный функционал чата.\n\n"
        "<b>5. Разрешено ли кому-либо изменять минимальный порог вступления в подразделение ДПС (с 1 ранга)?</b>\nОтвет — Нет, этот минимальный порог не может быть изменен никем.\n\n"
        "<b>6. Можно ли лидеру Правительства делать переводы своих сотрудников в СГБ или Городскую больницу согласно общей таблице переводов?</b>\nОтвет — Нет, такие переводы отсутствуют.\n\n"
        "<b>7. Требуется ли подавать вакансию (/addvacancy) при проведении наборов в СГБ в день блата?</b>\nОтвет — Нет, СГБ освобождено от подачи вакансий, лидер может принимать по блату в любое разрешенное время.\n\n"
        "<b>8. Можно ли принимать или исключать сотрудников из подразделения через личные сообщения в игре без создания заявлений на форуме?</b>\nОтвет — Нет, прием и исключение осуществляются исключительно через специальные заявления на форуме.\n\n"
        "<b>9. Разрешено ли лидеру использовать государственную волну без каких-либо ограничений по времени вне отчетов?</b>\nОтвет — Да, гос. волна доступна для наборов без ограничений, но для отчета учитывается только с 09:00 до 21:00.\n\n"
        "<b>10. Можно ли через чат департамента сообщать коллегам о необходимости доставки боеприпасов?</b>\nОтвет — Да, это разрешено правилами пользования департаментом.\n\n"
        "<b>11. Допускается ли назначение на должность начальника подразделения сотрудника, который занимает 4 ранг во фракции?</b>\nОтвет — Нет, начальником может быть только сотрудник не ниже 7 ранга.\n\n"
        "<b>12. Можно ли перевестись из Армии в Службу спасения без потери своего текущего ранга?</b>\nОтвет — Да, без потери ранга (при наличии военного билета).\n\n"
        "<b>13. Разрешено ли указывать в вакансии через планшет время начала собеседования в нечетные минуты (например, в 15:15)?</b>\nОтвет — Нет, начало должно объявляться строго в чётное время (:00, :10, :20, :30, :40, :50).\n\n"
        "<b>14. Можно ли лидеру организации «блатить» (принимать/повышать) неограниченное количество игроков в течение дня блата?</b>\nОтвет — Да, количество игроков не ограничено в рамках разрешенных рангов.\n\n"
        "<b>15. Обязаны ли начальники или заместители подразделений следить за участием своих подчиненных в различных мероприятиях?</b>\nОтвет — Да, это прямая обязанность руководства подразделений.\n\n"
        "<b>16. Можно ли перевестись из Пожарной службы (Службы спасения) в Городскую больницу с повышением ранга?</b>\nОтвет — Да, при переводе в ГБ идет повышение на +1 ранг.\n\n"
        "<b>17. Разрешено ли использовать чат департамента для пиара открытых заявлений на официальном портале области?</b>\nОтвет — Да, это разрешено.\n\n"
        "<b>18. Можно ли вступить в подразделение «Отдел кадров» сотруднику, который имеет 3 ранг?</b>\nОтвет — Нет, в «Отдел кадров» можно вступить только с 5 ранга.\n\n"
        "<b>19. Разрешено ли проводить ночные наборы в обязательном порядке, если лидеру этого делать не хочется?</b>\nОтвет — Нет, эти наборы необязательны и проводятся исключительно по личной инициативе руководства.\n\n"
        "<b>20. Можно ли написать в государственную волну информацию о проведении какой-либо глобальной акции или мероприятия от организации?</b>\nОтвет — Да, проведение мероприятий и акций от организации разрешено в гос. волне.\n\n")
    ]


def get_answers_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            "Рп термины",
            callback_data="show_rp_answers",
        ),
        InlineKeyboardButton(
            "ОПГ",
            callback_data="show_opg_answers",
        ),
        InlineKeyboardButton(
            "Гос. структуры",
            callback_data="show_gov_answers",
        )
    )
    return keyboard


def get_rp_answers_text():
    return (
        "📖 <b>Ответы: РП-термины</b>\n\n"
        "<b>Что такое ДМ? (Deathmatch)</b>\n"
        "Ответ — убийство без причины\n\n"
        "<b>Что такое ДБ? (DriveBy)</b>\n"
        "Ответ — убийство машиной или с водительского места, убийство транспортом\n\n"
        "<b>Что такое СК? (Spawn Kill)</b>\n"
        "Ответ — убийство после появления, убийство на спавне\n\n"
        "<b>Что такое ТК? (TeamKill)</b>\n"
        "Ответ — убийство своих\n\n"
        "<b>Что такое РП? (RolePlay)</b>\n"
        "Ответ — игра по ролям\n\n"
        "<b>Что такое МГ?</b>\n"
        "Ответ — использование реальной информации в игре\n\n"
        "<b>Что такое ГМ?</b>\n"
        "Ответ — неуязвимость, режим бога\n\n"
        "<b>Что такое ПГ? (PowerGaming)</b>\n"
        "Ответ — воображение себя героем (драка с толпой или без оружия против вооруженного)\n\n"
        "<b>Что такое РК? (RevengeKill)</b>\n"
        "Ответ — возвращение на место смерти / месть\n\n"
        "<b>Что такое БХ?</b>\n"
        "Ответ — бег с прыжками для ускорения\n\n"
        "<b>Что такое УК?</b>\n"
        "Ответ — уголовный кодекс\n\n"
        "<b>Что такое АК? (Академический/Административный Кодекс)</b>\n"
        "Ответ — административный, академический кодекс\n\n"
        "<b>Что такое ЗЗ?</b>\n"
        "Ответ — зеленая зона (место, где запрещено насилие)\n\n"
        "<b>Что такое ФР? (FastReloading)</b>\n"
        "Ответ — баг с быстрой перезарядкой\n\n"
        "<b>Что такое ФМ? (FastMoving)</b>\n"
        "Ответ — баг с быстрым перемещением\n\n"
        "<b>Что такое СХ?</b>\n"
        "Ответ — чит на скорость\n\n"
        "<b>Что такое ФФ? (FriendlyFire)</b>\n"
        "Ответ — урон по своим\n\n"
        "<b>Что такое ЦК? (CharacterKill)</b>\n"
        "Ответ — убийство по рп с потерей персонажа\n\n"
        "<b>Что такое УРП? (UnRolePlay)</b>\n"
        "Ответ — уход от ролевой игры\n\n"
        "<b>Что такое ТДМ?</b>\n"
        "Ответ — командный бой\n\n"
        "<b>Что такое МДМ?</b>\n"
        "Ответ — массовое убийство без причины\n\n"
        "<b>Что такое ОРП? (OffRolePlay)</b>\n"
        "Ответ — уход от РП\n\n"
        "<b>Что такое ЕПП? (Exploiting Pathing)</b>\n"
        "Ответ — езда по полям\n\n"
        "<b>Что такое ПК? (PlayerKill)</b>\n"
        "Ответ — убийство по рп\n\n"
        "<b>Что такое ФЦК? (FractionCharacterKill)</b>\n"
        "Ответ — фракционное убийство персонажа\n\n"
        "<b>Что такое OOC? (Out Of Character)</b>\n"
        "Ответ — реальный мир\n\n"
        "<b>Что такое IC? (In Character)</b>\n"
        "Ответ — игровой мир"
    )


def get_factions_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        InlineKeyboardButton(
            "Правительство",
            callback_data="fact_Правительство",
        ),
        InlineKeyboardButton(
            "СГБ",
            callback_data="fact_СГБ",
        ),
        InlineKeyboardButton(
            "Полиция",
            callback_data="fact_Полиция",
        ),
        InlineKeyboardButton(
            "Больница",
            callback_data="fact_Больница",
        ),
        InlineKeyboardButton(
            "ТРК",
            callback_data="fact_ТРК",
        ),
        InlineKeyboardButton(
            "Армия",
            callback_data="fact_Армия",
        ),
        InlineKeyboardButton(
            "Служба Спасения",
            callback_data="fact_Служба Спасения",
        ),
        InlineKeyboardButton(
            "ОПГ Тамбовское",
            callback_data="fact_ОПГ Тамбовское",
        ),
        InlineKeyboardButton(
            "ОПГ Кавказское",
            callback_data="fact_ОПГ Кавказское",
        ),
        InlineKeyboardButton(
            "ОПГ Оффники",
            callback_data="fact_ОПГ Оффники",
        ),
        InlineKeyboardButton(
            "Рп термины",
            callback_data="fact_rp_terms",
        ),
        InlineKeyboardButton(
            "⬅️ Назад к правилам и ответам",
            callback_data="back_to_rules_menu",
        ),
    )

    return keyboard


def get_start_exam_keyboard():
    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "▶️ Начать",
            callback_data="start_test",
        ),
        InlineKeyboardButton(
            "🔄 Сменить фракцию",
            callback_data="change_faction",
        ),
    )

    return keyboard


# =========================
# Приветствие
# =========================

def show_main_welcome(chat_id):
    text = (
        "Приветствую. Данный бот создал Mike_Tysonn, "
        "чтобы подготовить тебя к обзвону.\n\n"
        "Перед началом нужно ознакомиться с правилами ввода ответа."
    )
    image_url = "https://raw.githubusercontent.com/ZHwwssx/tg-bot-/main/welcome_after_key.jpeg"

    try:
        bot.send_photo(
            chat_id,
            image_url,
            caption=text,
            reply_markup=get_rules_keyboard(),
        )
    except Exception:
        logger.exception("Ошибка показа приветствия в чате %s", chat_id)
        safe_send(
            chat_id,
            text,
            reply_markup=get_rules_keyboard(),
        )

# =========================
# Команда /start
# =========================

@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id

    with data_lock:
        user_data.pop(chat_id, None)
        waiting_for_key.add(chat_id)

    safe_send(
        chat_id,
        "🔐 Введите ключ доступа для запуска бота:",
    )


@bot.message_handler(commands=["cancel"])
def cancel_command(message):
    chat_id = message.chat.id

    with data_lock:
        user_data.pop(chat_id, None)

    if chat_id in waiting_for_key:
        safe_send(
            chat_id,
            "Сначала введите ключ доступа. Для повторного запуска используйте /start",
        )
        return

    safe_send(
        chat_id,
        "📁 Выберите фракцию для подготовки:",
        reply_markup=get_factions_keyboard(),
    )


# =========================
# Проверка ключа
# =========================

@bot.message_handler(
    func=lambda message: message.chat.id in waiting_for_key
)
def handle_key_input(message):
    chat_id = message.chat.id

    # Защита от фотографий, стикеров и сообщений без текста.
    entered_key = (message.text or "").strip().lower()

    safe_delete(
        chat_id,
        message.message_id,
    )

    if not entered_key:
        safe_send(
            chat_id,
            "Пожалуйста, отправьте ключ текстом:",
        )
        return

    with data_lock:
        if entered_key == UNIVERSAL_KEY:
            waiting_for_key.discard(chat_id)
            access_granted = True

        elif (
            entered_key in VALID_KEYS
            and entered_key not in used_keys
        ):
            used_keys.add(entered_key)
            waiting_for_key.discard(chat_id)
            access_granted = True

        else:
            access_granted = False

    if access_granted:
        show_main_welcome(chat_id)
    else:
        safe_send(
            chat_id,
            "❌ Неверный ключ или он уже использован. "
            "Попробуйте еще раз:",
        )


# =========================
# Inline-кнопки
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data or ""

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        logger.exception("Ошибка callback query")

    # Вернуться к меню правил и ответов
    if data == "back_to_rules_menu":
        safe_delete(chat_id, message_id)
        safe_send(
            chat_id,
            "Выберите раздел:",
            reply_markup=get_rules_keyboard(),
        )
        return

    # Показать правила
    if data == "show_rules":
        safe_delete(chat_id, message_id)

        rules_text = (
            "📌 <b>Правила ввода ответа:</b>\n\n"
            "• Для ответа «нет»: "
            "нет, нельзя, не можно, запрещено.\n\n"
            "• Для ответа «да»: "
            "да, можно, конечно, разрешено.\n\n"
            "• Для числовых ответов используйте формат из правил.\n\n"
            "👇 Нажмите кнопку ниже, "
            "чтобы перейти к выбору фракции:"
        )

        markup = InlineKeyboardMarkup()

        markup.add(
            InlineKeyboardButton(
                "Перейти к фракциям",
                callback_data="go_to_factions",
            )
        )

        safe_send(
            chat_id,
            rules_text,
            reply_markup=markup,
            parse_mode="HTML",
        )

        return

    # Просмотр правильных ответов
    if data == "show_answers":
        safe_delete(chat_id, message_id)
        safe_send(
            chat_id,
            "Выбери раздел для ответов:",
            reply_markup=get_answers_keyboard(),
        )
        return

    if data == "show_rp_answers":
        safe_delete(chat_id, message_id)
        safe_send(
            chat_id,
            get_rp_answers_text(),
            parse_mode="HTML",
        )
        return

    if data == "show_opg_answers":
        safe_delete(chat_id, message_id)
        safe_send(
            chat_id,
            get_opg_answers_text(),
            parse_mode="HTML",
        )
        return

    if data == "show_gov_answers":
        safe_delete(chat_id, message_id)
        for answers_text in get_gov_answers_texts():
            safe_send(
                chat_id,
                answers_text,
                parse_mode="HTML",
            )
        return

    # Выбор фракции
    if data in {
        "go_to_factions",
        "change_faction",
        "back_to_menu",
    }:
        with data_lock:
            user_data.pop(chat_id, None)

        safe_delete(chat_id, message_id)

        safe_send(
            chat_id,
            "📁 Выберите фракцию для подготовки:",
            reply_markup=get_factions_keyboard(),
        )

        return

    # Нажата конкретная фракция
    if data.startswith("fact_"):
        faction_name = data.split("_", 1)[1]

        government_factions = {
            "Правительство",
            "СГБ",
            "Полиция",
            "Больница",
            "ТРК",
            "Армия",
            "Служба Спасения",
        }

        # Поддерживаем и новые, и уже отправленные старые кнопки.
        if faction_name in {"rp_terms", "Рп термины"}:
            questions = RP_QUESTIONS
            faction_name = "Рп термины"
        elif faction_name in government_factions:
            questions = GOV_QUESTIONS
        else:
            questions = CRIME_QUESTIONS

        # Каждый новый обзвон получает свой случайный порядок вопросов.
        questions = list(questions)
        random.shuffle(questions)

        with data_lock:
            user_data[chat_id] = {
                "questions": questions,
                "index": 0,
                "errors": [],
                "last_question_msg_id": None,
                "started": False,
                "processing": False,
            }

        safe_delete(chat_id, message_id)

        safe_send(
            chat_id,
            f"Выбрана фракция — {faction_name}.\n"
            "Начинаем обзвон?",
            reply_markup=get_start_exam_keyboard(),
        )

        return

    # Начать тест
    if data == "start_test":
        with data_lock:
            exam = user_data.get(chat_id)

            if not exam:
                return

            if exam.get("started"):
                return

            exam["started"] = True

        safe_delete(chat_id, message_id)
        send_next_question(chat_id)


# =========================
# Следующий вопрос
# =========================

def send_next_question(chat_id):
    with data_lock:
        exam = user_data.get(chat_id)

        if not exam:
            return

        index = exam["index"]
        questions = exam["questions"]

    if index >= len(questions):
        finish_exam(chat_id)
        return

    question_text = (
        f"Вопрос {index + 1}/{len(questions)}:\n"
        f"{questions[index]['q']}"
    )

    sent_message = safe_send(
        chat_id,
        question_text,
    )

    if sent_message:
        with data_lock:
            if chat_id in user_data:
                user_data[chat_id][
                    "last_question_msg_id"
                ] = sent_message.message_id


# =========================
# Обработка ответа
# =========================

@bot.message_handler(
    func=lambda message: (
        message.chat.id in user_data
        and user_data[message.chat.id].get(
            "started",
            False,
        )
    )
)
def handle_answer(message):
    chat_id = message.chat.id

    if not message.text:
        safe_send(
            chat_id,
            "Пожалуйста, отправьте текстовый ответ.",
        )
        return

    # Блокируем повторную обработку,
    # если пользователь отправил два ответа подряд.
    with data_lock:
        exam = user_data.get(chat_id)

        if not exam:
            return

        if exam.get("processing"):
            return

        index = exam["index"]
        questions = exam["questions"]

        if index >= len(questions):
            return

        exam["processing"] = True

    raw_text = message.text.lower().strip()

    user_clean = raw_text.strip(
        string.punctuation + " "
    )

    correct_variants = questions[index]["valid"]

    safe_delete(
        chat_id,
        message.message_id,
    )

    is_correct = (
        user_clean in correct_variants
        or raw_text in correct_variants
    )

    if is_correct:
        status_message = safe_send(
            chat_id,
            "Верно 🟢, переходим дальше.",
        )

    else:
        error_info = {
            "question": questions[index]["q"],
            "user_ans": message.text,
            "correct_ans": questions[index]["ans_text"],
        }

        with data_lock:
            exam = user_data.get(chat_id)

            if exam:
                exam["errors"].append(error_info)

        status_message = safe_send(
            chat_id,
            "Неверно 🔴 Ошибка засчитана. "
            "Количество ошибок будет подсчитано "
            "в конце обзвона.",
        )

    with data_lock:
        exam = user_data.get(chat_id)

        if exam:
            last_question_message_id = exam.get(
                "last_question_msg_id"
            )
        else:
            last_question_message_id = None

    if last_question_message_id:
        safe_delete(
            chat_id,
            last_question_message_id,
        )

    time.sleep(1.2)

    if status_message:
        safe_delete(
            chat_id,
            status_message.message_id,
        )

    with data_lock:
        exam = user_data.get(chat_id)

        if not exam:
            return

        exam["index"] += 1
        exam["processing"] = False

    send_next_question(chat_id)


# =========================
# Обработчик остальных сообщений
# =========================

@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    chat_id = message.chat.id

    if chat_id in waiting_for_key:
        return

    with data_lock:
        is_active = (
            chat_id in user_data
            and user_data[chat_id].get(
                "started",
                False,
            )
        )

    if not is_active:
        safe_send(
            chat_id,
            "Для начала работы введите /start",
        )


# =========================
# Завершение теста
# =========================

def finish_exam(chat_id):
    with data_lock:
        exam = user_data.pop(chat_id, None)

    if not exam:
        return

    errors = exam["errors"]
    errors_count = len(errors)

    if errors_count <= 1:
        verdict = "Вы прошли обзвон 🎉"
    elif errors_count in (2, 3):
        verdict = "Чуть-чуть не хватило"
    elif errors_count in (4, 5):
        verdict = "Стоит подучить правила"
    else:
        verdict = "Тебе явно нужно на форум"

    report = (
        f"{verdict}\n"
        f"Ошибок — {errors_count}\n\n"
    )

    for error in errors:
        report += (
            f"• {error['question']}\n"
            f"Ваш ответ — {error['user_ans']}.\n\n"
            f"Верный ответ — {error['correct_ans']}\n\n"
        )

    report += (
        "Согласно форуму.\n"
        "С уважением, Mike_Tysonn"
    )

    safe_send(
        chat_id,
        report,
    )

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton(
            "🔄 Выбрать другую фракцию",
            callback_data="back_to_menu",
        )
    )

    safe_send(
        chat_id,
        "Хотите пройти тест еще раз?",
        reply_markup=markup,
    )


# =========================
# Запуск
# =========================

if __name__ == "__main__":
    # Flask должен работать в обычном потоке, иначе Render завершит
    # процесс сразу после установки Telegram webhook.
    threading.Thread(
        target=run_flask,
        daemon=False,
    ).start()

    logger.info("Бот запущен")

    external_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("PUBLIC_URL")
    )

    if external_url:
        webhook_url = f"{external_url.rstrip('/')}/telegram-webhook"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        logger.info("Telegram webhook включён: %s", webhook_url)
    else:
        logger.warning(
            "RENDER_EXTERNAL_URL не найден, запускаем polling для локального режима"
        )
        bot.infinity_polling(skip_pending=True)
