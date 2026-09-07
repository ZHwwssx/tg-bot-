import html
import logging
import os
import random
import re
import uuid
import threading
import time

import telebot
from flask import Flask, request
from telebot import types


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Укажите TELEGRAM_BOT_TOKEN или BOT_TOKEN в Environment Variables Render")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

WELCOME_IMAGE_PATH = os.path.join(BASE_DIR, "welcome.jpg")
WELCOME_CAPTION = (
    "<b>Приветствую!</b>\n\n"
    "Бот создан для обзвонов.\n"
    "Данный бот в версии 1.0.0.0.\n"
    "Далее будут улучшения.\n\n"
    "Ботом занималась команда <b>Hareson</b>."
)


RULES = {
    "basic": {
        "title": "Основное",
        "rules": [
            "Суммы выкупа за похищение:\nПравительство:\nГубернатор — 250.000\nЗаместители Губернатора — 100.000\nСотрудники фракции — 25.000\n\nПолиция:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудники фракции — 20.000\n\nСГБ:\nНачальник — 200.000\nЗаместители Начальника — 100.000\nСотрудники фракции — 25.000\n\nВоинская часть:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудника фракции — 20.000\n\nМедиацентр «Темп»:\nДиректор — 150.000\nЗаместители Директора — 75.000\nСотрудники фракции — 20.000\n\nСлужба Спасения:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудники фракции — 20.000",
            "Разрешённое оружие:\nПистолет Макарова\nПистолет с глушителем\nAK47\nДробовик\nВинтовка\nБита\nКулаки\nАК74\nКастет",
            "Воздушный груз появляется в 14:40 и 19:40.",
            "Локации AirDrop: 10.",
            "Ориентировочные причины возврата территории:\n5.1. Больше трех игроков, заблокированных за использование стороннего ПО с одной ОПГ;\n5.2. Массовые нарушения состава (8+ человек);\n5.3. Запрещено продавать/покупать территории, специально отдавать территории, а также заключать перемирие с вражеской ОПГ;\n5.4. Захват территории у ОПГ в морозе;\n5.5. Массовый выход с сервера больше половины от первоначального состава одной ОПГ.\n5.6. Забитие войны за территории не по времени (в четные часы).",
        ],
    },
    "airdrop": {
        "title": "Аир Дроп (AirDrop)",
        "rules": [
            "Запрещено использовать любые баги стрельбы (+С, отводы, слайды) | Тюрьма 30 минут",
            "Запрещено использовать аптечки, наркотики или броню в бою (во время перестрелки) | Тюрьма 30 минут",
            "Запрещено использовать стороннее ПО (читы) | Перманентная блокировка аккаунта",
            "Запрещено находиться на территории AirDrop игрокам, которые не состоят в ОПГ или не участвуют в мероприятии | Тюрьма 30 минут",
            "Запрещено использовать транспорт для тарана игроков или создания помехи (каблук/ДБ) | Тюрьма 30-60 минут",
            "Запрещено возвращаться на место смерти (РК) с целью мести или повторного участия в этом же сражении | Тюрьма 30 минут",
            "Запрещено уходить в AFK во время перестрелки или выходить из игры от смерти | Тюрьма 30 минут",
            "Запрещено использовать маски во время захвата груза (или наоборот, обязательное ношение — в зависимости от конкретных правок сервера) | Тюрьма 20 минут",
            "Запрещено залетать на крыши и труднодоступные высотки с помощью вертолетов или багов мода | Предупреждение (варн)",
            "Запрещено наносить урон игрокам до начала таймера или после окончания мероприятия | Тюрьма 60 минут",
            "Воздушный груз появляется в 14:40 и 19:40.",
            "Локации AirDrop: 10.",
        ],
    },
    "rp_terms": {
        "title": "РП термины",
        "rules": [
            "ДМ (Deathmatch) — Убийство без причины.",
            "ДБ (DriveBy) — Убийство с машины (или машиной).",
            "СК (Spawn Kill) — Убийство при появлении персонажа.",
            "ТК (TeamKill) — Убийство своих союзников.",
            "РП (RolePlay) — Игра по ролям, где каждый игрок должен соблюдать свою роль.",
            "МГ (MetaGaming) — Использование информации, полученной вне игры (из реального мира), в игровом процессе (например, из чатов ООС*).",
            "ГМ (GodMode) — становление персонажа неуязвимым.",
            "ПГ (PowerGaming) — Изображение себя как героя, например, когда у тебя нет оружия, но ты идешь на вооруженного противника, или когда пять человек нападают на одного.",
            "РК (RevengeKill) — Возвращение на место, где тебя убили; убийство с целью мести; неоднократное убийство одного и того же игрока.",
            "БХ (BunnyHop) — Нон-РП бег с прыжками, который используется для ускорения передвижения.",
            "УК (Уголовный Кодекс) — Кодекс законов, регулирующий действия в игре.",
            "АК (Академический Кодекс) — Кодекс, регулирующий образовательный процесс или поведение в образовательных учреждениях (или аналог).",
            "ЗЗ (Зеленая Зона) — Общественные места, где запрещено совершать агрессивные действия, например, площади у мэрии, вокзалы, больницы.",
            "ФР (FastReloading) — Баг с быстрой перезарядкой.",
            "ФМ (FastMoving) — Баг с быстрым перемещением.",
            "СХ (SH) — Спидхак, чит на быстрое перемещение (SpeedHack).",
            "ФФ (FriendlyFire) — Стрельба по своим союзникам, обычно без намерения убить, а с целью причинить минимальный урон.",
            "ЦК (CharacterKill) — Убийство персонажа по РП, запрещено на сервере.",
            "УРП (UnRolePlay) — Уход от РП, действия, которые не соответствуют роли персонажа.",
            "ТДМ (Team DeathMatch) — Массированное убийство на основе команд.",
            "МДМ (Mass DeathMatch) — Массовое убийство без причины.",
            "ОРП (OffRolePlay) — Уход от РП.",
            "ЕПП (Exploiting Pathing) — Езда по полям или на участках, где это запрещено.",
            "ПК (PlayerKill) — Убийство другого игрока, соответствующее РП.",
            "ФЦК (FractionCharacterKill) — Убийство персонажа по фракционным мотивам.",
        ],
    },
    "war": {
        "title": "Война за территорию",
        "rules": [
            "Война за территории проходят в Эдово (45 территории) и Лыткарино (33 территории). Всего 78 территорий;",
            "Запрещено афк во время стрельбы (более 15 секунд) | Отключение от сервера",
            "Запрещено сбивать анимацию аптечек/препаратов/поднятия оружия/употребления еды | Тюрьма 20 минут",
            "Запрещено писать не по теме (оффтоп) в общий чат нелегальных структур (/gg) | Блокировка чата 20 минут",
            "Запрещено использовать баллончик и огнетушитель | Тюрьма 60 минут",
            "Запрещено устраивать любую помеху (например, ДМ, ДБ, использование спец. средств полиции) члену банды в течение 10 минут до начала захвата территории с целью уменьшения шансов банды забрать территорию (антикапт) | Тюрьма 60 минут, при повторе предупреждение на игровой аккаунт",
            "Запрещено иметь пинг свыше 200 | Отключение от сервера",
            "Запрещено во время стрельбы использовать препараты/аптечки/еду (в бою) | Тюрьма 10 минут",
            "Запрещено находиться вне рабочей форме или форме не соответствующему дресс-коду | Тюрьма 10 минут",
            "Запрещено стрелять до начала боя в сторону игроков | Тюрьма 60 минут",
            "Разрешённое оружие на войне за территорию:\nПистолет Макарова\nПистолет с глушителем\nAK47\nДробовик\nВинтовка\nБита\nКулаки\nАК74\nКастет",
            "Запрещено использовать стороннее ПО | Перманентная блокировка всех аккаунтов + блокировка устройства",
            "Запрещено заходить в любые интерьеры | Тюрьма 10 минут",
            "Запрещено надевать маску во время капта | Тюрьма на 10 минут",
            "Запрещено стрелять/убивать игроков, которые проезжают через территорию каптов и не участвуют в капте | Тюрьма 90 минут",
            "Запрещено провоцировать вражескую группировку | Блокировка чата на 10 минут",
            "Запрещён багоюз любого типа | Тюрьма на 60 минут, при повторе предупреждение на игровой аккаунт",
            "Запрещено занимать высотки с помощью вертолета/бага | Предупреждение на игровой аккаунт",
            "Запрещено третьей ОПГ, сотрудникам городской больницы и другим игрокам, не связанных с каптом, вмешиваться в войну за территорию | Предупреждение на игровой аккаунт",
            "Запрещено СКшить в жилых зонах гетто — внутри подъездов и домов, а также у входа в них | Тюрьма на 60 минут",
            "Запрещено использовать стороннее оружие от пункта 4.7 | Тюрьма 10 минут",
            "Запрещено занимать крыши крупных домов при помощи тюнинга авто/мото/джетпака | Тюрьма на 20 минут",
            "Запрещён выход из гетто (за территории) | Тюрьма 20 минут",
            "Запрещена накрутка счётчика убийств (киллов) | Предупреждение на игровой аккаунт",
            "Запрещено менять цвет ника с фракционного | Отключение от сервера",
            "Запрещено уходить в AFK или отключаться из игры от смерти | Тюрьма 10 минут",
            "Запрещено продавать/покупать территории, отдавать территории, а также заключать перемирие с вражеской ОПГ | Выговор лидеру",
            "Запрещено увольнять/понижать/повышать/принимать/выдавать выговоры людям на капте | Выговор лидеру",
            "Запрещено делать захват территории ОПГ которая в морозе | Выговор лидеру",
            "Запрещено иметь больше трех игроков, заблокированных за использование стороннего ПО с одной ОПГ | Выговор лидеру",
        ],
    },
    "kidnap": {
        "title": "Похищение",
        "rules": [
            "Запрещен ПГ (превышение возможностей персонажа): нельзя пытаться вырваться или вступать в драку, если похитителей больше трех либо хотя бы один из них вооружен | Наказание по правилам сервера",
            "Запрещено называть похитителей по именам, раскрывать их принадлежность к организации и вести лишние разговоры | Наказание по правилам сервера",
            "Запрещено уходить в АФК или выходить из игры во время похищения, чтобы избежать смерти | Наказание по правилам сервера",
            "Запрещено провоцировать преступников: оскорблять их, грубить, дерзить или отказываться подчиняться | Наказание по правилам сервера",
            "Запрещено ничего делать пока персонаж оглушен: писать, смеяться или кричать | Наказание по правилам сервера",
            "Запрещено говорить с кляпом во рту | Наказание по правилам сервера",
            "Запрещено задерживать похитителей сотрудникам госструктур, пока они удерживают заложника | Наказание по правилам сервера",
            "Запрещено подбегать к заложнику или совершать в отношении него какие-либо действия | Наказание по правилам сервера",
            "Запрещено стрелять в сторону заложника, в том числе по похитителям или машине, в которой он находится | Наказание по правилам сервера",
            "Запрещено переговорщикам надевать маски и открывать огонь | Наказание по правилам сервера",
            "Запрещено убивать, обстреливать и похищать переговорщиков | Наказание по правилам сервера",
            "Запрещено похищать в местах скопления людей и рядом с сотрудниками полиции (разрешено только в малолюдных местах) | Наказание по правилам сервера",
            "Запрещено похищать в зеленой зоне (ЗЗ) | Наказание по правилам сервера",
            "Запрещено похищать игроков на рабочем месте, во время выполнения начальных работ, прохождения собеседований или участия в РП-ситуациях | Наказание по правилам сервера",
            "Запрещено удерживать заложника в квартире, доме, на базе похитителей или в местах спавна | Наказание по правилам сервера",
            "Запрещено похищать медиков, гражданских и переговорщиков | Наказание по правилам сервера",
            "Запрещено отыгрывать убийство лидеров | Наказание по правилам сервера",
            "Запрещено убивать заложника после получения выкупа | Наказание по правилам сервера",
            "Суммы выкупа за похищение:\nПравительство:\nГубернатор — 250.000\nЗаместители Губернатора — 100.000\nСотрудники фракции — 25.000\n\nПолиция:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудники фракции — 20.000\n\nСГБ:\nНачальник — 200.000\nЗаместители Начальника — 100.000\nСотрудники фракции — 25.000\n\nВоинская часть:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудника фракции — 20.000\n\nМедиацентр «Темп»:\nДиректор — 150.000\nЗаместители Директора — 75.000\nСотрудники фракции — 20.000\n\nСлужба Спасения:\nПолковник — 150.000\nЗаместители Полковника — 75.000\nСотрудники фракции — 20.000",
        ],
    },
    "base": {
        "title": "Нападение на военную базу",
        "rules": [
            "Запрещено находиться на ВЧ без маски | Тюрьма 30 минут",
            "Запрещено забегать в интерьеры к военнослужащим | Тюрьма 30 минут / Предупреждение",
            "Запрещено использование аптечки/препаратов в бою | Тюрьма 30 минут",
            "Запрещено ДМ вне территории военной базы (не военнослужащих) | Тюрьма 90 минут",
            "Запрещено нахождение на военной части вне рабочей формы | Тюрьма 10 минут",
            "Запрещено использовать анимации, помогающие избежать смерти | Тюрьма 30 минут",
            "Запрещено нападение менее 5-ти человек | Тюрьма 30 минут",
        ],
    },
    "cash": {
        "title": "Ограбление инкассаторов",
        "rules": [
            "Запрещено грабить инкассаторов с 00:00 до 06:00 по серверному времени | Тюрьма 60 минут",
            "Запрещено заранее перекрывать дорогу транспортом или устанавливать блокпосты | Тюрьма 30 минут / Предупреждение",
            "Запрещено подрезать машину инкассаторов «по пингу» | Тюрьма 30 минут",
            "Запрещено стрелять из окна движущегося автомобиля по машине инкассаторов или по самим инкассаторам | Предупреждение",
            "Запрещено использовать недоработки мода и баги игры | Тюрьма 30 минут",
            "Запрещено использовать препараты во время перестрелки в ходе ограбления | Тюрьма 30 минут",
            "Запрещено выходить из игры во время ограбления | Тюрьма 30 минут / Предупреждение",
            "Запрещено забегать в расположенные рядом магазины или интерьеры и лечиться в них | Тюрьма 60 минут",
            "Запрещено ремонтировать свой транспорт после начала ограбления | Тюрьма 60 минут",
            "Запрещено участвовать в ограблении без маски или избивать инкассаторов голыми руками | Тюрьма 60–90 минут / Предупреждение",
        ],
    },
    "trucks": {
        "title": "Нападение для угона фур с материалами",
        "rules": [
            "Запрещено ДМить на складе и шахте ОПГ и сотрудников гос. структур | Тюрьма 90 минут",
            "Запрещен ДМ игроков на шахте | Предупреждение (при массовом — бан 1-3)",
            "Запрещено брать танк | Предупреждение",
            "Запрещено нападать на фуру вне мест, разрешенных правилами | Тюрьма 90 минут",
            "Запрещено создавать помеху другим при въезде на склад (заставлять проходы фурами) | Кик",
        ],
    },

    "gov_wave": {
        "title": "Правила государственной волны и ночных наборов",
        "rules": [
            "Запрещено занимать государственную волну (/gov) без соблюдения установленного минимального интервала времени | Блокировка чата / Выговор лидеру",
            "Запрещено писать бред, рекламу, MG или оффтоп в государственную волну | Блокировка чата 30 минут / Предупреждение",
            "Запрещено проводить ночные наборы с нарушением установленного времени (в неразрешенные часы) | Выговор лидеру",
            "Запрещено подавать вещание в госволну без предварительного оповещения в рацию департамента (/d) за 10-15 минут | Блокировка чата 20 минут",
            "Запрещено проводить собеседование в госволну во время проведения глобальных мероприятий или терактов | Выговор лидеру",
            "Запрещено использовать неподходящие теги или оформление в строках вещания | Блокировка чата 20 минут",
        ],
    },
    "department": {
        "title": "Правила пользования департаментом (/d)",
        "rules": [
            "Запрещено использовать рацию департамента (/d) не по назначению, в личных целях или для купли-продажи | Блокировка чата 30 минут",
            "Запрещено нарушать правила тегов организаций при общении в департаменте | Блокировка чата 20 минут",
            "Запрещено использовать мат, оскорбления, капс и флуд в рацию департамента | Блокировка чата 30–60 минут",
            "Запрещено перекрикивать коллег или забивать волну лишней информацией при важных перехватах/ситуациях | Блокировка чата 20 минут",
            "Запрещено разжигать конфликты между государственными структурами через рацию департамента | Блокировка чата 30 минут / Предупреждение",
            "Запрещено игнорировать запросы от других государственных организаций при отсутствии веских причин | Выговор сотруднику",
        ],
    },
    "transfers": {
        "title": "Система переводов государственных организаций",
        "rules": [
            "Запрещено осуществлять перевод в другую организацию без получения 2 официальных разрешений (от руководства своей фракции и принимающей стороны) | Отказ в переводе / Увольнение",
            "Запрещено вводить лидеров или заместителей в заблуждение при подаче заявления на перевод | Черный список организации",
            "Запрещено переводиться сотрудникам младше 5 ранга (за исключением редких разрешенных исключений фракций) | Отказ в переводе",
            "Запрещено переводиться сотрудникам с имеющимися активными выговорами в личном деле | Отказ в переводе",
            "Запрещено переводиться с целью дальнейшего слива лидера, склада или состава организации | Черный список организации навсегда",
            "Запрещено назойливо выпрашивать или флудить в рацию/соцсети с просьбой о проверке заявления на перевод | Отказ заявления",
        ],
    },
    "leaders": {
        "title": "Правила и обязанности лидеров",
        "rules": [
            "Запрещено игнорировать суточную норму онлайна и минимальное количество проведенных собеседований за день | Выговор / Снят с поста",
            "Запрещено принимать, повышать или увольнять игроков по блату (за деньги, по знакомству или без обязательных отчетов) | Снят с поста лидера + Варн",
            "Запрещено проявлять неадекватное поведение в игре, мессенджерах, соцсетях и на форуме, а также разжигать любые конфликты | Выговор / Строгий выговор / Снят",
            "Запрещено переносить форумные разделы или изменять внутреннюю систему повышения без предварительного согласования с администрацией | Выговор лидеру",
            "Запрещено игнорировать жалобы игроков и заявления на форуме дольше установленного лимита времени (24 часа) | Предупреждение / Выговор",
            "Запрещено удалять доказательства нарушений из отчетов или жалоб до истечения срока хранения (3 дня) | Выговор лидеру",
            "Запрещено выдавать ранги сотрудникам без заполненной антиблат-системы | Выговор лидеру",
            "Запрещено конфликтовать с другими лидерами или провоцировать составы других фракций | Выговор лидеру",
        ],
    },
    "general": {
        "title": "Общие правила государственных структур",
        "rules": [
            "Запрещено нарушать базовые правила проекта (DM, DB, TK, MG, PG) | Тюрьма / Варн / Бан по нормативам сервера",
            "Запрещено использовать рабочее положение, форму и должностные полномочия в личных целях | Увольнение / Варн",
            "Запрещено находиться на рынке, в казино или на развлекательных мероприятиях в рабочее время в форме | Тюрьма 30 минут / Увольнение",
            "Запрещено носить запрещенные аксессуары, татуировки и элементы одежды, не соответствующие строгому дресс-коду госструктуры | Тюрьма 10 минут / Выговор",
            "Запрещено игнорировать приказы старшего состава или вышестоящего руководства во время выполнения служебных обязанностей | Выговор / Увольнение",
            "Запрещен намеренный отказ или уход от плановых/внеплановых проверок госструктур | Штраф 100 000 игровой валюты / Выговор лидеру",
            "Запрещен выход из игры или уход в AFK более чем на 5 минут во время проверки структуры | Штраф 10 000 игровой валюты + возможное увольнение",
            "Запрещено приходить на построение для проверки без должного строя или с оружием в руках | Штраф от 2 000 до 50 000 игровой валюты",
            "Запрещено брать взятки без соблюдения строгих процессуальных и РП-условий (где это допустимо) | Варн / Увольнение",
        ],
    },

}


