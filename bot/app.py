import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from . import config, db
from .handlers import admin, auto_reply


def build_application() -> Application:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )

    db.init_db()

    app = ApplicationBuilder().token(config.require_token()).build()

    app.add_handler(CommandHandler(["start", "help"], admin.start))
    app.add_handler(CommandHandler("autoreply", admin.autoreply))
    app.add_handler(CommandHandler("ai", admin.ai_toggle))
    app.add_handler(CommandHandler("addrule", admin.addrule))
    app.add_handler(CommandHandler("addregex", admin.addregex))
    app.add_handler(CommandHandler("delrule", admin.delrule))
    app.add_handler(CommandHandler("listrules", admin.listrules))
    app.add_handler(CommandHandler("setprompt", admin.setprompt))
    app.add_handler(CommandHandler("stats", admin.stats))
    app.add_handler(CommandHandler("broadcast", admin.broadcast))

    # Any non-command text message goes through the auto-reply pipeline.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply.on_message))

    return app
