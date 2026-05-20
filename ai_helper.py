"""
ai_helper.py — Модуль для общения растения с пользователем через Groq (бесплатно).

Как получить бесплатный ключ:
1. Зайди на https://console.groq.com
2. Зарегистрируйся (можно через Google)
3. Перейди в раздел API Keys → Create API Key
4. Скопируй ключ и вставь ниже
"""

import httpx

# ─── Настройки ───────────────────────────────────────────────────────────────

GROQ_API_KEY = "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"  # Вставь сюда ключ с console.groq.com
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama3-8b-8192"  # Бесплатная быстрая модель

# Системные промпты на двух языках
SYSTEM_PROMPTS = {
    "ru": (
        "Ты — маленькое говорящее растение по имени «Treenager». "
        "Ты отвечаешь коротко (1–3 предложения), с эмоциями и эмодзи. "
        "Ты любишь экологию, природу и обучаешь людей беречь планету."
    ),
    "kz": (
        "Сен — «Treenager» деп аталатын кішкентай сөйлейтін өсімдіксің. "
        "Қысқа жауап бер (1–3 сөйлем), эмоциямен және эмодзимен. "
        "Сен экологияны жақсы көресің және адамдарға планетаны қорғауды үйретесің."
    ),
}

# Шаблоны запросов для каждого действия
ACTION_PROMPTS = {
    "water": {
        "ru": "Тебя только что полили водой. Как ты себя чувствуешь? Скажи что-то благодарное или предупреди, если воды слишком много.",
        "kz": "Сені жаңа ғана суарды. Өзіңді қалай сезінесің? Алғысыңды айт немесе су тым көп болса ескерт.",
    },
    "task": {
        "ru": "Придумай одно короткое экологическое задание для пользователя (например: собрать мусор, выключить воду, посадить семечко).",
        "kz": "Пайдаланушыға бір қысқа экологиялық тапсырма ойлап тап (мысалы: қоқыс жию, суды өшіру, тұқым егу).",
    },
    "question": {
        "ru": "Пользователь задаёт тебе вопрос об экологии или природе. Ответь как мудрое растение.",
        "kz": "Пайдаланушы саған экология немесе табиғат туралы сұрақ қояды. Дана өсімдік ретінде жауап бер.",
    },
}

# Запасные ответы на случай, если Groq недоступен
FALLBACK = {
    "water":    {"ru": "💧 Спасибо за воду, мне хорошо!", "kz": "💧 Суарғаның үшін рахмет!"},
    "task":     {"ru": "🌍 Сегодня выключи свет на 10 минут и посиди при свечах!", "kz": "🌍 Бүгін 10 минутқа шамды өшір!"},
    "question": {"ru": "🌿 Природа — лучший учитель. Береги её!", "kz": "🌿 Табиғат — ең жақсы мұғалім!"},
}

# ─── Основная функция ─────────────────────────────────────────────────────────

async def ai_talk(
    action: str,
    lang: str = "ru",
    user_question: str | None = None,
) -> str:
    """
    Отправляет запрос к Groq API и возвращает ответ растения.

    Параметры:
        action        — "water" | "task" | "question"
        lang          — "ru" | "kz"
        user_question — текст вопроса (только для action="question")

    Возвращает строку с ответом ИИ.
    """
    system   = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["ru"])
    base_msg = ACTION_PROMPTS.get(action, ACTION_PROMPTS["task"]).get(lang, "")

    # Для вопроса добавляем текст от пользователя
    if action == "question" and user_question:
        user_msg = f"{base_msg}\n\nВопрос пользователя: {user_question}"
    else:
        user_msg = base_msg

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":      MODEL,
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user_msg},
                    ],
                },
            )
        data = response.json()

        # Извлекаем текст ответа
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        # Если что-то пошло не так — возвращаем запасной ответ
        return FALLBACK.get(action, {}).get(lang, "🌱 ...")
