"""Telegram chatbot powered by Groq."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TypeAlias

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_ai_bot")

DEFAULT_MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = (
    "Ты — ИИ-помощник HS1 VPN. Отвечай по-русски, коротко и дружелюбно. "
    "Помогай с установкой и подключением HS1 VPN на Android. "
    f"Ссылка на приложение: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk. "
    "Инструкция: https://t.me/HS1group/60. "
    "Канал: @HS1group. Поддержка: @HS1family. "
    "Не выдумывай настройки, состояние серверов или детали подписки. "
    "Если не знаешь ответа или вопрос касается аккаунта/ключа, направь пользователя к @HS1family."
)
APP_ANDROID_LINK = "https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk"
HOW_TO_LINK = "https://t.me/HS1group/60"
ADMIN_USERNAME = "HS1family"
CHANNEL = "HS1group"
MAX_HISTORY_MESSAGES = 20
MAX_RESPONSE_TOKENS = 1024
TELEGRAM_MESSAGE_LIMIT = 4096

ConversationKey: TypeAlias = tuple[int, int]
conversations: dict[ConversationKey, list[dict[str, str]]] = {}
conversation_locks: dict[ConversationKey, asyncio.Lock] = {}
groq_client: AsyncGroq | None = None


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Скачать HS1 VPN на Android", url=APP_ANDROID_LINK)],
            [InlineKeyboardButton(text="🔑 Как подключить VPN", url=HOW_TO_LINK)],
            [
                InlineKeyboardButton(
                    text=f"📢 Наш канал @{CHANNEL}",
                    url=f"https://t.me/{CHANNEL}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"👨‍💻 Поддержка / Админ @{ADMIN_USERNAME}",
                    url=f"https://t.me/{ADMIN_USERNAME}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Спросить у ИИ-помощника",
                    callback_data="ask_ai",
                )
            ],
        ]
    )


def get_lock(key: ConversationKey) -> asyncio.Lock:
    """Return the lock used to keep one chat user's turns in order."""
    if key not in conversation_locks:
        conversation_locks[key] = asyncio.Lock()
    return conversation_locks[key]


def split_telegram_text(text: str) -> list[str]:
    """Split long answers at word boundaries to fit Telegram's message limit."""
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

    return chunks or ["I couldn't generate a response. Please try again."]


async def send_response(message: Message, text: str) -> None:
    chunks = split_telegram_text(text)
    for index, chunk in enumerate(chunks):
        markup = main_kb() if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)


async def start_handler(message: Message) -> None:
    await message.answer(
        "Йоу бро! 👋 Добро пожаловать в HS1 VPN!\n\n"
        "Я твой помощник и помогу разобраться за пару минут:\n\n"
        "📲 1. Скачай приложение\n"
        "🔑 2. Подключись по инструкции\n"
        "👨‍💻 3. Если не получится — напиши админу\n\n"
        "Выбирай кнопку ниже или просто напиши свой вопрос!",
        reply_markup=main_kb(),
    )


async def help_handler(message: Message) -> None:
    await message.answer(
        "Напиши вопрос про установку или подключение HS1 VPN — отвечу по-русски.\n\n"
        "/start — открыть меню\n"
        "/reset — очистить историю диалога\n"
        "/help — показать эту справку",
        reply_markup=main_kb(),
    )


async def ask_ai_handler(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Ок, бро! Напиши свой вопрос про HS1 VPN — например, как подключить "
            "приложение или что делать, если возникла проблема.",
            reply_markup=main_kb(),
        )
    await callback.answer()


async def reset_handler(message: Message) -> None:
    if message.from_user is not None:
        key = (message.chat.id, message.from_user.id)
        async with get_lock(key):
            conversations.pop(key, None)
    await message.answer("История диалога очищена.", reply_markup=main_kb())


async def chat_handler(message: Message) -> None:
    if message.text is None or message.from_user is None:
        return
    if groq_client is None:
        logger.error("Groq client was not initialized")
        await message.answer(
            "ИИ-помощник пока не настроен. Попробуй позже или напиши админу @HS1family.",
            reply_markup=main_kb(),
        )
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
            await message.bot.send_chat_action(
                chat_id=message.chat.id,
                action=ChatAction.TYPING,
            )
            completion = await groq_client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
                messages=request_messages,
                max_completion_tokens=MAX_RESPONSE_TOKENS,
            )
            answer = completion.choices[0].message.content
            if not answer or not answer.strip():
                raise ValueError("Groq returned an empty response")
        except RateLimitError:
            logger.warning("Groq rate limit reached")
            await message.answer(
                "Сейчас много запросов. Попробуй ещё раз чуть позже.",
                reply_markup=main_kb(),
            )
            return
        except APITimeoutError:
            logger.warning("Groq request timed out")
            await message.answer(
                "ИИ долго отвечает. Попробуй ещё раз или напиши админу @HS1family.",
                reply_markup=main_kb(),
            )
            return
        except APIConnectionError:
            logger.exception("Could not connect to Groq")
            await message.answer(
                "ИИ-помощник временно недоступен. Попробуй позже или напиши админу @HS1family.",
                reply_markup=main_kb(),
            )
            return
        except APIStatusError as error:
            logger.error("Groq returned HTTP status %s", error.status_code)
            await message.answer(
                "Не получилось получить ответ. Попробуй позже или напиши админу @HS1family.",
                reply_markup=main_kb(),
            )
            return
        except Exception:
            logger.exception("Could not generate a response")
            await message.answer(
                "Бро, ИИ сейчас не отвечает. Попробуй позже или напиши админу @HS1family.",
                reply_markup=main_kb(),
            )
            return

        updated_history = [
            *history,
            {"role": "user", "content": message.text},
            {"role": "assistant", "content": answer.strip()},
        ]
        conversations[key] = updated_history[-MAX_HISTORY_MESSAGES:]
        await send_response(message, answer)


async def main() -> None:
    global groq_client

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    groq_api_key = os.getenv("GROQ_API_KEY")
    missing = [
        name
        for name, value in (
            ("TELEGRAM_BOT_TOKEN", telegram_token),
            ("GROQ_API_KEY", groq_api_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing required secret(s): "
            + ", ".join(missing)
            + ". Add them in Replit Secrets before starting the bot."
        )

    groq_client = AsyncGroq(api_key=groq_api_key, timeout=30.0, max_retries=2)
    bot = Bot(token=telegram_token)
    dispatcher = Dispatcher()
    dispatcher.message.register(start_handler, CommandStart())
    dispatcher.message.register(help_handler, Command("help"))
    dispatcher.message.register(reset_handler, Command("reset"))
    dispatcher.callback_query.register(ask_ai_handler, F.data == "ask_ai")
    dispatcher.message.register(chat_handler, F.text)

    logger.info("Starting Telegram bot with Groq model %s", os.getenv("GROQ_MODEL", DEFAULT_MODEL))
    try:
        # This bot uses long polling; Telegram permits polling or a webhook, not both.
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        await groq_client.close()
        groq_client = None


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
