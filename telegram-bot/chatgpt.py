import openai
import logging
import requests
import json
from fastapi import HTTPException
import boto3
from requests_aws4auth import AWS4Auth
from envs import env


logging.basicConfig(level=logging.INFO)

# AWS SigV4 Configuration
# Get credentials from the Lambda execution environment
session = boto3.Session()
credentials = session.get_credentials().get_frozen_credentials()

REGION = env("DEPLOYMENT_REGION")
SERVICE = "execute-api"
aws_auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    SERVICE,
    session_token=credentials.token
)

# API Gateway base URL
API_BASE_URL = env("TASK_MANAGER_API_GATEWAY_URL")

# GPT configuration
GPT_MODEL = env("GPT_MODEL")
SYSTEM_PROMPT = env("GPT_SYSTEM_PROMPT")
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_task_list",
            "description": "Automatically save the task list with all tasks of the user to DB whenever there are any changes.",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": [
                    "task_list"
                ],
                "properties": {
                    "task_list": {
                        "type": "string",
                        "description": "Formatted task list."
                    },
                },
                "additionalProperties": False
            }
        }
    }
]


def call_tool_function(name, args):
    """
    Dispatch to the correct tool/function based on the `name` provided.
    """
    if name == "save_task_list":
        return save_task_list(**args)
    return {"error": "Function not found."}


def get_task_list(user_id):
    """
    Get the current task list for a given user from the remote API,
    signing the request using AWS SigV4.
    """
    params = {"user_id": user_id}
    try:
        response = requests.get(
            f"{API_BASE_URL}/task_list",
            params=params,
            auth=aws_auth
        )
        logging.info(f"GET /task_list response: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to get task list."}
    except Exception as e:
        logging.error(f"Exception fetching task list: {e}", exc_info=True)
        return {"error": str(e)}


def save_task_list(user_id: str, task_list: str):
    """
    Save a formatted task list for a user in DynamoDB via the API,
    signing the request with AWS SigV4.
    """
    if not isinstance(task_list, str):
        return {"error": "Task list must be a string."}

    payload = {
        "user_id": str(user_id),         # Ensure user_id is a string
        "task_list": task_list.strip()     # Trim whitespace for consistency
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{API_BASE_URL}/task_list",
            json=payload,
            headers=headers,
            auth=aws_auth
        )
        logging.info(f"POST /task_list response: {response.status_code}")
        if response.status_code in [200, 201]:
            return response.json()
        return {
            "error": f"Failed to save task list. Status Code: {response.status_code}, Error: {response.text}"
        }
    except Exception as e:
        logging.error(f"Exception saving task list: {e}", exc_info=True)
        return {"error": str(e)}


def chat_with_gpt(user_id: str, input_text: str):
    """
    Orchestrate interaction with the OpenAI ChatCompletion API.
    1) Fetch user's current task list.
    2) Send ChatGPT a system prompt, the user task list context, and the user's message.
    3) If GPT calls a tool (function), execute it and pass its result back to GPT.
    4) Return the final GPT response to the user.
    """
    # Retrieve current task list
    task_list = get_task_list(user_id)

    # Prepare the conversation so GPT has context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the current task list for the user:\n\n{task_list}\n---\n\n"
        },
        {"role": "user", "content": input_text}
    ]

    try:
        # Initial completion
        completion = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            tools=TOOLS
        )

        # Check if GPT responded directly or is calling a tool
        if completion.choices[0].message.content:
            logging.info("GPT returned a direct response.")
            return {"response": completion.choices[0].message.content}
        else:
            # GPT has a function call
            logging.info("GPT returned a tool (function) call.")
            messages.append(completion.choices[0].message)

            # Process each tool call
            for tool_call in completion.choices[0].message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                args["user_id"] = user_id  # ensure user_id is included

                # Execute the tool function
                result = call_tool_function(name, args)

                # Add the tool's result to the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })

            # Request a final response from GPT after the tool call
            final_completion = openai.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                tools=TOOLS
            )
            return {"response": final_completion.choices[0].message.content}

    except Exception as e:
        logging.error(f"Exception in chat_with_gpt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