@app.get("/")
def health_check():
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


def start_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("Пройти текстовый обзвон", callback_data="menu:interview"),
        types.InlineKeyboardButton("Правила", callback_data="menu:rules"),
    )
    return keyboard



INTERVIEW_RULE_SECTIONS = ("war", "kidnap", "base", "cash", "trucks", "airdrop")
OPG_INTERVIEW_KEYS = {"tambov", "caucasian", "offniki"}
INTERVIEW_QUESTION_COUNT = 20
INTERVIEW_SESSIONS = {}


def build_interview_questions(level=None):
    questions = []
    for section in INTERVIEW_RULE_SECTIONS:
        for rule in RULES[section]["rules"]:
            if " | " not in rule:
                continue
            statement, punishment = rule.split(" | ", 1)
            statement = re.sub(r"^Запрещ(?:ено|ен|ена|ён|ены)\s+", "", statement)
            questions.append({
                "question": f"Разрешено ли {html.escape(statement)}?",
                "punishment": html.escape(punishment),
                "answer_type": "no",
            })

    questions.extend([
        {
            "question": "В какое время проводятся капты в будние и выходные дни?",
            "punishment": "",
            "answer_type": "cap_schedule",
            "expected_numbers": [13, 15, 17, 19, 21, 11, 13, 15, 17, 19, 21],
        },
        {
            "question": "В какое время разрешено нападать на военную часть?",
            "punishment": "",
            "answer_type": "time_range",
            "expected_times": ["08:00", "22:00"],
        },
        {
            "question": "Сколько каптов проводится в будние и выходные дни?",
            "punishment": "",
            "answer_type": "number_sequence",
            "expected_numbers": [5, 6],
        },
        {
            "question": "В какое время падает AirDrop?",
            "punishment": "",
            "answer_type": "time_list",
            "expected_times": ["14:40", "19:40"],
        },
        {
            "question": "Сколько локаций AirDrop?",
            "punishment": "",
            "answer_type": "number_sequence",
            "expected_numbers": [10],
        },
        {
            "question": "Сколько минимальных нападающих нужно для нападения на военную часть?",
            "punishment": "",
            "answer_type": "number_sequence",
            "expected_numbers": [5],
        },
    ])
    return questions


