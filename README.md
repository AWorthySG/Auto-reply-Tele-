# Auto-reply-Tele-

Automatically replies to private messages sent to your personal Telegram account.

A normal Telegram bot (created with @BotFather) can only answer messages sent to the bot itself. To answer messages sent to *you*, this script logs in as your account through the Telegram client API (a "userbot") using [Telethon](https://docs.telethon.dev).

## Behaviour

- Replies only in private one-to-one chats. Groups and channels are ignored.
- Ignores bots, your own messages and Telegram's service account (login codes).
- Replies at most once per chat per `COOLDOWN_MINUTES` (default 60).
- If you send a message in a chat yourself, the cooldown restarts, so the script stays silent while you are talking.
- Optional: `SKIP_CONTACTS=true` limits replies to people not in your contacts.

## Setup

1. Go to <https://my.telegram.org>, log in, open **API development tools** and create an app. Copy the `api_id` and `api_hash`.
2. Install:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
3. Put your `API_ID`, `API_HASH` and reply text in `.env`.
4. Run:
   ```bash
   python autoreply.py
   ```
   On the first run you enter your phone number, the login code Telegram sends you, and your 2FA password if you have one. This creates `autoreply.session`, so later runs log in without prompts.

The script only replies while it is running. To keep it on permanently, run it on an always-on machine or small server (for example with `systemd`, `tmux` or `screen`).

## Commands

Send these in your **Saved Messages** chat:

| Command | Effect |
|---|---|
| `/autoreply status` | Show whether auto-reply is on and the current message |
| `/autoreply on` | Turn auto-reply on |
| `/autoreply off` | Turn auto-reply off |
| `/autoreply set <text>` | Change the reply text until the script restarts |

## Security

- `autoreply.session` gives full access to your Telegram account. Never share or commit it. `.gitignore` already excludes it and `.env`.
- To revoke access: Telegram **Settings → Devices**, terminate the session.
- Keep the cooldown on. Sending many identical automated messages can get an account rate-limited.

## Alternative: Telegram Business (Premium)

If you have Telegram Premium, **Settings → Telegram Business → Away Message** offers a built-in auto-reply without any code. Business also lets you connect a @BotFather bot to your account for custom logic, without sharing your login session.
