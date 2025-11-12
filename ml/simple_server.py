"""
Simple ML Inference Server without heavy dependencies.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import random

app = FastAPI(
    title="SignLink AI - Simple ML Server",
    version="1.0.0",
    description="Simple sign language recognition server"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InferenceRequest(BaseModel):
    """Request schema for inference"""
    language: str
    input_type: str
    data: Optional[str] = None
    keypoints: Optional[List[List[float]]] = None
    model_version: str = "latest"

class Alternative(BaseModel):
    """Alternative prediction"""
    sign: str
    confidence: float

class InferenceResponse(BaseModel):
    """Response schema for inference"""
    prediction: str
    confidence: float
    alternatives: List[Alternative]
    model_name: str
    model_version: str

# Mock sign language vocabulary
SIGN_VOCABULARY = [
    "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
    "GOOD", "BAD", "WATER", "FOOD", "HOME", "WORK", "FAMILY",
    "FRIEND", "LOVE", "HELP", "SORRY", "WELCOME", "NICE",
    "BEAUTIFUL", "HAPPY", "SAD", "ANGRY", "EXCITED"
]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SignLink AI - Simple ML Server",
        "version": "1.0.0",
        "status": "operational",
        "model_loaded": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": True,
        "device": "cpu"
    }

@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest):
    """
    Predict sign language from input (mock implementation).
    """
    try:
        # Mock prediction logic
        prediction = random.choice(SIGN_VOCABULARY)
        confidence = round(random.uniform(0.75, 0.98), 3)
        
        # Generate alternatives
        alternatives = []
        remaining_signs = [s for s in SIGN_VOCABULARY if s != prediction]
        for _ in range(min(3, len(remaining_signs))):
            alt_sign = random.choice(remaining_signs)
            remaining_signs.remove(alt_sign)
            alt_confidence = round(random.uniform(0.1, confidence - 0.1), 3)
            alternatives.append({
                "sign": alt_sign,
                "confidence": alt_confidence
            })
        
        return InferenceResponse(
            prediction=prediction,
            confidence=confidence,
            alternatives=alternatives,
            model_name="simple_mock_model",
            model_version=request.model_version
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models(language: Optional[str] = None):
    """List available models."""
    models = [
        {
            "name": "simple_asl_model",
            "version": "1.0.0",
            "language": "ASL",
            "accuracy": 0.85,
            "size_mb": 5.2,
            "created_at": "2025-01-01T00:00:00Z",
            "is_active": True
        }
    ]
    
    if language:
        models = [m for m in models if m["language"] == language]
    
    return {"models": models, "total": len(models)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
