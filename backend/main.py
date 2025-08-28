from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base, get_db, engine
import models, auth
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
from chat import ChatService
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from websocket_ import manager
from sqlalchemy.future import select
from models import Conversation
from sqlalchemy.orm import selectinload
from models import UserCreator
from sqlalchemy.future import select
from passlib.context import CryptContext
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
@app.post("/signup/creator")
async def signup_creator(data: models.CreatorSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_creator(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"access_token": token}
@app.post("/signup/business")
async def signup_business(data: models.BusinessSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_business(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"access_token": token}

@app.post("/login")
async def login(data: models.Login, db: AsyncSession = Depends(get_db)):
    token = await auth.login(data, db)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token}

@app.post("/signup/google")
async def signup_google(data: models.GoogleSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_with_google(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Google signup failed")
    return {"access_token": token}

@app.post("/login/google")
async def login_google(data: models.GoogleToken, db: AsyncSession = Depends(get_db)):
    token = await auth.login_with_google(data.token, db)
    if not token:
        raise HTTPException(status_code=401, detail="Google login failed")
    return {"access_token": token}

@app.get("/get_current_user")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        return {"email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

@app.get("/chat/creators", response_model=List[dict])
async def get_creators(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Get list of creators for businesses to start conversations with"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can access creators list")
            
        creators = await ChatService.get_creators_list(db)
        return creators
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/chat/conversations")
async def create_conversation(
    data: models.ConversationCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversation_id = await ChatService.create_conversation(email, role, data, db)
        if not conversation_id:
            raise HTTPException(status_code=400, detail="Failed to create conversation")
            
        return {"conversation_id": conversation_id, "message": "Conversation created successfully"}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/chat/conversations", response_model=List[models.ConversationResponse])
async def get_conversations(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversations = await ChatService.get_conversations(email, role, db)
        return conversations
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/chat/conversations/{conversation_id}", response_model=models.ConversationDetail)
async def get_conversation_detail(
    conversation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed conversation with messages"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversation = await ChatService.get_conversation_detail(conversation_id, email, role, db)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        return conversation
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/chat/messages", response_model=models.MessageResponse)
async def send_message(
    data: models.MessageCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a conversation"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        message = await ChatService.send_message(email, role, data, db)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to send message")
            
        return message
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/chat/conversations/{conversation_id}/read")
async def mark_conversation_as_read(
    conversation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Mark all messages in a conversation as read"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        
        await ChatService.mark_messages_as_read(conversation_id, role, db)
        return {"message": "Messages marked as read"}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    



@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time chat"""
    
    if not await manager.connect(websocket, token):
        return
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(f"pong: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/chat/messages", response_model=models.MessageResponse)
async def send_message_with_notifications(
    data: models.MessageCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a conversation with real-time notifications"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        message = await ChatService.send_message(email, role, data, db)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to send message")
        
        # Get conversation details for WebSocket notification
        conversation_query = select(Conversation).where(
            Conversation.id == data.conversation_id
        ).options(
            selectinload(Conversation.creator),
            selectinload(Conversation.business)
        )
        conv_result = await db.execute(conversation_query)
        conversation = conv_result.scalar()
        
        if conversation:
            # Send real-time notification to both participants
            notification = {
                "type": "new_message",
                "conversation_id": conversation.id,
                "message": {
                    "id": message.id,
                    "sender_type": message.sender_type,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read
                },
                "conversation_info": {
                    "creator_email": conversation.creator.email,
                    "business_name": conversation.business.business_name
                }
            }
            
            await manager.send_to_conversation_participants(
                conversation.creator.email,
                conversation.business.email,
                conversation.business.business_name,
                notification
            )
        
        return message
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")