# Personal Task Manager as a Telegram Bot Powered by ChatGPT

This is a simple task manager Telegram bot that helps you manage your tasks within Telegram chats. It saves, formats, and retrieves your tasks with the help of ChatGPT. ChatGPT does not store any information; it only processes user messages and retrieves task information from DynamoDB.

## Project Stack

- Python
- DynamoDB
- AWS Lambda
- AWS API Gateway
- AWS WAF
- AWS S3
- AWS SAM CLI

This project is deployed on AWS using the AWS SAM CLI tool. Both the REST API endpoints and the Telegram bot are deployed as Lambda functions to optimize costs, while user tasks are stored in DynamoDB.

## Pre-requisites

- Access to AWS account
- AWS command line credentials with write access for Lambda, API Gateway, DynamoDB, WAF and S3
- AWS CLI installed and configured with credentials above
- AWS SAM CLI installed
- Telegram bot registered with BotFather
- Telegram bot token
- ChatGPT API key

## How to Deploy

The deployment process consists of two parts:
- Deploying REST API endpoints
- Deploying the Telegram bot
- Enable webhooks for bot in Telegram

### Deploying REST API Endpoints

1. Navigate to the `app-endpoints/` directory.
2. Build the code:
   ```bash
   sam build
   ```
3. Deploy the code:
   ```bash
   sam deploy --guided
   ```
4. In the AWS Console, verify that the API Gateway and Lambda functions have been created.

### Deploying the Telegram Bot

1. Navigate to the `telegram-bot/` directory.
2. Build the code:
   ```bash
   sam build
   ```
3. Retrieve the following details:
   - Your Telegram bot token.
   - Your ChatGPT token.
   - IDs of authorized users who can use your bot separated by comma (`1234567890,0987654321`).
   - The URL of the API Gateway endpoint. You can find this URL in the AWS Console under **API Gateway > Your API > Stages > Your Stage > Invoke URL**.
4. Deploy the code:
   ```bash
   sam deploy --guided \
     --parameter-overrides \
     "ParameterKey=TelegramBotToken,ParameterValue=your-telegram-token-here ParameterKey=AuthorizedUsers,ParameterValue=id-of-telegram-authorised-users ParameterKey=OpenAiApiKey,ParameterValue=your-chatgpt-token-here ParameterKey=GPTModel,ParameterValue=gpt-4 ParameterKey=GPTSystemPrompt,ParameterValue='You are a helpful assistant that helps users manage their tasks.' ParameterKey=TaskManagerAPIGatewayURL,ParameterValue='url-of-api-gateway-endpoint'"
   ```
   **Note:** Replace the placeholder values (e.g., `your-telegram-token-here`, `id-of-telegram-authorised-users`, etc.) with your actual credentials and parameters.
5. In the AWS Console, verify that the Lambda function and API Gateway for the Telegram bot have been created.

# Register bot as Telegram webhook

1. Get the URL of the API Gateway endpoint for the Telegram bot.
```
API Gateway > Your API > Stages > Your Stage > Invoke URL
```

2. And use following command in the terminal:
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" -d "url=<WEBHOOK_URL>"
```
