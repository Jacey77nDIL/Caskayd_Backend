import os
from fastapi import FastAPI
from dotenv import load_dotenv
import motor.motor_asyncio
from urllib.parse import quote_plus
from app.models import CreatorSignUp, BusinessSignUp
from typing import Union
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
MONGO_USERNAME = quote_plus(os.getenv("MONGO_USERNAME"))
MONGO_PASSWORD = quote_plus(os.getenv("MONGO_PASSWORD"))
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@waitlist.gdshkuo.mongodb.net/?retryWrites=true&w=majority&appName=waitlist"

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register")
async def register_user(user: Union[CreatorSignUp, BusinessSignUp]):
    if user.is_creator:
        user_data = user.dict()
        result = await db["creators"].insert_one(user_data)
        return {"message": "CreatorSignUp registered", "id": str(result.inserted_id)}
    else:
        user_data = user.dict()
        result = await db["businesses"].insert_one(user_data)
        return {"message": "BusinessSignUp registered", "id": str(result.inserted_id)}


@app.get("/")
async def root():
    return {"message": "Welcome to the Caskayd waitlist API"}