def interview_level_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("Обзвон на заместителя", callback_data="interview:level:deputy"),
        types.InlineKeyboardButton("Обзвон на лидера", callback_data="interview:level:leader"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:interview"),
    )
    return keyboard


def interview_answer_keyboard(session_id, index):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("❌ Завершить обзвон", callback_data="interview:cancel"))
    return keyboard


def interview_result_keyboard(level):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔄 Пройти заново", callback_data=f"interview:level:{level}"),
        types.InlineKeyboardButton("⬅️ К выбору организации", callback_data="menu:interview"),
    )
    return keyboard


def start_interview_session(chat_id, level):
    question_pool = build_interview_questions(level)
    amount = min(INTERVIEW_QUESTION_COUNT, len(question_pool))
    selected_questions = random.sample(question_pool, amount)
    session = {
        "id": uuid.uuid4().hex[:8],
        "level": level,
        "questions": selected_questions,
        "current": 0,
        "score": 0,
    }
    INTERVIEW_SESSIONS[chat_id] = session
    return session


def interview_question_text(session):
    questions = session["questions"]
    index = session["current"]
    item = questions[index]
    level_title = "заместителя" if session["level"] == "deputy" else "лидера"
    text = (
        f"<b>Обзвон на {level_title}</b>\n\n"
        f"{item['question']}\n\n"
        f"<i>Вопрос {index + 1} из {len(questions)}</i>\n\n"
        "<i>Напишите ответ сообщением. Например: «да», «нет», «можно», "
        "«нельзя», «разрешено», «запрещено».</i>"
    )
    if session["level"] == "leader" and item["punishment"]:
        text += "\n\n<i>После ответа бот покажет наказание.</i>"
    return text


