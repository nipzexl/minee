
"""
EcoBala — Эко-тамагочи бот на aiogram 3.x
Запуск: python bot.py
Зависимости: aiogram==3.x, python-dotenv (опционально)
"""

import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем функцию общения с ИИ из ai_helper.py
from ai_helper import ai_talk

# ─── Настройки ───────────────────────────────────────────────────────────────

BOT_TOKEN = "8834002135:AAFvAPmS5C8IdS6OQT-MWR_T-9n9LGWbjiE"  # Замените на реальный токен от @BotFather
session = AiohttpSession(proxy="http://109.123.232.55:8080")
bot = Bot(token=BOT_TOKEN, session=session)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Глобальное хранилище данных пользователей ───────────────────────────────

# Структура: user_data[user_id] = {
#   "plant_name": str,   — имя растения
#   "health": int,       — здоровье (0–100)
#   "water": int,        — уровень воды (0–100)
#   "exp": int,          — опыт
#   "lang": str,         — язык ("ru" или "kz")
# }
user_data: dict[int, dict] = {}

# ─── Состояния FSM (конечный автомат для диалогов) ───────────────────────────

class BotStates(StatesGroup):
    choosing_lang   = State()   # Выбор языка
    choosing_plant  = State()   # Выбор растения
    asking_question = State()   # Ожидание вопроса от пользователя

# ─── Тексты интерфейса на двух языках ────────────────────────────────────────

TEXTS = {
    "ru": {
        "welcome":        "🌱 Привет! Я Treenager — твоё эко-тамагочи.\nВыбери язык общения:",
        "choose_plant":   "Отлично! Теперь выбери своё растение:",
        "plant_chosen":   "🌿 Твоё растение «{name}» создано!\nЗдоровье: {health} | Вода: {water} | Опыт: {exp}",
        "status":         "🌿 {name}\n❤️ Здоровье: {health}\n💧 Вода: {water}\n⭐ Опыт: {exp}",
        "watered":        "💧 Полито! Вода: {water}, Здоровье: {health}",
        "task_done":      "✅ Задание выполнено! Опыт: {exp}",
        "ask_question":   "❓ Напиши свой вопрос:",
        "wilted":         "😢 Я завял... Напиши /start чтобы начать заново.",
        "overwatered":    "😰 Осторожно, перелив! Вода: {water}, Здоровье: {health}",
        "btn_water":      "💧 Полить",
        "btn_task":       "📋 Задание",
        "btn_ask":        "❓ Спросить",
        "btn_status":     "📊 Статус",
        "lang_ru":        "🇷🇺 Русский",
        "lang_kz":        "🇰🇿 Қазақша",
    },
    "kz": {
        "welcome":        "🌱 Сәлем! Мен Treenager — сенің эко-тамагочиің.\nТіл таңда:",
        "choose_plant":   "Керемет! Енді өсімдігіңді таңда:",
        "plant_chosen":   "🌿 «{name}» өсімдігің жасалды!\nДенсаулық: {health} | Су: {water} | Тәжірибе: {exp}",
        "status":         "🌿 {name}\n❤️ Денсаулық: {health}\n💧 Су: {water}\n⭐ Тәжірибе: {exp}",
        "watered":        "💧 Суарылды! Су: {water}, Денсаулық: {health}",
        "task_done":      "✅ Тапсырма орындалды! Тәжірибе: {exp}",
        "ask_question":   "❓ Сұрағыңды жаз:",
        "wilted":         "😢 Мен солып кеттім... Қайта бастау үшін /start жаз.",
        "overwatered":    "😰 Абай бол, тым көп су! Су: {water}, Денсаулық: {health}",
        "btn_water":      "💧 Суару",
        "btn_task":       "📋 Тапсырма",
        "btn_ask":        "❓ Сұрау",
        "btn_status":     "📊 Статус",
        "lang_ru":        "🇷🇺 Русский",
        "lang_kz":        "🇰🇿 Қазақша",
    },
}

# Доступные растения (имя : эмодзи)
PLANTS = {
    "Росток":   "🌱",
    "Кактус":   "🌵",
    "Цветок":   "🌸",
    "Дерево":   "🌳",
    "Бамбук":   "🎋",
}

