from curses.ascii import isdigit
import logging
from typing import Dict
import hashlib

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

ADD_ACC, ENTER_PHONE, ENTER_PASS, LOGGED_IN, TYPING_REPLY, TYPING_CHOICE = range(6)

start_keyboard = [
    ["Add New Account"],
    # ["Number of siblings", "Something else..."],
    # ["Done"],
]
start_markup = ReplyKeyboardMarkup(start_keyboard, input_field_placeholder="Choose the option...", one_time_keyboard=True)

logged_keyboard = [
    ["Balance", "Competition"],
    ["Bet record", "Log out"],
]
logged_markup = ReplyKeyboardMarkup(logged_keyboard, input_field_placeholder="Choose the option...", resize_keyboard=True)

def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation, display any stored data and ask user for input."""
    if context.user_data and ("phone" in context.user_data) and ("pass" in context.user_data) and context.user_data["phone"] and context.user_data["pass"]:
        reply_text = "You're already added account.\nPlease tell what you want me to do."
        
        await update.message.reply_text(reply_text, reply_markup=logged_markup)
        return LOGGED_IN
    else:
        reply_text = "Hi! My name is Mr.OL_BOT.\nPlease choose the option!"
        
        await update.message.reply_text(reply_text, reply_markup=start_markup)
        return ADD_ACC


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for info about the selected predefined choice."""
    text = update.message.text.lower()
    context.user_data["choice"] = text
    if context.user_data.get(text):
        reply_text = (
            f"Your {text}? I already know the following about that: {context.user_data[text]}"
        )
    else:
        reply_text = f"Your {text}? Yes, I would love to hear about that!"

    await update.message.delete()
    await update.message.reply_text(reply_text)

    return TYPING_REPLY

async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Please enter your phone number:"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return_value: int
    reply_text: str
    text = update.message.text

    if text.isdigit():
        context.user_data["phone"] = text
        reply_text = "Please enter your password:"

        return_value = ENTER_PASS
    else:
        reply_text = "Phone number is invalid!\nPlease Enter your phone number:"

        return_value = ENTER_PHONE

    await update.message.reply_text(reply_text)

    return return_value

async def enter_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    context.user_data["pass"] = hashlib.md5((text+"GG").encode('utf-8')).hexdigest()

    reply_text = "Your account is successfully added!\nPlease tell me what you want me to do."
    await update.message.reply_text(reply_text, reply_markup=logged_markup)

    return LOGGED_IN

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_text = (
        "Your account balance is:\n"
        "Available: $1000\n"
        "Block: $500\n"
        "Total: $1500"
        )
    await update.message.reply_text(reply_text, reply_markup=logged_markup)

async def log_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["phone"] = ""
    context.user_data["pass"] = ""
    reply_text = "You're successfully log out."
    
    await update.message.reply_text(reply_text, reply_markup=start_markup)
    return ADD_ACC

async def custom_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for a description of a custom category."""
    await update.message.reply_text(
        'Alright, please send me the category first, for example "Most impressive skill"'
    )

    return TYPING_CHOICE


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""
    text = update.message.text
    category = context.user_data["choice"]
    context.user_data[category] = text.lower()
    del context.user_data["choice"]

    await update.message.reply_text(
        "Neat! Just so you know, this is what you already told me:"
        f"{facts_to_str(context.user_data)}"
        "You can tell me more, or change your opinion on something.",
        reply_markup=markup,
    )

    return CHOOSING


async def show_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the gathered info."""
    await update.message.reply_text(
        f"This is what you already told me: {facts_to_str(context.user_data)}"
    )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""
    if "choice" in context.user_data:
        del context.user_data["choice"]

    await update.message.reply_text(
        f"I learned these facts about you: {facts_to_str(context.user_data)}Until next time!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath="conversationbot")
    application = Application.builder().token("5629058980:AAF5gNsKvg26YmSMUYhEvkXTBGRpE7XDx5M").persistence(persistence).build()

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ADD_ACC: [
                MessageHandler(
                    # filters.Regex("^(Age|Favourite colour|Number of siblings)$"), regular_choice
                    filters.Regex("^(Add New Account)$"), add_account
                )
            ],
            ENTER_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, enter_phone
                )
            ],
            ENTER_PASS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, enter_pass
                )
            ],
            LOGGED_IN: [
                MessageHandler(
                    filters.Regex("^Balance$"), check_balance
                ),
                MessageHandler(
                    filters.Regex("^Log out$"), log_out
                )
            ],
            TYPING_CHOICE: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")), regular_choice
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
        name="my_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)

    show_data_handler = CommandHandler("show_data", show_data)
    application.add_handler(show_data_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()