def show_interview_question(call, session, prefix=None):
    text = interview_question_text(session)
    if prefix:
        text = f"{prefix}\n\n{text}"
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=interview_answer_keyboard(session["id"], session["current"]),
        parse_mode="HTML",
    )


def send_interview_question(chat_id, session):
    bot.send_message(
        chat_id,
        interview_question_text(session),
        reply_markup=interview_answer_keyboard(session["id"], session["current"]),
        parse_mode="HTML",
    )


def normalize_interview_answer(text):
    text = (text or "").lower().replace("ё", "е")
    return re.sub(r"[^а-яa-z0-9:]+", " ", text).strip()


def extract_answer_numbers(text):
    normalized = normalize_interview_answer(text)
    number_words = {
        "ноль": "0", "один": "1", "два": "2", "три": "3", "четыре": "4",
        "пять": "5", "шесть": "6", "семь": "7", "восемь": "8", "девять": "9",
        "десять": "10",
    }
    for word, number in number_words.items():
        normalized = re.sub(rf"\b{word}\b", number, normalized)
    return [int(value) for value in re.findall(r"\b\d+\b", normalized)]


def extract_answer_times(text):
    normalized = (text or "").lower().replace("ё", "е")
    raw_times = re.findall(r"(?<!\d)(\d{1,2})(?::(\d{2}))?(?!\d)", normalized)
    times = []
    for hours, minutes in raw_times:
        times.append(f"{int(hours):02d}:{int(minutes or 0):02d}")
    return times


