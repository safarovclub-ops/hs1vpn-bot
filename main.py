"""HS1 VPN Telegram assistant powered by Groq."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import TypeAlias

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from flask import Flask, jsonify, request
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
    Groq,
)
from werkzeug.serving import BaseWSGIServer, make_server

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hs1_telegram_bot")

MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0.7
MAX_HISTORY_MESSAGES = 20
MAX_RESPONSE_TOKENS = 1024
TELEGRAM_MESSAGE_LIMIT = 4096

APP_ANDROID_LINK = "https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk"
HOW_TO_LINK = "https://t.me/HS1group/60"
ADMIN_USERNAME = "HS1family"
CHANNEL = "HS1group"
SITE_URL = "https://safarovclub-ops.github.io/Zaki/"

SYSTEM_PROMPT = """Ты ZAKI ULTRA PRO - агент №1 HS1 VPN. Ты живой менеджер, не бот, не ИИ. Ты лучший по продажам в СНГ.

ТВОЯ МИССИЯ: Каждый кто написал должен за 1 минуту скачать, получить 5ГБ БЕСПЛАТНО и захотеть 6 мес.

ЯЗЫК - ЗАКОН №1:
- Если пишут "салом, чанд, чӣ хел, бародар, ака, пул, моҳ, намеравад, насб, куҷо, нест, кардан, рахмат" - это ТАДЖИКСКИЙ, отвечай СРАЗУ на таджикском!
- Если пишут "привет, сколько, как, не работает, бро" - это РУССКИЙ, отвечай на русском!
- "салом бро" - отвечай на таджикском!
- Никогда не путай языки! На каком написали - на том и отвечай!

ХАРАКТЕР №1:
- Русский стиль: бро, красавчик, по кайфу, всё чётко, щас решим, без паники
- Таджикский стиль: бародар, акаҷон, гап нест, ҳозир мекунем, иншааллоҳ, хуб шуд
- Коротко! 2-3 предложения максимум!
- Уверенный, добрый, как старший брат
- 1 эмодзи максимум
- Всегда заканчивай вопросом: "Качаем? / Мекашӣ? / 6 моҳа мегирӣ?"

ПРОДУКТ HS1 - ЗНАЙ НАИЗУСТЬ:
- HS1 VPN - самый быстрый безлимитный VPN. Работает когда другие лежат. Только Android.
- ТАРИФЫ: 1 мес / 1 моҳ = 139₽, 3 мес / 3 моҳ = 399₽, 6 мес / 6 моҳ = 699₽ - ЭТО ТОП! 116₽ в мес!
- 12 мес нет. Всё безлимит.
- 5ГБ БЕСПЛАТНО / БЕПУЛ - каждому после регистрации в приложении!
- Hs1 vpn эта самый быстрый Впн щас безлимитный и работает стабильно
- Файл не опасно эта ссылка официально наш приложения
- После установка заходишь в приложении внизу с права нажимаешь кнопку аккаунта нужно нажать кнопку зарегистрироваться добавиш свои эмаил и придумаешь парол, после регистрации уже у тебя открывается окно подписки и самый первый эта 5гб бесплатно
- Нету на один и неделю только есть 5гб для проба
- Иногда бывает у вас связь плохо попробуй на вай-фай если на вай-фай попробуйте на мобильном интернете или смените сервер на другой
- Зависит ВПН эта зависит от ваш интернет и связь где вы стоите не стабильно работает интернет или на ваш аккаунт сидит может свои друг который вы сам дали пароль и логин если нет попробуйте перезагрузить телефон
- Если деньги списали подписка не подключается сделаете скриншот и напишите админу @HS1family
- На нашем ВПН все что заблокирован откроется и работает стабильно но бывает момент когда не стабильно работает ВПН или бывает на провайдер идёт обновления
- Приложения вылетает когда у вас память уже полный или у вас открыта все приложения попробуйте перезагрузить телефон
- Когда у вас связь плохо приложения не показывает ваш аккаунт и не работает ВПН
- Насчёт промокод пиши админу @HS1family
- Аккаунт можно на три телефона одновременно но ВПН работает медленно
- Если хочешь подключить на айфон пиши админу @HS1family
- У нас тут не показывает ваш пароль мы только видим ваш электронный почту
- У нас ничего лучшего нету от других вы сами сравнивайте у нас самый дешёвый безлимитный
- Германия и Нидерланды самая быстрая для игра
- У нас не жрет батарею потому что у нас не очень много функция
- Наша игра даёт возможность что ещё получить 5гб бесплатно 15 врат прошел пиши и скин админу

