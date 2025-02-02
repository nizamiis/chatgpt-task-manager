from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from envs import env
import logging
from chatgpt import chat_with_gpt


logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = env("TELEGRAM_BOT_TOKEN")
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Authorized users to interact with the bot
AUTHORIZED_USERS = env("AUTHORIZED_USERS")
AUTHORIZED_USERS = [int(user_id.strip()) for user_id in AUTHORIZED_USERS.split(",") if user_id.strip()]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Task Manager Bot! Send me your task queries.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Received message in Telegram: {update.to_dict()}")
    user_id = update.message["from"]["id"]
    if user_id not in AUTHORIZED_USERS:
        logging.warning(f"Unauthorized user: {update.message['from']}")
        return

    user_input = update.message.text
    api_response = chat_with_gpt(user_id, user_input)
    await update.message.reply_text(api_response.get("response", "I'm not sure how to respond to that."), parse_mode="Markdown")


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


if __name__ == "__main__":
    print("Starting Task Management Application...")
    application.run_polling()