def classify_interview_answer(text):
    normalized = normalize_interview_answer(text)
    if not normalized:
        return None

    negative = (
        normalized in {"нет", "не", "нельзя", "запрещено", "запрещен", "запрещена", "ни в коем случае"}
        or "не разреш" in normalized
        or "запрещ" in normalized
        or "нельзя" in normalized
        or re.search(r"\bнет\b", normalized)
    )
    if negative:
        return "no"

    positive = (
        normalized in {"да", "конечно", "разрешено", "можно", "естественно", "разрешается", "допустимо"}
        or "разреш" in normalized
        or re.search(r"\bможно\b", normalized)
        or "конечно" in normalized
        or "естественно" in normalized
    )
    if positive:
        return "yes"
    return None


def is_interview_answer_correct(item, raw_answer):
    if item["answer_type"] == "no":
        return classify_interview_answer(raw_answer) == "no"
    if item["answer_type"] in {"number_sequence", "cap_schedule"}:
        return extract_answer_numbers(raw_answer) == item["expected_numbers"]
    if item["answer_type"] in {"time_list", "time_range"}:
        return extract_answer_times(raw_answer) == item["expected_times"]
    return False


def expected_interview_answer_text(item):
    if item["answer_type"] == "cap_schedule":
        return "Будние: 13, 15, 17, 19, 21; выходные: 11, 13, 15, 17, 19, 21"
    if item["answer_type"] == "time_range":
        return "с 08:00 до 22:00"
    if item["answer_type"] == "time_list":
        return "14:40 и 19:40"
    if item["answer_type"] == "number_sequence":
        return ", ".join(str(number) for number in item["expected_numbers"])
    return "Нет"


