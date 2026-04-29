# -----------------------------------------------------------------------------
# ========================== IMPORTS AND CONSTANTS ============================
# -----------------------------------------------------------------------------
# First Party Imports
import logging
# Third Party Imports
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ================================= HANDLERS ==================================
# -----------------------------------------------------------------------------

async def start(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi <b>{user.first_name}</b>! I'm alive. Send me anything."
    )


async def help_command(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /help."""
    await update.message.reply_text(
        "/start - greet the bot\n"
        "/help  - show this message\n"
        "Or just send any text."
    )


async def handle_text(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle plain text messages."""
    text = update.message.text
    logger.info('Received: "%s"', text)

    # TODO: add logic here
    await update.message.reply_text(f"You said: {text}")


async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle photo messages."""
    photo = update.message.photo[-1]  # largest available size
    file = await context.bot.get_file(photo.file_id)
    logger.info('Photo received: "%s"', file.file_path)

    await update.message.reply_text(
        "Nice photo! Unfortunately I can't do anything with it yet."
    )


async def handle_callback(
    update: Update,
    _: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()  # acknowledge the press

    logger.info('Callback data: "%s"', query.data)
    await query.edit_message_text(f"Button pressed: {query.data}")


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log errors."""
    logger.error(
        "Update %s caused error: %s", update, context.error, exc_info=True
    )


# -----------------------------------------------------------------------------
# =============================== ENTRY POINT =================================
# -----------------------------------------------------------------------------

def start_telebot(bot_token: str) -> None:
    logger.info("Starting bot with token: %s", bot_token[:4] + "****")
    app = Application.builder().token(bot_token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Messages
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Errors
    app.add_error_handler(error_handler)

    logger.info("Bot started and polling for updates")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
