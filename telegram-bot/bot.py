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

# ---------------------------------------------------------------------
# Environment Variable Parsing
# ---------------------------------------------------------------------
def get_telegram_token():
    """Retrieve Telegram Bot token from environment."""
    return env("TELEGRAM_BOT_TOKEN")

def get_authorized_users():
    """
    Retrieve a list of authorized user IDs (integers) from a comma-separated
    environment variable.
    """
    raw_users = env("AUTHORIZED_USERS")
    user_ids = []
    if raw_users:
        user_ids = [
            int(u.strip()) for u in raw_users.split(",") if u.strip()
        ]
    return user_ids

TELEGRAM_TOKEN = get_telegram_token()
AUTHORIZED_USERS = get_authorized_users()

# Build the Telegram application with the provided token
application = Application.builder().token(TELEGRAM_TOKEN).build()


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /start command. Greets the user with a welcome message.
    """
    await update.message.reply_text("Welcome to the Task Manager Bot! Send me your task queries.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for all non-command text messages. Only authorized users can receive responses.
    """
    user_id = update.effective_user.id if update.effective_user else None
    message_text = update.message.text if update.message else ""

    logging.info(f"Received message from user {user_id}: {message_text}")

    if user_id not in AUTHORIZED_USERS:
        logging.warning(f"Unauthorized access attempt from user_id: {user_id}")
        return  # Silently return or optionally notify them with a message

    # Interact with ChatGPT / GPT-based function
    response = chat_with_gpt(user_id, message_text)

    await update.message.reply_text(
        response.get("response", "I'm not sure how to respond to that."),
        parse_mode="Markdown"
    )

# Register handlers in the application
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ---------------------------------------------------------------------
# AWS Lambda Handler
# ---------------------------------------------------------------------
def lambda_handler(event, context):
    """
    AWS Lambda handler that processes incoming webhook updates from Telegram.
    This function is triggered when the AWS API Gateway endpoint receives a POST request.
    """
    logging.info("Received Lambda event.")
    logging.debug(f"Event payload: {json.dumps(event)}")

    try:
        # Parse the incoming request body
        body = json.loads(event["body"])

        # Convert the raw update JSON into a Telegram Update object
        update = Update.de_json(body, application.bot)

        # Initialize the application once
        loop = asyncio.get_event_loop()
        if not application._initialized:
            loop.run_until_complete(application.initialize())

        # Process the update with the existing event loop
        loop.run_until_complete(application.process_update(update))

        return {"statusCode": 200, "body": "OK"}

    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}
