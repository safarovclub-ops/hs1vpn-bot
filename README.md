# Groq Telegram AI Bot

A Telegram chatbot built with Python, aiogram 3, and Groq. It supports private
and group chats, keeps a short conversation context for each person in memory,
and provides `/start`, `/help`, and `/reset` commands.

## Run on Replit

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy its
   token.
2. Add `TELEGRAM_BOT_TOKEN` and `GROQ_API_KEY` in **Tools → Secrets**.
3. Start the **Telegram AI Bot** workflow.

The bot reads secrets directly from the environment. Do not put tokens in source
files or commit a `.env` file.

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Token created with @BotFather |
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq chat model |
| `LOG_LEVEL` | No | `INFO` | Python log level |

Conversation history is kept in memory and is cleared when the bot restarts.
Use `/reset` to clear one person's history without restarting.

## Local development

Install dependencies from `requirements.txt`, set the two required environment
variables, then run:

```sh
python bot.py
```
