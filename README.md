# HS1 VPN Telegram AI Bot

A Russian-language HS1 VPN support bot built with Python, aiogram 3, and Groq.
Its menu links to the Android app and setup instructions. The AI assistant uses
the `llama-3.3-70b-versatile` model at temperature `0.9`, keeps the latest 15
messages per person in memory, and provides `/start`, `/help`, and `/reset`.

## HS1 VPN links

- Android app: https://github.com/safarovclub-ops/HS1VPN/releases/download/v1.0/HSOneVPN12.apk
- Setup instructions: https://t.me/HS1group/60
- Channel: https://t.me/HS1group
- Support: https://t.me/HS1family

The inline menu includes buttons for all four links. Replies use a casual,
concise Russian tone; they avoid claiming unverified troubleshooting fixes.

## Run on Replit

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy its
   token.
2. Add `TELEGRAM_BOT_TOKEN` and `GROQ_API_KEY` in **Tools → Secrets**.
3. Start the **Telegram AI Bot** workflow.

The bot reads secrets directly from the environment. Do not put tokens in source
files or commit a `.env` file. On startup it removes any webhook configured for
this Telegram bot so long polling can work; queued Telegram updates are kept.

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Token created with @BotFather |
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `LOG_LEVEL` | No | `INFO` | Python log level |

Conversation history is kept in memory and is cleared when the bot restarts.
Use `/reset` to clear one person's history without restarting.

## Local development

Install dependencies from `requirements.txt`, set the two required environment
variables, then run:

```sh
python main.py
```
