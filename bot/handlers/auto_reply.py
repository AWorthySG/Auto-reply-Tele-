import logging

from telegram import Update
from telegram.ext import ContextTypes

from .. import db
from ..services import ai, matcher

log = logging.getLogger(__name__)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle every non-command text message: log it, then auto-reply if enabled."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or message.text is None:
        return

    chat_row = db.ensure_chat(chat.id, chat.title or (chat.full_name if hasattr(chat, "full_name") else None))
    text = message.text

    reply_type = None
    replied = False

    if chat_row["autoreply_enabled"]:
        rule = matcher.find_match(chat.id, text)
        if rule is not None:
            await message.reply_text(rule["response"])
            replied = True
            reply_type = "rule"
        elif chat_row["ai_enabled"] and ai.is_configured():
            try:
                answer = await ai.generate_reply(text, chat_row["system_prompt"])
                await message.reply_text(answer)
                replied = True
                reply_type = "ai"
            except Exception:  # noqa: BLE001 - never crash the handler on AI failure
                log.exception("AI reply failed for chat %s", chat.id)

    db.log_message(
        chat_id=chat.id,
        user_id=user.id if user else None,
        username=user.username if user else None,
        text=text,
        was_auto_replied=replied,
        reply_type=reply_type,
    )
