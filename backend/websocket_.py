from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
from jose import jwt, JWTError
import json
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

class ConnectionManager:
    def __init__(self):
        # Store active connections by user email and role
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store user info for each websocket
        self.connection_info: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, token: str):
        """Connect a user via websocket"""
        try:
            # Verify the token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            role = payload.get("role")
            
            await websocket.accept()
            
            # Store connection
            user_key = f"{email}:{role}"
            if user_key not in self.active_connections:
                self.active_connections[user_key] = []
            self.active_connections[user_key].append(websocket)
            
            # Store connection info
            self.connection_info[websocket] = {
                "email": email,
                "role": role,
                "user_key": user_key
            }
            
            return True
            
        except JWTError:
            await websocket.close(code=1008)  # Policy Violation
            return False
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket"""
        if websocket in self.connection_info:
            user_key = self.connection_info[websocket]["user_key"]
            
            # Remove from active connections
            if user_key in self.active_connections:
                self.active_connections[user_key].remove(websocket)
                if not self.active_connections[user_key]:
                    del self.active_connections[user_key]
            
            # Remove connection info
            del self.connection_info[websocket]
    
    async def send_to_user(self, email: str, role: str, message: dict):
        """Send message to specific user"""
        user_key = f"{email}:{role}"
        if user_key in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_key]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def send_to_conversation_participants(self, creator_email: str, business_email: str, 
                                             business_name: str, message: dict):
        """Send message to both participants in a conversation"""
        await self.send_to_user(creator_email, "creator", message)
        await self.send_to_user(business_email, "business", message)

# Global connection manager instance
manager = ConnectionManager()


