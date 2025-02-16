# Importing necessary modules
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import boto3
import openai
from envs import env
from mangum import Mangum


# Initialize FastAPI application
app = FastAPI()

# AWS DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
task_summary_table = dynamodb.Table("UserTaskSummary")

# OpenAI Configuration
openai.api_key = env("OPENAI_API_KEY")

# Models
class TaskList(BaseModel):
    user_id: Optional[str] = None
    task_list: Optional[str] = None


@app.post("/task_list", status_code=201)
def save_task_list(task_list: TaskList):
    """
    Saves a user's formatted task list in DynamoDB.
    """
    try:
        task_data = task_list.dict()
        if not task_data.get("user_id") or not task_data.get("task_list"):
            raise HTTPException(status_code=400, detail="Missing required fields: user_id or task_list")

        # Store in DynamoDB
        task_summary_table.put_item(Item=task_data)

        return {"message": "Task saved successfully", "task": task_data}
    except Exception as e:
        logging.error(f"Error saving task list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/task_list")
def get_tasks(user_id: str = Query(..., description="User ID to fetch the task list")):
    """
    Retrieves the stored task list for a user from DynamoDB.
    """
    response = task_summary_table.get_item(Key={"user_id": user_id})
    return response.get("Item", {}).get("task_list", "No tasks found.")


# Handler for AWS Lambda
handler = Mangum(app)
