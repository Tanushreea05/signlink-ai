"""
Simple FastAPI server for Signverse AI
Provides basic API endpoints without database dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import time

app = FastAPI(
    title="Signverse AI API",
    description="AI-powered sign language recognition platform",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SignPrediction(BaseModel):
    sign: str
    confidence: float

class InferenceRequest(BaseModel):
    input_type: str
    keypoints: Optional[List[List[float]]] = None
    model_version: str = "latest"

class InferenceResponse(BaseModel):
    prediction: str
    confidence: float
    model_name: str
    processing_time_ms: float
    alternatives: List[SignPrediction]

class UserRegistration(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str

# Mock data
MOCK_SIGNS = [
    "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
    "SORRY", "HELP", "LOVE", "FRIEND", "GOOD", "BAD",
    "HAPPY", "SAD", "WATER", "FOOD", "HOME", "WORK"
]

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Signverse AI API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "inference": "/api/v1/inference/predict",
            "auth": "/api/v1/auth/"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "signverse-ai-api"
    }

@app.post("/api/v1/inference/predict", response_model=InferenceResponse)
async def predict_sign(request: InferenceRequest):
    """Predict sign language from input data"""
    start_time = time.time()
    
    # Mock prediction logic
    primary_prediction = random.choice(MOCK_SIGNS)
    primary_confidence = random.uniform(0.7, 0.95)
    
    # Generate alternatives
    alternatives = []
    remaining_signs = [s for s in MOCK_SIGNS if s != primary_prediction]
    for _ in range(3):
        alt_sign = random.choice(remaining_signs)
        alt_confidence = random.uniform(0.3, 0.6)
        alternatives.append(SignPrediction(sign=alt_sign, confidence=alt_confidence))
        remaining_signs.remove(alt_sign)
    
    processing_time = (time.time() - start_time) * 1000
    
    return InferenceResponse(
        prediction=primary_prediction,
        confidence=primary_confidence,
        model_name="signverse-v1.0-mock",
        processing_time_ms=processing_time,
        alternatives=alternatives
    )

@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register_user(user: UserRegistration):
    """Register a new user (mock implementation)"""
    # Mock registration
    user_id = f"user_{random.randint(1000, 9999)}"
    token = f"mock_token_{random.randint(100000, 999999)}"
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin):
    """Login user (mock implementation)"""
    # Mock login
    user_id = f"user_{random.randint(1000, 9999)}"
    token = f"mock_token_{random.randint(100000, 999999)}"
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id
    )

@app.get("/api/v1/inference/models")
async def list_models():
    """List available ML models"""
    return {
        "models": [
            {
                "name": "signverse-v1.0",
                "version": "1.0.0",
                "languages": ["ASL", "BSL", "ISL"],
                "accuracy": 0.92,
                "status": "active"
            },
            {
                "name": "signverse-lite",
                "version": "0.9.0",
                "languages": ["ASL"],
                "accuracy": 0.87,
                "status": "active"
            }
        ]
    }

@app.get("/api/v1/inference/stats")
async def get_stats():
    """Get inference statistics"""
    return {
        "total_predictions": random.randint(10000, 50000),
        "accuracy": random.uniform(0.85, 0.95),
        "avg_processing_time_ms": random.uniform(50, 150),
        "supported_signs": len(MOCK_SIGNS),
        "active_users": random.randint(100, 1000)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
