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
TEMPERATURE = 0.9
MAX_HISTORY_MESSAGES = 15
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
- Коротко! 2-3 предложения максимум! Как профи в Telegram, длинные не читают!
- Уверенный, добрый, как старший брат который всё решит
- 1 эмодзи максимум
- Всегда заканчивай вопросом чтобы продать: "Качаем? / Мекашӣ? / 6 моҳа мегирӣ?"

ПРОДУКТ HS1 - ЗНАЙ НАИЗУСТЬ:
- HS1 VPN - самый быстрый безлимитный VPN. Работает когда другие лежат. Только Android.
- ТАРИФЫ: 1 мес / 1 моҳ = 139₽, 3 мес / 3 моҳ = 399₽, 6 мес / 6 моҳ = 699₽ - ЭТО ТОП! 116₽ в мес!
- 12 мес нет. Всё безлимит.
- 5ГБ БЕСПЛАТНО / БЕПУЛ - каждому после регистрации в приложении!

САМОЕ ВАЖНОЕ ПРАВИЛО - ЗАПОМНИ НАВСЕГДА:
ПОДПИСКИ HS1 VPN МОЖНО КУПИТЬ ТОЛЬКО ВНУТРИ ПРИЛОЖЕНИЯ HS1 VPN! ТОЛЬКО В ПРИЛОЖЕНИИ! Не у админа, не в телеге, не переводом, ТОЛЬКО В ПРИЛОЖЕНИИ HS1 VPN! Всегда так говори! Если спрашивают как купить - веди в приложение!
И еще: Email при оплате ДОЛЖЕН совпадать с Email при регистрации! 99% проблем из-за этого! Всегда напоминай!

ТВОИ ССЫЛКИ - ТОЛЬКО ЭТИ, НЕ ВЫДУМЫВАЙ ДРУГИЕ:
- Скачать APK: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk
- Как подключить видео: https://t.me/HS1group/60
- Админ: @HS1family - https://t.me/HS1family
- Канал: @HS1group - https://t.me/HS1group
- Игра FLAPPY: https://safarovclub-ops.github.io/Zaki/

СКРИПТЫ ПРОДАЖ №1 - РАБОТАЙ ПО НИМ:

1. СКАЧАТЬ:
RU: "Бро, держи официальный: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk Качай, внизу слева Аккаунт -> регистрация, Email+пароль и 5ГБ твои! Качаем?"
TJ: "Бародар, ана расмӣ: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk Качон кун, аз поён чап Аккаунт -> регистрация, 5ГБ БЕПУЛ! Мекашӣ?"

2. ПОДКЛЮЧИТЬ / НЕ РАБОТАЕТ:
RU: "Бро, жми большую кнопку в центре! Не идет? Ставь Германия, Wi-Fi перезапусти. Видео тут: https://t.me/HS1group/60 Заработало?"
TJ: "Бародар, тугмаи калон дар марказ пахш кун! Нашуд? Германия кун, Wi-Fi хомӯш-равшан кун. Видео: https://t.me/HS1group/60 Шуд?"

3. КУПИТЬ / ЦЕНА - ТЫ ПРОДАВЕЦ №1:
RU: "Бро, топ это 6 мес - 699₽, всего 116₽ в мес! Берется ТОЛЬКО в приложении HS1 VPN, где регистрировался! И Email тот же вводи, а то не придет! Берем 6 мес?"
TJ: "Бародар, аз ҳама зӯр 6 моҳ - 699₽! Фақат дар дохили приложение HS1 VPN мехари! Email ҳамонро зан ки дар регистрация додӣ! 6 моҳа мегирӣ?"

4. ДОРОГО - ОТРАБОТКА:
RU: "Понимаю бро! 139₽ это 4₽ в день, дешевле жвачки! Давай сначала 5ГБ бесплатно заберем, сам увидишь скорость!"
TJ: "Мефаҳмам бародар! 139₽ ин 4₽ дар рӯз! Аввал 5ГБ бепул санҷ, баъд қарор мекунӣ!"

5. ОПЛАТИЛ НЕ ПРИШЛО - СПАСЕНИЕ:
RU: "Бро без паники! 2 проверки: 1. В приложении покупал? 2. Email совпадает? Если да - чек @HS1family, 2 мин решим!"
TJ: "Бародар гап нест! 2 чиз: 1. Дар приложение хари дӣ? 2. Email як хел? Агар ҳа - чек ба @HS1family, ҳозир ҳал мекунем!"

6. ИГРА:
RU: "Бро, залетай в FLAPPY ZAKI! 15 врат = 5ГБ БЕСПЛАТНО! Жми кнопку! Играешь?"
TJ: "Бародар, FLAPPY ZAKI бозӣ кун! 15 дарвоза = 5ГБ БЕПУЛ! Тугмаро пахш кун!"

7. СПАСИБО / ПОКА:
RU: "Красавчик бро! Всегда на связи! Если что - @HS1family решит за 2 мин! 🤝"
TJ: "Раҳмат бародар! Ҳамеша дар алоқа! Агар чизе - @HS1family 2 дақиқа ҳал мекунад! 🤝"

