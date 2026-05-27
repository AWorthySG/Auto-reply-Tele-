# Auto-reply-Tele-

A personal Telegram **auto-reply userbot**. It logs in as *your own* account
(using Telethon) and automatically replies to **private chats and groups** when
you're away — using keyword-based rules with a default fallback.

> ### Why a "userbot" and not a normal bot?
> A normal BotFather bot **cannot** reply on your behalf. Bots only see messages
> sent directly to them, and they can't post as *you* in groups. To auto-reply
> for your personal account across private chats **and** groups, the only option
> is a *userbot*: a client that logs in as you via Telegram's user API.
>
> ⚠️ **Read this:** Automating a personal account ("self-bot") is a gray area in
> Telegram's Terms of Service. Heavy or spammy automation can get an account
> limited or banned. This tool is built to be conservative — it only replies
> when you're away, replies at most once per chat per cooldown window, and in
> groups only when you're @mentioned or replied to. Use it on low volumes, keep
> the cooldown sensible, and don't use it to mass-message. You accept the risk.

## How it behaves

- **Away-only:** replies only after you've been inactive (sent no message
  yourself) for `away.inactivity_minutes`. The moment you send any message, the
  away timer resets.
- **Keyword rules:** the first rule whose keywords appear in the incoming
  message wins; otherwise it uses `default_reply` (or stays silent if you set
  that to null).
- **Cooldown:** after replying to a chat, it stays silent there for
  `cooldown.minutes` to avoid loops/spam.
- **Groups:** by default only replies when you're @mentioned or someone replies
  to your message. Never replies to channels, other bots, or service messages.

## Setup

### 1. Get your API credentials

1. Go to <https://my.telegram.org> and log in with your phone number.
2. Open **API development tools** and create an app (any name).
3. Copy the **api_id** and **api_hash**.

### 2. Install

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

> If installing Telethon fails while building `pyaes` with
> `AttributeError: install_layout` (a setuptools quirk on some Linux distros),
> retry with `SETUPTOOLS_USE_DISTUTILS=stdlib pip install -r requirements.txt`.

### 3. Configure

```bash
cp .env.example .env          # fill in TELEGRAM_API_ID / TELEGRAM_API_HASH
cp config.example.yaml config.yaml   # edit your rules, timings, ignore lists
```

`.env` and `config.yaml` are gitignored — they hold your secrets and settings.

### 4. Log in once

```bash
python login.py
```

This prompts for the code Telegram sends you (and your 2FA password if you have
one) and creates a `autoreply.session` file so future runs are unattended.

### 5. Run

```bash
python -m autoreply.main
```

Leave it running on a machine that stays on (your always-on PC, a Raspberry Pi,
or a small VPS). When you stop it, auto-replies stop. For an unattended
deployment that restarts itself, see **Deployment** below.

### Try it without connecting (dry run)

See exactly what it would reply to sample messages, with no login or network:

```bash
python -m autoreply.main --dry-run
```

## Configuration reference

See `config.example.yaml` — every option is commented. Key ones:

| Setting | Meaning |
| --- | --- |
| `away.inactivity_minutes` | How long with no activity from you before it's "away". |
| `cooldown.minutes` | Min time between auto-replies to the same chat. |
| `private_chats.enabled` / `groups.enabled` | Toggle each surface. |
| `groups.only_when_mentioned` | If true (recommended), only reply in groups when @mentioned or replied to. |
| `rules` | List of `{ keywords: [...], reply: "..." }`, evaluated top to bottom. |
| `default_reply` | Used when no rule matches; set to `null` to stay silent. |
| `signature` | Optional text appended to every reply. |
| `ignore.user_ids` / `ignore.chat_ids` | Never auto-reply these. |

## Deployment

The bot only runs while its process is alive, so for real use run it under a
supervisor that restarts it on crashes/reboots. Two ready-made options:

### systemd (VPS / Linux host)

1. Place the project at `/opt/auto-reply-tele`, create the venv, and add `.env`
   + `config.yaml`.
2. Log in once **as the service user** so the session file exists:
   `sudo -u autoreply /opt/auto-reply-tele/.venv/bin/python login.py`
3. Install the unit (edit the `User`/paths inside first if needed):
   ```bash
   sudo cp deploy/autoreply.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now autoreply
   journalctl -u autoreply -f      # watch logs
   ```

### Docker

Secrets come from `.env`; `config.yaml` is bind-mounted read-only so you can
edit it on the host; the login session + state persist in a named volume.

```bash
cp .env.example .env                         # fill in API id/hash
cp config.example.yaml config.yaml           # then edit your rules
docker compose run --rm autoreply python login.py   # one-time interactive login
docker compose up -d                         # start (auto-restarts)
docker compose logs -f                        # watch logs
```

The one-time login writes the session into the `autoreply-data` volume, so it
survives restarts and rebuilds and only needs to be done once.

## Development

```bash
pip install -r requirements.txt pytest
python -m pytest          # unit tests for the matching / away / cooldown logic
```

The decision logic lives in `autoreply/engine.py` as a pure function
(`decide_reply`) with no Telegram dependencies, so it's fully unit-tested. The
Telethon layer in `autoreply/main.py` is a thin adapter around it.

## Files

| Path | Purpose |
| --- | --- |
| `autoreply/config.py` | Load + validate YAML config. |
| `autoreply/matcher.py` | Keyword → reply matching. |
| `autoreply/state.py` | Persisted away timer + per-chat cooldown (`state.json`). |
| `autoreply/engine.py` | Pure `decide_reply()` decision logic. |
| `autoreply/main.py` | Telethon client, event handlers, `--dry-run`. |
| `login.py` | One-time interactive login. |