# ─── Вспомогательные функции ─────────────────────────────────────────────────

def get_lang(user_id: int) -> str:
    """Возвращает язык пользователя (по умолчанию русский)."""
    return user_data.get(user_id, {}).get("lang", "ru")


def t(user_id: int, key: str, **kwargs) -> str:
    """Возвращает локализованный текст с подстановкой параметров."""
    lang = get_lang(user_id)
    text = TEXTS[lang].get(key, TEXTS["ru"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Создаёт основную клавиатуру с действиями."""
    lang = get_lang(user_id)
    txts = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=txts["btn_water"]),  KeyboardButton(text=txts["btn_task"])],
            [KeyboardButton(text=txts["btn_ask"]),    KeyboardButton(text=txts["btn_status"])],
        ],
        resize_keyboard=True,
    )


def lang_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang_ru"),
        InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz"),
    ]])


def plant_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора растения."""
    buttons = [
        InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"plant_{name}")
        for name, emoji in PLANTS.items()
    ]
    # Разбиваем на строки по 2 кнопки
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def is_plant_alive(user_id: int) -> bool:
    """Проверяет, живо ли растение пользователя."""
    return user_data.get(user_id, {}).get("health", 0) > 0

# ─── Инициализация бота ───────────────────────────────────────────────────────

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ─── Обработчики команд ───────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start — начинаем с выбора языка."""
    await state.set_state(BotStates.choosing_lang)
    await message.answer(
        TEXTS["ru"]["welcome"],  # Приветствие всегда на русском
        reply_markup=lang_keyboard(),
    )


@dp.callback_query(F.data.in_({"lang_ru", "lang_kz"}), BotStates.choosing_lang)
async def cb_choose_lang(call: CallbackQuery, state: FSMContext):
    """Пользователь выбрал язык."""
    user_id = call.from_user.id
    lang = "ru" if call.data == "lang_ru" else "kz"

    # Сохраняем язык (или создаём запись)
    if user_id not in user_data:
        user_data[user_id] = {"plant_name": "Росток", "health": 100, "water": 100, "exp": 0, "lang": lang}
    else:
        user_data[user_id]["lang"] = lang

    await call.message.edit_text(t(user_id, "choose_plant"))
    await call.message.edit_reply_markup(reply_markup=plant_keyboard())
    await state.set_state(BotStates.choosing_plant)
    await call.answer()


@dp.callback_query(F.data.startswith("plant_"), BotStates.choosing_plant)
async def cb_choose_plant(call: CallbackQuery, state: FSMContext):
    """Пользователь выбрал растение — инициализируем его данные."""
    user_id   = call.from_user.id
    plant_name = call.data.removeprefix("plant_")

    # Полная инициализация состояния игры
    user_data[user_id].update({
        "plant_name": plant_name,
        "health":     100,
        "water":      100,
        "exp":        0,
    })

    emoji = PLANTS.get(plant_name, "🌱")
    ud    = user_data[user_id]

    await call.message.edit_text(
        f"{emoji} " + t(user_id, "plant_chosen",
                        name=plant_name, health=ud["health"],
                        water=ud["water"], exp=ud["exp"])
    )
    await call.message.answer("⬇️", reply_markup=main_keyboard(user_id))
    await state.clear()
    await call.answer()

# ─── Кнопка «Полить» ─────────────────────────────────────────────────────────

@dp.message(F.text.in_({"💧 Полить", "💧 Суару"}))
async def action_water(message: Message):
    """Поливаем растение. Вода +20, но если > 100 — здоровье -5 (перелив)."""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer("Сначала напиши /start!")
        return

    if not is_plant_alive(user_id):
        await message.answer(t(user_id, "wilted"))
        return

    ud = user_data[user_id]
    ud["water"] += 20

    if ud["water"] > 100:
        ud["water"]  = 100
        ud["health"] = max(0, ud["health"] - 5)  # Штраф за перелив
        status_text  = t(user_id, "overwatered", water=ud["water"], health=ud["health"])
    else:
        status_text = t(user_id, "watered", water=ud["water"], health=ud["health"])

    # Получаем ответ растения от ИИ
    ai_response = await ai_talk(action="water", lang=ud["lang"])

    await message.answer(status_text)
    await message.answer(f"🌱 {ud['plant_name']}: {ai_response}")

# ─── Кнопка «Задание» ────────────────────────────────────────────────────────

@dp.message(F.text.in_({"📋 Задание", "📋 Тапсырма"}))
async def action_task(message: Message):
    """Выдаём экологическое задание. Опыт +10."""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer("Сначала напиши /start!")
        return

    if not is_plant_alive(user_id):
        await message.answer(t(user_id, "wilted"))
        return

    ud = user_data[user_id]
    ud["exp"] += 10  # Начисляем опыт за задание

    # Получаем задание от ИИ
    ai_response = await ai_talk(action="task", lang=ud["lang"])

    await message.answer(t(user_id, "task_done", exp=ud["exp"]))
    await message.answer(f"📋 {ai_response}")

# ─── Кнопка «Спросить» ───────────────────────────────────────────────────────

@dp.message(F.text.in_({"❓ Спросить", "❓ Сұрау"}))
async def action_ask_prompt(message: Message, state: FSMContext):
    """Просим пользователя ввести вопрос."""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer("Сначала напиши /start!")
        return

    await state.set_state(BotStates.asking_question)
    await message.answer(
        t(user_id, "ask_question"),
        reply_markup=ReplyKeyboardRemove(),  # Убираем клавиатуру на время ввода
    )


@dp.message(BotStates.asking_question)
async def action_ask_answer(message: Message, state: FSMContext):
    """Получаем вопрос пользователя и отправляем его в ИИ."""
    user_id       = message.from_user.id
    user_question = message.text

    if user_id not in user_data:
        await message.answer("Сначала напиши /start!")
        await state.clear()
        return

    ud = user_data[user_id]

    # Передаём вопрос в ai_helper
    ai_response = await ai_talk(
        action="question",
        user_question=user_question,
        lang=ud["lang"],
    )

    await message.answer(f"🌱 {ud['plant_name']}: {ai_response}", reply_markup=main_keyboard(user_id))
    await state.clear()

# ─── Кнопка «Статус» ─────────────────────────────────────────────────────────

@dp.message(F.text.in_({"📊 Статус", "📊 Статус"}))
async def action_status(message: Message):
    """Показываем текущее состояние растения."""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer("Сначала напиши /start!")
        return

    ud = user_data[user_id]
    await message.answer(
        t(user_id, "status",
          name=ud["plant_name"], health=ud["health"],
          water=ud["water"],     exp=ud["exp"])
    )

# ─── Фоновая задача: таймер деградации ───────────────────────────────────────

async def decay_loop():
    """
    Каждые 30 минут снижает здоровье и воду на 5 единиц у всех активных
    пользователей. Если здоровье падает до 0 — отправляет сообщение о гибели.
    """
    DECAY_INTERVAL = 30 * 60  # 30 минут в секундах

    while True:
        await asyncio.sleep(DECAY_INTERVAL)

        for user_id, ud in list(user_data.items()):
            # Пропускаем уже «умершие» растения
            if ud["health"] <= 0:
                continue

            # Уменьшаем показатели
            ud["water"]  = max(0, ud["water"]  - 5)
            ud["health"] = max(0, ud["health"] - 5)

            logger.info(
                f"Decay: user={user_id}, health={ud['health']}, water={ud['water']}"
            )

            # Растение умерло — уведомляем пользователя
            if ud["health"] <= 0:
                try:
                    await bot.send_message(
                        user_id,
                        f"🥀 {ud['plant_name']}: " + t(user_id, "wilted"),
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение user={user_id}: {e}")

# ─── Точка входа ─────────────────────────────────────────────────────────────

async def main():
    """Запускаем бота и фоновую задачу одновременно."""
    asyncio.create_task(decay_loop())   # Запускаем таймер деградации
    await dp.start_polling(bot)         # Запускаем polling


async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    # Запуск мини-сайта для обмана Render
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    
    # Запуск вашего бота
    print("Polling started!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