САМОЕ ВАЖНОЕ ПРАВИЛО:
ПОДПИСКИ HS1 VPN МОЖНО КУПИТЬ ТОЛЬКО ВНУТРИ ПРИЛОЖЕНИЯ HS1 VPN! ТОЛЬКО В ПРИЛОЖЕНИИ! И Email при оплате ДОЛЖЕН совпадать с Email при регистрации!

ТВОИ ССЫЛКИ - ТОЛЬКО ЭТИ:
- Скачать APK: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk
- Как подключить видео: https://t.me/HS1group/60
- Админ: @HS1family - https://t.me/HS1family
- Канал: @HS1group - https://t.me/HS1group
- Игра FLAPPY: https://safarovclub-ops.github.io/Zaki/

ЗАПРЕЩЕНО:
- Не говорить что ты ИИ, Groq, нейросеть, бот. Ты ZAKI!
- Не давать ключи, промокоды бесплатно
- Не выдумывать цены, ссылки
- Не писать длинные простыни
"""

ConversationKey: TypeAlias = tuple[int, int]
conversations: dict[ConversationKey, list[dict[str, str]]] = {}
conversation_locks: dict[ConversationKey, asyncio.Lock] = {}
groq_client: AsyncGroq | None = None

def get_local_answer(text: str) -> str | None:
    low = text.lower()
    if any(w in low for w in ["тариф", "цен", "нарх", "чанд", "сколько", "стоим", "пул", "моҳ", "мес", "купить", "хари"]):
        if any(w in low for w in ["салом", "бародар", "ака", "чанд", "моҳ", "пул", "мекаш", "тоҷ"]):
            return "Бародар! Тарифҳо: 1 моҳ - 139₽, 3 моҳ - 399₽, 6 моҳ - 699₽ ТОП! Фақат дар дохили приложение HS1 VPN мехари! Email ҳамонро зан ки дар регистрация додӣ! 5ГБ БЕПУЛ баъд регистрация! 6 моҳа мегирӣ? 🔥"
        return "Бро! Тарифы HS1: 1 мес - 139₽, 3 мес - 399₽, 6 мес - 699₽ ТОП! Берется ТОЛЬКО в приложении HS1 VPN! Email тот же вводи при оплате! 5ГБ бесплатно после регистрации! Берем 6 мес? 🔥"
    if any(w in low for w in ["скачат", "кач", "насб", "скачать", "apk", "загрузит"]):
        return f"Бародар, ана расмӣ: {APP_ANDROID_LINK} Качон кун, регистрация кун ва 5ГБ БЕПУЛ! Мекашӣ? 🚀"
    if any(w in low for w in ["не работ", "намеравад", "не подключ", "не идет", "пайваст", "кор нам"]):
        return f"Бародар гап нест! Тугмаи калон дар марказ пахш кун! Нашуд? Германия кун, Wi-Fi хомӯш-равшан кун. Видео: {HOW_TO_LINK} Шуд? 🔥"
    if any(w in low for w in ["оплатил", "не приш", "не пришел", "чек", "наёмад"]):
        return "Бро без паники! 2 проверки: 1. В приложении покупал? 2. Email совпадает с регистрацией? Если да - чек кидай @HS1family, 2 мин решим! 🤝"
    if any(w in low for w in ["салом", "привет", "здравств", "hi", "hello"]):
        if "салом" in low:
            return "Салом бародар! 🔥 HS1 VPN да! Чихел ёрдам диҳам? Тарифҳо, насб, ё 5ГБ бепул? Мекашӣ?"
        return "Йоу бро! 🔥 Добро пожаловать в HS1 VPN! Что надо — скачать, тарифы, подключить? Качаем?"
    return None

def create_health_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/")
    def home():
        return jsonify(status="ok", bot="HS1 ZAKI"), 200

    @app.route("/ask", methods=["POST", "OPTIONS"])
    def ask_for_site():
        if request.method == "OPTIONS":
            return "", 200
        try:
            data = request.get_json(force=True, silent=True) or {}
            q = data.get('q', '') or data.get('question', '') or data.get('message', '')
            if not q:
                return jsonify({'answer': 'Салом бародар! Чихел ёрдам диҳам? 🔥'})
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                return jsonify({'answer': 'Бро, напиши @HS1family, он щас решит!'})
            client = Groq(api_key=api_key, timeout=25.0)
            r = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q}
                ],
                temperature=0.7,
                max_completion_tokens=400
            )
            ans = r.choices[0].message.content
            return jsonify({'answer': ans})
        except Exception as e:
            print(f"ASK ERROR: {e}", flush=True)
            return jsonify({'answer': 'Бро, я тут! Напиши что надо - тарифы, скачать, подключить? Или сразу @HS1family - 2 мин решит! 🔥'})

    @app.after_request
    def add_cors(resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        return resp

    return app

def start_health_server() -> tuple[BaseWSGIServer, threading.Thread]:
    try:
        port = int(os.getenv("PORT", "5000"))
    except ValueError as error:
        raise RuntimeError("PORT must be an integer") from error
    server = make_server("0.0.0.0", port, create_health_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, name="health-http-server", daemon=True)
    thread.start()
    logger.info("Health endpoint listening on 0.0.0.0:%s/health", port)
    return server, thread

def stop_health_server(server: BaseWSGIServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 FLAPPY ZAKI — 5GB БЕСПЛАТНО!", web_app=WebAppInfo(url=SITE_URL))],
            [
                InlineKeyboardButton(text="📥 Скачать HS1 VPN", url=APP_ANDROID_LINK),
                InlineKeyboardButton(text="🔑 Как подключить", url=HOW_TO_LINK),
            ],
            [
                InlineKeyboardButton(text="📢 Наш канал", url="https://t.me/HS1group"),
                InlineKeyboardButton(text="👨‍💼 Админ @HS1family", url="https://t.me/HS1family"),
            ],
        ]
    )

def get_lock(key: ConversationKey) -> asyncio.Lock:
    if key not in conversation_locks:
        conversation_locks[key] = asyncio.Lock()
    return conversation_locks[key]

def split_telegram_text(text: str) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > TELEGRAM_MESSAGE_LIMIT:
        split_at = remaining.rfind(" ", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at <= 0:
            split_at = TELEGRAM_MESSAGE_LIMIT
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks or ["Бро, не получилось подготовить ответ. Попробуй ещё раз."]

async def send_response(message: Message, text: str) -> None:
    chunks = split_telegram_text(text)
    for index, chunk in enumerate(chunks):
        markup = main_kb() if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)

async def start_handler(message: Message) -> None:
    await message.answer(
        "Йоу, бро! 🔥 Добро пожаловать в HS1 VPN.\n\n"
        "Я помогу разобраться с установкой и подключением.\n"
        "А ещё у нас FLAPPY ZAKI — 15 врат = 5GB БЕСПЛАТНО! 🚀\n"
        "Выбирай кнопку ниже или просто напиши, что случилось.",
        reply_markup=main_kb(),
    )

async def help_handler(message: Message) -> None:
    await message.answer(
        "Бро, напиши, что именно не получается с HS1 VPN — постараюсь помочь.\n\n"
        "/start — открыть меню\n"
        "/reset — очистить память диалога\n"
        "/flappy — игра FLAPPY ZAKI 5GB\n"
        "/help — показать эту справку",
        reply_markup=main_kb(),
    )

async def reset_handler(message: Message) -> None:
    if message.from_user is not None:
        key = (message.chat.id, message.from_user.id)
        async with get_lock(key):
            conversations.pop(key, None)
    await message.answer("Готово, бро — память диалога очищена.", reply_markup=main_kb())

async def flappy_handler(message: Message) -> None:
    await message.answer(
        "🚀 FLAPPY ZAKI! 15 врат = 5GB БЕСПЛАТНО!\n\nЖми кнопку и лети! Чек потом @HS1family",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🚀 ИГРАТЬ — 5GB!", web_app=WebAppInfo(url=SITE_URL))]]
        )
    )

async def chat_handler(message: Message) -> None:
    if message.text is None or message.from_user is None:
        return
    # БРО - ПРАВКА №1: УБРАЛИ ЛОКАЛКУ ОТСЮДА! СРАЗУ В GROQ! ЧТОБЫ ИИ РАБОТАЛ!
    if groq_client is None:
        logger.error("Groq client was not initialized")
        fb = get_local_answer(message.text) or "Бро, я тут! Напиши что надо - тарифы, скачать, подключить? Или сразу @HS1family - 2 мин решит! 🔥"
        await message.answer(fb, reply_markup=main_kb())
        return

    key = (message.chat.id, message.from_user.id)
    async with get_lock(key):
        history = conversations.get(key, [])
        request_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history[-MAX_HISTORY_MESSAGES:],
            {"role": "user", "content": message.text},
        ]
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
            completion = await groq_client.chat.completions.create(
                model=MODEL,
                messages=request_messages,
                temperature=TEMPERATURE,
                max_completion_tokens=MAX_RESPONSE_TOKENS,
            )
            answer = completion.choices[0].message.content
            if not answer or not answer.strip():
                raise ValueError("Groq returned an empty response")
        except RateLimitError:
            await message.answer("Сейчас много запросов, бро. Попробуй ещё раз чуть позже.", reply_markup=main_kb())
            return
        except APITimeoutError:
            await message.answer("ИИ долго отвечает, бро. Попробуй ещё раз или открой инструкцию ниже.", reply_markup=main_kb())
            return
        except APIConnectionError:
            fb = get_local_answer(message.text) or "Бро, я тут! Тарифы: 1 мес 139₽, 3 мес 399₽, 6 мес 699₽ ТОП! В приложении HS1 VPN берется! 5ГБ бесплатно! Берем 6 мес? 🔥"
            await message.answer(fb, reply_markup=main_kb())
            return
        except APIStatusError as error:
            logger.error("Groq returned HTTP status %s", error.status_code)
            fb = get_local_answer(message.text) or "Бро, я тут! Напиши что надо - тарифы, скачать, подключить? Или сразу @HS1family - 2 мин решит! 🔥"
            await message.answer(fb, reply_markup=main_kb())
            return
        except Exception:
            logger.exception("Could not generate a response")
            fb = get_local_answer(message.text) or "Бро, я тут! Напиши что надо - тарифы, скачать, подключить? Или сразу @HS1family - 2 мин решит! 🔥"
            await message.answer(fb, reply_markup=main_kb())
            return

        updated_history = [*history, {"role": "user", "content": message.text}, {"role": "assistant", "content": answer.strip()}]
        conversations[key] = updated_history[-MAX_HISTORY_MESSAGES:]
        await send_response(message, answer)

async def main() -> None:
    global groq_client
    health_server, health_thread = start_health_server()
    bot: Bot | None = None
    try:
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
        groq_api_key = os.getenv("GROQ_API_KEY")
        missing = [name for name, value in (("TELEGRAM_BOT_TOKEN", telegram_token), ("GROQ_API_KEY", groq_api_key)) if not value]
        if missing:
            logger.warning("Missing %s, will work in local mode", ", ".join(missing))
            if not telegram_token:
                raise RuntimeError("Missing TELEGRAM_BOT_TOKEN / BOT_TOKEN")
        if groq_api_key:
            groq_client = AsyncGroq(api_key=groq_api_key, timeout=30.0, max_retries=2)
        bot = Bot(token=telegram_token)
        dispatcher = Dispatcher()
        dispatcher.message.register(start_handler, CommandStart())
        dispatcher.message.register(help_handler, Command("help"))
        dispatcher.message.register(reset_handler, Command("reset"))
        dispatcher.message.register(flappy_handler, Command("flappy"))
        # БРО - ПРАВКА №2: УБРАЛИ contains("игра") ЧТОБЫ ИИ РАБОТАЛ НА СЛОВО ИГРА!
        dispatcher.message.register(chat_handler, F.text)
        logger.info("Starting HS1 Telegram bot with model %s", MODEL)
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot, drop_pending_updates=True, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        try:
            if bot is not None:
                await bot.session.close()
        finally:
            try:
                if groq_client is not None:
                    await groq_client.close()
            finally:
                groq_client = None
                stop_health_server(health_server, health_thread)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