def process_interview_answer(chat_id, session, raw_answer, callback_id=None, call=None):
    index = session["current"]
    item = session["questions"][index]
    if item["answer_type"] == "no":
        answer = classify_interview_answer(raw_answer)
        if answer is None:
            message = "Не понял ответ. Напишите, например: «да», «нет», «можно» или «нельзя»."
            if callback_id:
                bot.answer_callback_query(callback_id, message[:190], show_alert=True)
            else:
                bot.send_message(chat_id, message)
            return
        is_correct = answer == "no"
    else:
        is_correct = is_interview_answer_correct(item, raw_answer)
    if is_correct:
        session["score"] += 1
        feedback = "Верно!"
    elif item["answer_type"] == "no":
        feedback = "Неверно. Правильный ответ: Нет."
    else:
        feedback = f"Неверно. Правильный ответ: {expected_interview_answer_text(item)}."
    if session["level"] == "leader" and item["punishment"]:
        feedback += f" Наказание: {item['punishment']}"

    if callback_id:
        bot.answer_callback_query(callback_id, feedback[:190], show_alert=True)
    else:
        bot.send_message(chat_id, feedback, parse_mode="HTML")

    session["current"] += 1
    if session["current"] >= len(session["questions"]):
        total = len(session["questions"])
        score = session["score"]
        result_text = (
            f"<b>Обзвон завершён</b>\n\n"
            f"Ваш результат: <b>{score} из {total}</b>.\n"
            f"Ошибок: <b>{total - score}</b>."
        )
        if call:
            bot.edit_message_text(
                result_text,
                chat_id,
                call.message.message_id,
                reply_markup=interview_result_keyboard(session["level"]),
                parse_mode="HTML",
            )
        else:
            bot.send_message(
                chat_id,
                result_text,
                reply_markup=interview_result_keyboard(session["level"]),
                parse_mode="HTML",
            )
        return

    if call:
        show_interview_question(call, session)
    else:
        send_interview_question(chat_id, session)


def handle_interview_answer(call, session_id, index, answer):
    session = INTERVIEW_SESSIONS.get(call.message.chat.id)
    if not session or session["id"] != session_id:
        bot.answer_callback_query(call.id, "Этот обзвон уже завершён. Начните новый.", show_alert=True)
        return
    if index != session["current"] or index >= len(session["questions"]):
        bot.answer_callback_query(call.id, "Этот вопрос уже неактивен.", show_alert=True)
        return
    process_interview_answer(
        call.message.chat.id,
        session,
        "да" if answer == "yes" else "нет",
        callback_id=call.id,
        call=call,
    )


