import asyncio
import json
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from envs import env
from chatgpt import chat_with_gpt

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = env("TELEGRAM_BOT_TOKEN")
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Authorized users to interact with the bot
AUTHORIZED_USERS = env("AUTHORIZED_USERS")
AUTHORIZED_USERS = [int(user_id.strip()) for user_id in AUTHORIZED_USERS.split(",") if user_id.strip()]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    await update.message.reply_text("Welcome to Task Manager Bot! Send me your task queries.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages (that are not commands)."""
    logging.info(f"Received message in Telegram: {update.to_dict()}")
    user_id = update.message.from_user.id
    
    if user_id not in AUTHORIZED_USERS:
        logging.warning(f"Unauthorized user: {update.message.from_user}")
        return

    user_input = update.message.text
    api_response = chat_with_gpt(user_id, user_input)
    await update.message.reply_text(
        api_response.get("response", "I'm not sure how to respond to that."),
        parse_mode="Markdown"
    )

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


def lambda_handler(event, context):
    """AWS Lambda handler for processing Telegram webhook updates."""
    logging.info(f"Received event: {json.dumps(event)}")
    print(f"Event: {json.dumps(event)}")
    try:
        # Parse the incoming request body
        body = json.loads(event["body"])

        # Convert the raw update JSON into a Telegram Update object
        update = Update.de_json(body, application.bot)

        # Ensure the application is initialized only once
        loop = asyncio.get_event_loop()
        if not application._initialized:  # Prevent multiple initializations
            loop.run_until_complete(application.initialize())

        # Process the update within the existing event loop
        loop.run_until_complete(application.process_update(update))
        
        return {"statusCode": 200, "body": "OK"}
    except Exception as e:
        logging.error(f"Error processing update: {e}")
        return {"statusCode": 500, "body": "Internal Server Error"}
