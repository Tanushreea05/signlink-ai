"""
Simple Backend Server for SignLink AI.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import httpx
import asyncio

app = FastAPI(
    title="SignLink AI - Simple Backend",
    version="1.0.0",
    description="Simple backend for SignLink AI"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock user database
users_db = {
    "test@example.com": {
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "fake_hashed_password",
        "is_active": True
    }
}

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class InferenceRequest(BaseModel):
    language: str
    input_type: str
    keypoints: Optional[List[List[float]]] = None
    model_version: str = "latest"

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SignLink AI - Simple Backend",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "ml_server": "connected"
    }

@app.post("/api/v1/auth/register")
async def register(user: UserRegister):
    """Register a new user"""
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_db[user.email] = {
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": f"hashed_{user.password}",
        "is_active": True
    }
    
    return {
        "message": "User registered successfully",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "is_active": True
        }
    }

@app.post("/api/v1/auth/login")
async def login(user: UserLogin):
    """Login user"""
    if user.email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    stored_user = users_db[user.email]
    if stored_user["hashed_password"] != f"hashed_{user.password}":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": f"fake_token_for_{user.email}",
        "token_type": "bearer",
        "user": {
            "email": stored_user["email"],
            "full_name": stored_user["full_name"],
            "is_active": stored_user["is_active"]
        }
    }

@app.post("/api/v1/inference/predict")
async def predict(request: InferenceRequest):
    """Make inference request to ML server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/predict",
                json=request.dict(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML server unavailable: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="ML server error")

@app.get("/api/v1/models")
async def list_models():
    """List available models"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/models",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML server unavailable: {str(e)}")

@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    return {
        "users_count": len(users_db),
        "active_users": len([u for u in users_db.values() if u["is_active"]]),
        "ml_server_status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
