# Auto-reply-Tele-

A Telegram bot for **auto-replies** (keyword rules + AI fallback) and **chat
management** (admin commands, logging & analytics). Built with
[`python-telegram-bot`](https://docs.python-telegram-bot.org/) and the Anthropic
Claude API.

This is the **local-first** build — it runs via long polling with a local SQLite
database. Serverless deployment (Vercel + Supabase) is a planned later phase.

## Features

- **Rule-based auto-reply** — keyword and regex rules, stored per chat (or global).
- **AI fallback** — when no rule matches, optionally reply with a Claude-generated
  answer using a per-chat persona/system prompt (prompt-cached).
- **Admin commands** — manage rules, toggles, persona, and broadcasts (gated to
  configured admin user IDs).
- **Logging & analytics** — every message is logged; `/stats` reports totals,
  auto-reply hit rate, and top users.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your numeric user ID via [@userinfobot](https://t.me/userinfobot).
3. Configure environment:

   ```bash
   cp .env.example .env
   # edit .env: set TELEGRAM_BOT_TOKEN, ADMIN_IDS, and (optional) ANTHROPIC_API_KEY
   ```

4. Install dependencies and run:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python -m scripts.run_local
   ```

The bot starts in long-polling mode. Message it on Telegram to test.

## Commands

| Command | Who | Description |
| --- | --- | --- |
| `/start`, `/help` | anyone | Show help |
| `/stats` | anyone | Message + auto-reply stats for the chat |
| `/autoreply on\|off` | admin | Toggle all auto-replies in the chat |
| `/ai on\|off` | admin | Toggle AI fallback replies in the chat |
| `/addrule keyword \| response` | admin | Add a keyword rule |
| `/addregex pattern \| response` | admin | Add a regex rule |
| `/listrules` | admin-ish | List active rules |
| `/delrule <id>` | admin | Delete a rule |
| `/setprompt <text>` | admin | Set the AI persona for the chat |
| `/broadcast <text>` | admin | Message all known chats |

## Configuration

See `.env.example`. Key variables:

- `TELEGRAM_BOT_TOKEN` — required.
- `ADMIN_IDS` — comma-separated numeric IDs allowed to run admin commands.
- `ANTHROPIC_API_KEY` — enables AI replies. Without it, the bot runs rule-only.
- `ANTHROPIC_MODEL` — defaults to `claude-haiku-4-5-20251001` (fast + cheap).
- `DATABASE_PATH` — SQLite file path (default `bot.db`).

## Project layout

```
bot/
  config.py            env/secrets
  db.py                SQLite storage (chats, rules, messages)
  services/ai.py       Claude API wrapper (cached system prompt)
  services/matcher.py  keyword/regex rule matching
  handlers/            auto-reply pipeline + admin commands
  app.py               builds the Application and registers handlers
scripts/run_local.py   long-polling entrypoint
```
