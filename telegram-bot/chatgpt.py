import openai
import logging
import requests
import json
from fastapi import HTTPException


logging.basicConfig(level=logging.INFO)
API_BASE_URL = "https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/Prod/"
system_prompt = "You are a helpful assistant that helps users manage their tasks."
gpt_model = "gpt-4o"
tools = [
    {
        "type": "function",
        "function": {
            "name": "save_task_list",
            "description": "Save the task list with all tasks of the user to DB when there are any changes.",
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


def call_function(name, args):
    if name == "save_task_list":
        return save_task_list(**args)
    else:
        return {"error": "Function not found."}


def get_task_list(user_id):
    params = {"user_id": user_id}

    response = requests.get(f"{API_BASE_URL}/task_list", params=params)
    logging.error(f"Response: {response.json()}")
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Failed to get task list."}


def save_task_list(user_id: str, task_list: str):
    """
    Saves a formatted task list for a user in DynamoDB via the API.
    """
    # Ensure task_list is a valid string
    if not isinstance(task_list, str):
        return {"error": "Task list must be a string."}

    # Prepare the payload
    payload = {
        "user_id": str(user_id),  # Ensure user_id is a string
        "task_list": task_list.strip()  # Trim whitespace for consistency
    }

    # Send the POST request
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{API_BASE_URL}/task_list", json=payload, headers=headers)

    # Log the response for debugging
    #logging.error(f"Response ({response.status_code}): {response.text}")

    # Handle the response
    if response.status_code in [200, 201]:  # Check for both success codes
        return response.json()
    else:
        return {
            "error": f"Failed to save task list. Status Code: {response.status_code}, Error: {response.text}"
        }


def chat_with_gpt(user_id: str, input_text: str):
    """
    Send message to OpenAI API.
    """

    # Get the current task list for the user
    task_list = get_task_list(user_id)

    # Prepare the prompt
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Here is the current task list for the user:\n\n{task_list}---\n\n"},
        {"role": "user", "content": input_text}
    ]

    try:
        # Send first user message to ChatGPT
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages,
            tools=tools
        )

        # Check if the response is a message or a tool call
        logging.error(f"ChatGPT first response: {completion}")
        if completion.choices[0].message.content:
            return {"response": completion.choices[0].message.content}
        else:
            # Handle tool call
            messages.append(completion.choices[0].message)
            for tool_call in completion.choices[0].message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                # Add user_id to the arguments
                args["user_id"] = user_id

                result = call_function(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })

            # ChatGPT final message
            logging.error(f"ChatGPT final response: {messages}")
            completion_2 = openai.chat.completions.create(
                model=gpt_model,
                messages=messages,
                tools=tools,
            )

            return {"response": completion_2.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