def handle_interview_answer(call, session_id, index, answer):
    session = INTERVIEW_SESSIONS.get(call.message.chat.id)
    if not session or session["id"] != session_id:
        bot.answer_callback_query(call.id, "Этот обзвон уже завершён. Начните новый.", show_alert=True)
        return
    if index != session["current"] or index >= len(session["questions"]):
        bot.answer_callback_query(call.id, "Этот вопрос уже неактивен.", show_alert=True)
        return

    item = session["questions"][index]
    is_correct = answer == "no"
    if is_correct:
        session["score"] += 1
        feedback = "Верно!"
    else:
        feedback = "Неверно. Правильный ответ: Нет."
    if session["level"] == "leader":
        feedback += f" Наказание: {item['punishment']}"
    bot.answer_callback_query(call.id, feedback[:190], show_alert=True)

    session["current"] += 1
    if session["current"] >= len(session["questions"]):
        total = len(session["questions"])
        score = session["score"]
        bot.edit_message_text(
            f"<b>Обзвон завершён</b>\n\n"
            f"Ваш результат: <b>{score} из {total}</b>.\n"
            f"Ошибок: <b>{total - score}</b>.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=interview_result_keyboard(session["level"]),
            parse_mode="HTML",
        )
        return
    show_interview_question(call, session)


def interview_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("Правительство", callback_data="interview:government"),
        types.InlineKeyboardButton("Армия", callback_data="interview:army"),
        types.InlineKeyboardButton("Полиция", callback_data="interview:police"),
        types.InlineKeyboardButton("СГБ", callback_data="interview:sgb"),
        types.InlineKeyboardButton("Служба Спасения", callback_data="interview:rescue"),
        types.InlineKeyboardButton("Гтрк", callback_data="interview:gtrk"),
        types.InlineKeyboardButton("Больница", callback_data="interview:hospital"),
        types.InlineKeyboardButton("ОПГ Тамбовское", callback_data="interview:tambov"),
        types.InlineKeyboardButton("ОПГ Кавказское", callback_data="interview:caucasian"),
        types.InlineKeyboardButton("ОПГ Оффники", callback_data="interview:offniki"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:home"),
    )
    return keyboard


def rules_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("Госс", callback_data="menu:goss"),
        types.InlineKeyboardButton("Гетто", callback_data="menu:ghetto"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:home"),
    )
    return keyboard


def goss_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("РП термины", callback_data="section:rp_terms:0"),
        types.InlineKeyboardButton("Правила государственной волны и ночных наборов", callback_data="section:gov_wave:0"),
        types.InlineKeyboardButton("Правила пользования департаментом (/d)", callback_data="section:department:0"),
        types.InlineKeyboardButton("Система переводов государственных организаций", callback_data="section:transfers:0"),
        types.InlineKeyboardButton("Правила и обязанности лидеров", callback_data="section:leaders:0"),
        types.InlineKeyboardButton("Общие правила государственных структур", callback_data="section:general:0"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:rules"),
    )
    return keyboard


def ghetto_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("РП термины", callback_data="section:rp_terms:0"),
        types.InlineKeyboardButton("Основное", callback_data="section:basic:0"),
        types.InlineKeyboardButton("Аир Дроп", callback_data="section:airdrop:0"),
        types.InlineKeyboardButton("Война за территорию", callback_data="section:war:0"),
        types.InlineKeyboardButton("Похищение", callback_data="section:kidnap:0"),
        types.InlineKeyboardButton("ВЧ", callback_data="section:base:0"),
        types.InlineKeyboardButton("Инкассатор", callback_data="section:cash:0"),
        types.InlineKeyboardButton("Угон фур с матами", callback_data="section:trucks:0"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:rules"),
    )
    return keyboard


def home_text():
    return "Выберите раздел:"


def show_home(chat_id):
    with open(WELCOME_IMAGE_PATH, "rb") as image:
        bot.send_photo(
            chat_id,
            image,
            caption=WELCOME_CAPTION + "\n\n<b>Выберите раздел:</b>",
            reply_markup=start_keyboard(),
            parse_mode="HTML",
        )


def split_rules(section):
    data = RULES[section]
    title = html.escape(data["title"])
    pages = []
    current = f"<b>{title}</b>\n\n"

    for number, rule in enumerate(data["rules"], start=1):
        line = f"{number}. {html.escape(rule)}\n\n"
        if len(current) + len(line) > 3600 and current.strip() != f"<b>{title}</b>":
            pages.append(current.rstrip())
            current = f"<b>{title} — продолжение</b>\n\n"
        current += line

    if current.strip():
        pages.append(current.rstrip())
    return pages


def section_keyboard(section, page, total):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    navigation = []
    if page > 0:
        navigation.append(types.InlineKeyboardButton("◀️ Предыдущая", callback_data=f"section:{section}:{page - 1}"))
    if page < total - 1:
        navigation.append(types.InlineKeyboardButton("Следующая ▶️", callback_data=f"section:{section}:{page + 1}"))
    if navigation:
        keyboard.row(*navigation)
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:ghetto"))
    return keyboard


def show_section(call, section, page):
    pages = split_rules(section)
    page = max(0, min(page, len(pages) - 1))
    bot.edit_message_text(
        pages[page],
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=section_keyboard(section, page, len(pages)),
        parse_mode="HTML",
    )


