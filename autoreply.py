"""Auto-reply to private Telegram messages sent to your own account.

Runs as a "userbot": it logs in with your phone number through the
Telegram client API (MTProto) and replies on your behalf.

Control it from your Saved Messages chat:
    /autoreply on | off | status
    /autoreply set <new reply text>
"""

import logging
import os
import time

from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_NAME = os.getenv("SESSION_NAME", "autoreply")
REPLY_MESSAGE = os.getenv(
    "REPLY_MESSAGE",
    "Hi, I am away at the moment. I will reply as soon as I can.",
)
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_MINUTES", "60")) * 60
SKIP_CONTACTS = os.getenv("SKIP_CONTACTS", "false").lower() == "true"

# Telegram's official service account (login codes, security notices).
TELEGRAM_SERVICE_ID = 777000

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO
)
log = logging.getLogger("autoreply")

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
state = {"enabled": True, "message": REPLY_MESSAGE}
# chat_id -> monotonic time of the last message you (or the bot) sent there
last_outgoing = {}


def in_cooldown(chat_id):
    last = last_outgoing.get(chat_id)
    return last is not None and time.monotonic() - last < COOLDOWN_SECONDS


@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def on_private_message(event):
    if not state["enabled"] or in_cooldown(event.chat_id):
        return

    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False) or sender.is_self:
        return
    if sender.id == TELEGRAM_SERVICE_ID:
        return
    if SKIP_CONTACTS and getattr(sender, "contact", False):
        return

    await event.reply(state["message"])
    last_outgoing[event.chat_id] = time.monotonic()
    log.info("Auto-replied to %s (id %s)", sender.first_name, sender.id)


@client.on(events.NewMessage(outgoing=True, func=lambda e: e.is_private))
async def on_own_message(event):
    # Replying manually starts the cooldown, so the bot stays quiet
    # while you are in the conversation yourself.
    last_outgoing[event.chat_id] = time.monotonic()


@client.on(events.NewMessage(outgoing=True, chats="me", pattern=r"^/autoreply\b"))
async def on_command(event):
    parts = event.raw_text.split(maxsplit=2)
    action = parts[1].lower() if len(parts) > 1 else "status"

    if action == "on":
        state["enabled"] = True
    elif action == "off":
        state["enabled"] = False
    elif action == "set" and len(parts) == 3:
        state["message"] = parts[2]
    elif action != "status":
        await event.reply("Usage: /autoreply on | off | status | set <text>")
        return

    status = "ON" if state["enabled"] else "OFF"
    await event.reply(f"Auto-reply is {status}.\nMessage:\n{state['message']}")


def main():
    client.start()  # prompts for phone number and login code on first run
    log.info("Auto-reply running. Send /autoreply status to Saved Messages.")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
