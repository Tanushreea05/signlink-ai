"""
WebSocket API for real-time sign language recognition.

Handles streaming video frames and real-time inference.
"""

import json
import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.websockets import WebSocketState

from app.core.security import decode_token
from app.core.config import settings

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time inference.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, message: dict, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(client_id)
            except Exception:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)


manager = ConnectionManager()


async def get_user_from_token(token: str) -> str:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User ID
        
    Raises:
        Exception: If token is invalid
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except Exception as e:
        raise Exception(f"Invalid token: {str(e)}")


@router.websocket("/stream")
async def websocket_stream(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time sign language recognition.
    
    Protocol:
    - Client sends: {"type": "frame", "data": "base64_encoded_frame", "language": "ASL"}
    - Server responds: {"type": "prediction", "prediction": "HELLO", "confidence": 0.95}
    
    Args:
        websocket: WebSocket connection
        token: JWT authentication token
    """
    client_id = None
    
    try:
        # Authenticate user
        user_id = await get_user_from_token(token)
        client_id = f"{user_id}_{id(websocket)}"
        
        # Accept connection
        await manager.connect(websocket, client_id)
        
        # Send connection confirmation
        await manager.send_message({
            "type": "connected",
            "message": "WebSocket connection established",
            "client_id": client_id
        }, client_id)
        
        # Frame buffer for temporal modeling
        frame_buffer = []
        frame_count = 0
        
        while True:
            # Receive frame data
            data = await websocket.receive_json()
            
            if data.get("type") == "frame":
                frame_count += 1
                
                # Add frame to buffer
                frame_buffer.append({
                    "frame_id": frame_count,
                    "data": data.get("data"),
                    "timestamp": data.get("timestamp"),
                })
                
                # Keep only last N frames for temporal context
                if len(frame_buffer) > 30:
                    frame_buffer.pop(0)
                
                # Send acknowledgment
                await manager.send_message({
                    "type": "ack",
                    "frame_id": frame_count,
                }, client_id)
                
                # Process every Nth frame to reduce load
                if frame_count % 5 == 0:
                    # TODO: Call ML inference service with frame_buffer
                    # For now, send mock prediction
                    await manager.send_message({
                        "type": "prediction",
                        "frame_id": frame_count,
                        "prediction": "HELLO",
                        "confidence": 0.92,
                        "language": data.get("language", "ASL"),
                        "is_processing": False,
                    }, client_id)
            
            elif data.get("type") == "ping":
                # Respond to ping
                await manager.send_message({
                    "type": "pong",
                    "timestamp": data.get("timestamp"),
                }, client_id)
            
            elif data.get("type") == "stop":
                # Client requested to stop streaming
                await manager.send_message({
                    "type": "stopped",
                    "message": "Streaming stopped",
                }, client_id)
                break
    
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        if client_id:
            try:
                await manager.send_message({
                    "type": "error",
                    "message": str(e),
                }, client_id)
            except Exception:
                pass
            manager.disconnect(client_id)


@router.websocket("/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time chat with sign language translation.
    
    Args:
        websocket: WebSocket connection
        token: JWT authentication token
    """
    client_id = None
    
    try:
        # Authenticate user
        user_id = await get_user_from_token(token)
        client_id = f"chat_{user_id}_{id(websocket)}"
        
        # Accept connection
        await manager.connect(websocket, client_id)
        
        await manager.send_message({
            "type": "connected",
            "message": "Chat connection established",
        }, client_id)
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Echo message back (in production, this would translate and broadcast)
                await manager.send_message({
                    "type": "message",
                    "user_id": user_id,
                    "message": data.get("message"),
                    "timestamp": data.get("timestamp"),
                }, client_id)
            
            elif data.get("type") == "disconnect":
                break
    
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
    
    except Exception as e:
        print(f"Chat WebSocket error: {e}")
        if client_id:
            manager.disconnect(client_id)