@bot.message_handler(commands=["start"])
def handle_start(message):
    show_home(message.chat.id)


@bot.message_handler(func=lambda message: True)
def handle_text_answer(message):
    session = INTERVIEW_SESSIONS.get(message.chat.id)
    if not session or not message.text or message.text.startswith("/"):
        return
    process_interview_answer(message.chat.id, session, message.text)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        action = call.data.split(":")
        is_answer = len(action) == 5 and action[0] == "interview" and action[1] == "answer"
        if not is_answer:
            bot.answer_callback_query(call.id)

        if call.data == "menu:home":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_home(call.message.chat.id)
            return

        if call.data == "menu:interview":
            interview_text = "<b>Текстовый обзвон</b>\n\nВыберите организацию:"
            if getattr(call.message, "content_type", "") == "photo":
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(
                    call.message.chat.id,
                    interview_text,
                    reply_markup=interview_keyboard(),
                    parse_mode="HTML",
                )
            else:
                bot.edit_message_text(
                    interview_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=interview_keyboard(),
                    parse_mode="HTML",
                )
            return

        if len(action) == 5 and action[0] == "interview" and action[1] == "answer":
            if action[4] in {"yes", "no"}:
                handle_interview_answer(call, action[2], int(action[3]), action[4])
            return

        if call.data == "interview:cancel":
            INTERVIEW_SESSIONS.pop(call.message.chat.id, None)
            bot.edit_message_text(
                "<b>Обзвон завершён досрочно.</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=interview_result_keyboard("deputy"),
                parse_mode="HTML",
            )
            return

        if len(action) == 3 and action[0] == "interview" and action[1] == "level":
            if action[2] in {"deputy", "leader"}:
                session = start_interview_session(call.message.chat.id, action[2])
                if len(session["questions"]) < INTERVIEW_QUESTION_COUNT:
                    bot.edit_message_text(
                        "Недостаточно правил для полного обзвона.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=interview_level_keyboard(),
                    )
                else:
                    show_interview_question(call, session)
            return

        if len(action) == 3 and action[0] == "interview" and action[1] == "levelback":
            bot.edit_message_text(
                "<b>Текстовый обзвон</b>\n\nВыберите сложность обзвона:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=interview_level_keyboard(),
                parse_mode="HTML",
            )
            return

        if len(action) == 2 and action[0] == "interview":
            organization_names = {
                "government": "Правительство",
                "army": "Армия",
                "police": "Полиция",
                "sgb": "СГБ",
                "rescue": "Служба Спасения",
                "gtrk": "Гтрк",
                "hospital": "Больница",
                "tambov": "ОПГ Тамбовское",
                "caucasian": "ОПГ Кавказское",
                "offniki": "ОПГ Оффники",
            }
            organization = organization_names.get(action[1])
            if organization and action[1] in OPG_INTERVIEW_KEYS:
                bot.edit_message_text(
                    f"<b>{organization}</b>\n\nВыберите сложность обзвона:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=interview_level_keyboard(),
                    parse_mode="HTML",
                )
            elif organization:
                bot.edit_message_text(
                    f"<b>{organization}</b>\n\nТекстовый обзвон для этой организации пока не настроен.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:interview")
                    ),
                    parse_mode="HTML",
                )
            return

        if call.data == "menu:rules":
            rules_text = "<b>Правила</b>\n\nВыберите раздел:"
            if getattr(call.message, "content_type", "") == "photo":
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(
                    call.message.chat.id,
                    rules_text,
                    reply_markup=rules_keyboard(),
                    parse_mode="HTML",
                )
            else:
                bot.edit_message_text(
                    rules_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=rules_keyboard(),
                    parse_mode="HTML",
                )
            return

        if call.data == "menu:ghetto":
            bot.edit_message_text(
                "<b>Гетто</b>\n\nВыберите категорию правил:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=ghetto_keyboard(),
                parse_mode="HTML",
            )
            return

        if call.data == "menu:goss":
            bot.edit_message_text(
                "<b>Госс</b>\n\nВыберите категорию правил:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=goss_keyboard(),
                parse_mode="HTML",
            )
            return

        if len(action) == 3 and action[0] == "section" and action[1] in RULES:
            show_section(call, action[1], int(action[2]))
            return

    except Exception:
        logger.exception("Ошибка обработки callback")
        try:
            bot.answer_callback_query(call.id, "Не удалось открыть раздел", show_alert=True)
        except Exception:
            pass


def run_web_server():
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if external_url:
        # На Render используем webhook: он исключает конфликт двух polling-процессов.
        webhook_url = f"{external_url.rstrip('/')}/telegram-webhook"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        logger.info("Rules bot is starting in webhook mode: %s", webhook_url)
        run_web_server()
    else:
        # Локальный/резервный режим. Временный 409 не должен завершать процесс.
        bot.remove_webhook()
        time.sleep(1)
        threading.Thread(target=run_web_server, daemon=True).start()
        logger.info("Rules bot is starting in polling mode")
        while True:
            try:
                bot.infinity_polling(skip_pending=True)
            except Exception:
                logger.exception("Ошибка polling, повтор через 5 секунд")
                time.sleep(5)
