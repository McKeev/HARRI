# --------------------------------------------------------------------------------------
# IMPORTS AND LOGGING
# --------------------------------------------------------------------------------------
# First Party Imports
import logging
import time

# Third Party Imports
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Local Imports
from harri.memory import User, UserConflictError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# COMMAND HANDLERS
# --------------------------------------------------------------------------------------


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start. This is the first command users will see,
    so we can use it to greet them and give basic instructions."""
    # Type guard
    if update.message is None or update.effective_user is None:
        return

    # Take first name as default name
    name = update.effective_user.first_name

    # Get user id
    try:
        user = await User.register(
            telegram_id=update.effective_user.id,
            name=name,
        )
        msg = (
            "Welcome Sir,\n"
            "I am H.A.R.R.I., your personal assistant.\n\n"
            "As I'm still in alpha stage, I have limited capabalities,"
            "but I'm here to help you as best as I can.\n"
            f"\nI've registered you in my system under the name `{user.name}`. "
            "You can change this name later with the /setname command "
            "if you prefer something else."
            + "\n\nYou can use /help to see available commands."
            "\n\nLooking forward to assisting you!"
        )

        # Send the info message
        await update.message.reply_text(msg, parse_mode="Markdown")

        # Send a standalone emoji to trigger Telegram's full-screen confetti explosion!
        await update.message.reply_text("🎉")
    except UserConflictError:
        await update.message.reply_text(
            "It appears you are already registered. Use /userinfo to see your info."
        )


async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    # Type guard
    if update.message is None:
        return

    await update.message.reply_text(
        "/start - greet the bot and register\n"
        "/help  - show this message\n"
        "/userinfo - show your registered info\n"
        "/setname <new_name> - change your registered name\n"
        "/link_portfolio <portfolio_ticker> - link a portfolio to your account)\n"
        "/delete_account - delete your account and all data\n"
        "\nOr just send any text to chat with H.A.R.R.I (Not implemented yet)."
    )


async def userinfo(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /userinfo."""
    # Type guard
    if update.message is None or update.effective_user is None:
        return
    user = await User.from_tele_id(update.effective_user.id)
    if user is None:
        await update.message.reply_text(
            "You are not registered yet. Use /start to register."
        )
        return
    await update.message.reply_text(await user.info(), parse_mode="Markdown")


async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setname <new_name>."""
    # Type guard
    if update.message is None or update.effective_user is None or context.args is None:
        return

    new_name = " ".join(context.args).strip()
    if not new_name:
        await update.message.reply_text("Please provide a valid name after /setname.")
        return

    user = await User.from_tele_id(update.effective_user.id)
    if user is None:
        await update.message.reply_text(
            "You are not registered yet. Use /start to register."
        )
        return

    user.name = new_name
    if await user.save():
        await update.message.reply_text(
            f"Your name has been updated to `{new_name}`.", parse_mode="Markdown"
        )
    else:
        # Should not happen!
        raise RuntimeError("Undefined error occurred while saving user name change.")


async def link_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /link_portfolio <portfolio_ticker>."""
    # Type guard
    if update.message is None or update.effective_user is None or context.args is None:
        return

    if context.args is None or len(context.args) != 1:
        await update.message.reply_text(
            "Please provide exactly one portfolio ticker after /link_portfolio."
        )
        return

    ticker = context.args[0].strip().upper()

    user = await User.from_tele_id(update.effective_user.id)
    if user is None:
        await update.message.reply_text(
            "You are not registered yet. Use /start to register."
        )
        return

    user.portfolio = ticker
    if await user.save():
        await update.message.reply_text(
            f"Your associated portfolio has been updated to `{ticker}`.",
            parse_mode="Markdown",
        )
    else:
        # Should not happen!
        raise RuntimeError("Undefined error occurred while saving user name change.")


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_account."""
    # Type guard
    if (
        update.message is None
        or update.effective_user is None
        or context.user_data is None
    ):
        return

    if (await User.from_tele_id(update.effective_user.id)) is None:
        await update.message.reply_text("You are not registered.")
        return
    # Get confirmation with inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("Yes, Delete", callback_data="confirm_delete"),
            InlineKeyboardButton("Cancel", callback_data="cancel_delete"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ Are you sure you want to delete your account? This cannot be undone.\n\n"
        "_You have 10 seconds to confirm._",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    # Store the timestamp in user_data to check for expiration later
    context.user_data["delete_request_time"] = time.time()


async def delete_account_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the inline keyboard callback for account deletion (`delete_account`)."""
    query = update.callback_query

    # Type guard
    if query is None or update.effective_user is None:
        return

    await query.answer()

    if query.data not in ("confirm_delete", "cancel_delete"):
        return

    request_time = 0
    if context.user_data is not None:
        request_time = context.user_data.get("delete_request_time", 0)

    # Check if 10 seconds have passed
    if time.time() - request_time > 10:
        await query.edit_message_text(
            "⏳ This delete request has expired (10 seconds passed). "
            "Please run /delete_account again."
        )
        return

    if query.data == "cancel_delete":
        await query.edit_message_text("🙅‍♂️ Account deletion cancelled.")
        return

    if query.data == "confirm_delete":
        user = await User.from_tele_id(update.effective_user.id)
        if user:
            await user.delete()
            await query.edit_message_text(
                "🗑️ Your account and all associated data have been deleted."
            )
        else:
            await query.edit_message_text("Account already deleted or not found.")


# --------------------------------------------------------------------------------------
# MESSAGE, KEYBOARD AND ERROR HANDLERS
# --------------------------------------------------------------------------------------


async def handle_text(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages."""
    # Type guard
    if update.message is None:
        return

    text = update.message.text
    logger.info('Received: "%s"', text)

    # TODO: add logic here
    await update.message.reply_text(f"You said: {text}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages."""
    # Type guard
    if update.message is None:
        return

    photo = update.message.photo[-1]  # largest available size
    file = await context.bot.get_file(photo.file_id)
    logger.info('Photo received: "%s"', file.file_path)

    await update.message.reply_text(
        "Nice photo! Unfortunately I can't do anything with it yet."
    )


async def handle_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    # Type guard
    if update.callback_query is None:
        return

    query = update.callback_query
    await query.answer()  # acknowledge the press

    logger.warning('Unhandled callback data received: "%s"', query.data)

    await query.answer(
        text="This button is no longer valid or an error occurred.",
        show_alert=False,  # False makes it a temporary toast notification
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error("Update %s caused error: %s", update, context.error, exc_info=True)


# --------------------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------------------


def start_telebot(bot_token: str) -> None:
    logger.info("Starting bot with token: %s", bot_token[:4] + "****")
    app = Application.builder().token(bot_token).build()

    # Commands userinfo
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("setname", setname))
    app.add_handler(CommandHandler("delete_account", delete_account))
    app.add_handler(CommandHandler("link_portfolio", link_portfolio))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Inline keyboard callbacks
    app.add_handler(
        CallbackQueryHandler(
            delete_account_callback,
            pattern="^(confirm_delete|cancel_delete)$",
        )
    )
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Errors
    app.add_error_handler(error_handler)

    logger.info("Bot started and polling for updates")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