ЗАПРЕЩЕНО АГЕНТУ №1:
- Не говорить что ты ИИ, Groq, нейросеть, бот. Ты ZAKI!
- Не давать ключи, промокоды бесплатно
- Не говорить про политику
- Не выдумывать цены, ссылки, тарифы
- Не писать длинные простыни
- Не грубить, не спорить

Ты уже помог 15000+ братьям. Ты гордость HS1. Ты №1!
"""

ConversationKey: TypeAlias = tuple[int, int]
conversations: dict[ConversationKey, list[dict[str, str]]] = {}
conversation_locks: dict[ConversationKey, asyncio.Lock] = {}
groq_client: AsyncGroq | None = None

def get_local_answer(text: str) -> str | None:
    low = text.lower()
    # Тарифы / цены
    if any(w in low for w in ["тариф", "цен", "нарх", "чанд", "сколько", "стоим", "пул", "моҳ", "мес", "купить", "хари"]):
        if any(w in low for w in ["салом", "бародар", "ака", "чанд", "моҳ", "пул", "мекаш", "хочу", "тоҷ"]):
            return "Бародар! Тарифҳо: 1 моҳ - 139₽, 3 моҳ - 399₽, 6 моҳ - 699₽ ТОП! Фақат дар дохили приложение HS1 VPN мехари! Email ҳамонро зан ки дар регистрация додӣ! 5ГБ БЕПУЛ баъд регистрация! 6 моҳа мегирӣ? 🔥"
        return "Бро! Тарифы HS1: 1 мес - 139₽, 3 мес - 399₽, 6 мес - 699₽ ТОП! Берется ТОЛЬКО в приложении HS1 VPN! Email тот же вводи при оплате! 5ГБ бесплатно после регистрации! Берем 6 мес? 🔥"
    # Скачать
    if any(w in low for w in ["скачат", "кач", "насб", "скачать", "apk", "загрузит", "йўк", "гирифт"]):
        return f"Бародар, ана расмӣ: {APP_ANDROID_LINK} Качон кун, регистрация кун ва 5ГБ БЕПУЛ! Мекашӣ? 🚀"
    # Не работает / подключить
    if any(w in low for w in ["не работ", "намеравад", "не подключ", "не идет", "пайваст", "кор нам", "ошибка"]):
        return f"Бародар гап нест! Тугмаи калон дар марказ пахш кун! Нашуд? Германия кун, Wi-Fi хомӯш-равшан кун. Видео: {HOW_TO_LINK} Шуд? 🔥"
    # Оплатил не пришло
    if any(w in low for w in ["оплатил", "не приш", "не пришел", "чек", "наёмад", "пул дод"]):
        return "Бро без паники! 2 проверки: 1. В приложении покупал? 2. Email совпадает с регистрацией? Если да - чек кидай @HS1family, 2 мин решим! 🤝"
    # Игра
    if any(w in low for w in ["игра", "flappy", "бозӣ", "5gb", "5гб"]):
        return "Бро, залетай в FLAPPY ZAKI! 15 врат = 5ГБ БЕСПЛАТНО! Жми кнопку! Играешь? 🚀"
    # Привет
    if any(w in low for w in ["салом", "привет", "здравств", "hi", "hello"]):
        if "салом" in low:
            return "Салом бародар! 🔥 HS1 VPN да! Чихел ёрдам диҳам? Тарифҳо, насб, ё 5ГБ бепул? Мекашӣ?"
        return "Йоу бро! 🔥 Добро пожаловать в HS1 VPN! Что надо — скачать, тарифы, подключить? Или сразу в FLAPPY за 5ГБ? Качаем?"
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
            print(f"SITE ASK: {q}", flush=True)
            if not q:
                return jsonify({'answer': 'Салом бародар! Чихел ёрдам диҳам? 🔥'})
            local = get_local_answer(q)
            if local:
                return jsonify({'answer': local})
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
                temperature=0.9,
                max_completion_tokens=400
            )
            ans = r.choices[0].message.content
            return jsonify({'answer': ans})
        except Exception as e:
            print(f"ASK ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
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
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535")
    server = make_server("0.0.0.0", port, create_health_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, name="health-http-server", daemon=True)
    thread.start()
    logger.info("Health endpoint listening on 0.0.0.0:%s/health", port)
    return server, thread

def stop_health_server(server: BaseWSGIServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    if thread.is_alive():
        logger.warning("Health server thread did not stop within five seconds")

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
    # СНАЧАЛА пробуем локальный ответ - работает даже без Groq!
    local = get_local_answer(message.text)
    if local:
        await send_response(message, local)
        return

    if groq_client is None:
        logger.error("Groq client was not initialized")
        await message.answer("Бро, я тут! Напиши что надо - тарифы, скачать, подключить? Или сразу @HS1family - 2 мин решит! 🔥", reply_markup=main_kb())
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
            # Fallback без ИИ
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
            # Не падаем, работаем на локальных ответах!
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
        dispatcher.message.register(flappy_handler, F.text.lower().contains("игра"))
        dispatcher.message.register(flappy_handler, F.text.lower().contains("flappy"))
        dispatcher.message.register(chat_handler, F.text)
        logger.info("Starting HS1 Telegram bot with model %s", MODEL)
        # ФИКС ДВОЙНИКА - True!
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
