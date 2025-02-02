# Importing necessary modules
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import boto3
from datetime import datetime, timedelta
from jose import JWTError, jwt
import openai
from envs import env


# Initialize FastAPI application
app = FastAPI()

# AWS DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
task_summary_table = dynamodb.Table("UserTaskSummary")

# JWT Configuration
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OpenAI Configuration
openai.api_key = env("OPENAI_API_KEY")

# Models
class TaskList(BaseModel):
    user_id: Optional[str] = None
    task_list: Optional[str] = None

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Authentication Functions
fake_users_db = {
    "testuser": {"username": "testuser", "password": "testpassword"}
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/token", response_model=Token)
def login(user: User):
    user_dict = fake_users_db.get(user.username)
    if not user_dict or user_dict["password"] != user.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

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
