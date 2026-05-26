import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from .. import config, db
from ..services import ai

log = logging.getLogger(__name__)

HELP_TEXT = (
    "*Auto-reply bot*\n"
    "/start, /help — show this message\n"
    "/stats — message + auto-reply stats for this chat\n\n"
    "*Admin only*\n"
    "/autoreply on|off — toggle all auto-replies here\n"
    "/ai on|off — toggle AI fallback replies here\n"
    "/addrule keyword | response — add a keyword rule\n"
    "/addregex pattern | response — add a regex rule\n"
    "/listrules — list active rules\n"
    "/delrule <id> — delete a rule by id\n"
    "/setprompt <text> — set the AI persona for this chat\n"
    "/broadcast <text> — send a message to all known chats"
)


def admin_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None or user.id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("Sorry, that command is admin-only.")
            return
        return await func(update, context)

    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat:
        db.ensure_chat(chat.id, chat.title)
    await update.effective_message.reply_text(HELP_TEXT, parse_mode="Markdown")


def _parse_on_off(args: list[str]) -> bool | None:
    if not args:
        return None
    val = args[0].strip().lower()
    if val in {"on", "true", "1", "yes"}:
        return True
    if val in {"off", "false", "0", "no"}:
        return False
    return None


@admin_only
async def autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _parse_on_off(context.args)
    if state is None:
        await update.effective_message.reply_text("Usage: /autoreply on|off")
        return
    db.set_chat_flag(update.effective_chat.id, "autoreply_enabled", int(state))
    await update.effective_message.reply_text(
        f"Auto-reply is now {'ON' if state else 'OFF'} for this chat."
    )


@admin_only
async def ai_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _parse_on_off(context.args)
    if state is None:
        await update.effective_message.reply_text("Usage: /ai on|off")
        return
    if state and not ai.is_configured():
        await update.effective_message.reply_text(
            "ANTHROPIC_API_KEY is not set, so AI replies can't be enabled yet."
        )
        return
    db.set_chat_flag(update.effective_chat.id, "ai_enabled", int(state))
    await update.effective_message.reply_text(
        f"AI fallback replies are now {'ON' if state else 'OFF'} for this chat."
    )


async def _add_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, is_regex: bool) -> None:
    raw = " ".join(context.args)
    if "|" not in raw:
        kind = "pattern" if is_regex else "keyword"
        cmd = "addregex" if is_regex else "addrule"
        await update.effective_message.reply_text(f"Usage: /{cmd} {kind} | response")
        return
    pattern, response = (part.strip() for part in raw.split("|", 1))
    if not pattern or not response:
        await update.effective_message.reply_text("Both a pattern and a response are required.")
        return
    rule_id = db.add_rule(update.effective_chat.id, pattern, response, is_regex=is_regex)
    await update.effective_message.reply_text(f"Added rule #{rule_id}.")


@admin_only
async def addrule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _add_rule(update, context, is_regex=False)


@admin_only
async def addregex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _add_rule(update, context, is_regex=True)


@admin_only
async def delrule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Usage: /delrule <id>")
        return
    rule_id = int(context.args[0])
    ok = db.delete_rule(rule_id, update.effective_chat.id)
    await update.effective_message.reply_text(
        f"Deleted rule #{rule_id}." if ok else f"No rule #{rule_id} found for this chat."
    )


async def listrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rules = db.list_rules(update.effective_chat.id)
    if not rules:
        await update.effective_message.reply_text("No rules set for this chat.")
        return
    lines = []
    for r in rules:
        kind = "regex" if r["is_regex"] else "kw"
        scope = "global" if r["chat_id"] is None else "chat"
        lines.append(f"#{r['id']} [{kind},{scope}] {r['pattern']} → {r['response']}")
    await update.effective_message.reply_text("\n".join(lines))


@admin_only
async def setprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.effective_message.reply_text("Usage: /setprompt <persona text>")
        return
    db.set_system_prompt(update.effective_chat.id, prompt)
    await update.effective_message.reply_text("AI persona updated for this chat.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = db.chat_stats(update.effective_chat.id)
    top = "\n".join(f"  {who}: {n}" for who, n in s["top_users"]) or "  (none yet)"
    await update.effective_message.reply_text(
        f"Messages logged: {s['total']}\n"
        f"Auto-replied: {s['replied']} (rule: {s['rule_replies']}, ai: {s['ai_replies']})\n"
        f"Top users:\n{top}"
    )


@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Usage: /broadcast <message>")
        return
    sent = 0
    for chat_id in db.all_chat_ids():
        try:
            await context.bot.send_message(chat_id, text)
            sent += 1
        except Exception:  # noqa: BLE001 - skip chats the bot can't message
            log.warning("Broadcast to %s failed", chat_id)
    await update.effective_message.reply_text(f"Broadcast sent to {sent} chat(s).")
