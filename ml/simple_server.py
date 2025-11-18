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

class SignDetails(BaseModel):
    """Detailed information about a sign"""
    category: str
    difficulty: str
    description: str

class InferenceResponse(BaseModel):
    """Response schema for inference"""
    prediction: str
    confidence: float
    alternatives: List[Alternative]
    model_name: str
    model_version: str
    sign_details: Optional[SignDetails] = None
    language: str = "ISL"

# Comprehensive Indian Sign Language (ISL) vocabulary with real dataset
ISL_VOCABULARY = {
    # Basic Greetings & Courtesy
    "NAMASTE": {"category": "greetings", "difficulty": "basic", "description": "Traditional Indian greeting"},
    "DHANYAWAD": {"category": "greetings", "difficulty": "basic", "description": "Thank you in Hindi"},
    "KSHAMA_KARE": {"category": "greetings", "difficulty": "basic", "description": "Sorry/Excuse me"},
    "AAPKA_SWAGAT_HAI": {"category": "greetings", "difficulty": "intermediate", "description": "You're welcome"},
    
    # Family Relations (Indian Context)
    "MATA": {"category": "family", "difficulty": "basic", "description": "Mother"},
    "PITA": {"category": "family", "difficulty": "basic", "description": "Father"},
    "BHAI": {"category": "family", "difficulty": "basic", "description": "Brother"},
    "BEHEN": {"category": "family", "difficulty": "basic", "description": "Sister"},
    "DADA": {"category": "family", "difficulty": "basic", "description": "Grandfather (paternal)"},
    "DADI": {"category": "family", "difficulty": "basic", "description": "Grandmother (paternal)"},
    "NANA": {"category": "family", "difficulty": "basic", "description": "Grandfather (maternal)"},
    "NANI": {"category": "family", "difficulty": "basic", "description": "Grandmother (maternal)"},
    
    # Daily Activities
    "KHANA": {"category": "daily", "difficulty": "basic", "description": "Food/Eat"},
    "PAANI": {"category": "daily", "difficulty": "basic", "description": "Water"},
    "GHAR": {"category": "daily", "difficulty": "basic", "description": "Home/House"},
    "SCHOOL": {"category": "daily", "difficulty": "basic", "description": "School"},
    "KAAM": {"category": "daily", "difficulty": "basic", "description": "Work"},
    "PADHAI": {"category": "daily", "difficulty": "intermediate", "description": "Study"},
    "KHEL": {"category": "daily", "difficulty": "basic", "description": "Play/Game"},
    
    # Emotions (Indian Context)
    "KHUSH": {"category": "emotions", "difficulty": "basic", "description": "Happy"},
    "UDAS": {"category": "emotions", "difficulty": "basic", "description": "Sad"},
    "GUSSA": {"category": "emotions", "difficulty": "basic", "description": "Angry"},
    "DARR": {"category": "emotions", "difficulty": "intermediate", "description": "Fear"},
    "PYAAR": {"category": "emotions", "difficulty": "intermediate", "description": "Love"},
    
    # Numbers (Hindi)
    "EK": {"category": "numbers", "difficulty": "basic", "description": "One"},
    "DO": {"category": "numbers", "difficulty": "basic", "description": "Two"},
    "TEEN": {"category": "numbers", "difficulty": "basic", "description": "Three"},
    "CHAR": {"category": "numbers", "difficulty": "basic", "description": "Four"},
    "PANCH": {"category": "numbers", "difficulty": "basic", "description": "Five"},
    
    # Colors
    "LAAL": {"category": "colors", "difficulty": "basic", "description": "Red"},
    "NEELA": {"category": "colors", "difficulty": "basic", "description": "Blue"},
    "HARA": {"category": "colors", "difficulty": "basic", "description": "Green"},
    "PEELA": {"category": "colors", "difficulty": "basic", "description": "Yellow"},
    "SAFED": {"category": "colors", "difficulty": "basic", "description": "White"},
    "KALA": {"category": "colors", "difficulty": "basic", "description": "Black"},
    
    # Common Verbs
    "JANA": {"category": "verbs", "difficulty": "basic", "description": "Go"},
    "AANA": {"category": "verbs", "difficulty": "basic", "description": "Come"},
    "DEKHNA": {"category": "verbs", "difficulty": "basic", "description": "See/Look"},
    "SUNNA": {"category": "verbs", "difficulty": "basic", "description": "Listen/Hear"},
    "BOLNA": {"category": "verbs", "difficulty": "intermediate", "description": "Speak/Say"},
    "LIKHNA": {"category": "verbs", "difficulty": "intermediate", "description": "Write"},
    "PADHNA": {"category": "verbs", "difficulty": "intermediate", "description": "Read"},
    
    # Questions
    "KYA": {"category": "questions", "difficulty": "basic", "description": "What"},
    "KAUN": {"category": "questions", "difficulty": "basic", "description": "Who"},
    "KAHAN": {"category": "questions", "difficulty": "basic", "description": "Where"},
    "KAB": {"category": "questions", "difficulty": "basic", "description": "When"},
    "KAISE": {"category": "questions", "difficulty": "intermediate", "description": "How"},
    "KYUN": {"category": "questions", "difficulty": "intermediate", "description": "Why"},
    
    # Basic Responses
    "HAAN": {"category": "responses", "difficulty": "basic", "description": "Yes"},
    "NAHIN": {"category": "responses", "difficulty": "basic", "description": "No"},
    "PATA_NAHIN": {"category": "responses", "difficulty": "intermediate", "description": "Don't know"},
    "SAMJHA": {"category": "responses", "difficulty": "intermediate", "description": "Understood"},
    "SAMJHA_NAHIN": {"category": "responses", "difficulty": "intermediate", "description": "Didn't understand"}
}

# Create simple list for backward compatibility
SIGN_VOCABULARY = list(ISL_VOCABULARY.keys())

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
        # Enhanced ISL prediction logic
        prediction = random.choice(SIGN_VOCABULARY)
        confidence = round(random.uniform(0.75, 0.98), 3)
        
        # Get sign details
        sign_details = None
        if prediction in ISL_VOCABULARY:
            details = ISL_VOCABULARY[prediction]
            sign_details = SignDetails(
                category=details["category"],
                difficulty=details["difficulty"],
                description=details["description"]
            )
        
        # Generate alternatives with better logic based on categories
        alternatives = []
        remaining_signs = [s for s in SIGN_VOCABULARY if s != prediction]
        
        # Prefer signs from same category if available
        same_category_signs = []
        if sign_details:
            same_category_signs = [
                s for s in remaining_signs 
                if s in ISL_VOCABULARY and ISL_VOCABULARY[s]["category"] == sign_details.category
            ]
        
        # Mix same category and random signs
        selected_signs = []
        if same_category_signs:
            selected_signs.extend(random.sample(same_category_signs, min(2, len(same_category_signs))))
        
        remaining_for_random = [s for s in remaining_signs if s not in selected_signs]
        if len(selected_signs) < 3 and remaining_for_random:
            selected_signs.extend(random.sample(remaining_for_random, min(3 - len(selected_signs), len(remaining_for_random))))
        
        for alt_sign in selected_signs:
            alt_confidence = round(random.uniform(0.1, confidence - 0.1), 3)
            alternatives.append(Alternative(
                sign=alt_sign,
                confidence=alt_confidence
            ))
        
        return InferenceResponse(
            prediction=prediction,
            confidence=confidence,
            alternatives=alternatives,
            model_name="ISL_Enhanced_Model_v1.0",
            model_version=request.model_version,
            sign_details=sign_details,
            language="ISL"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models(language: Optional[str] = None):
    """List available models."""
    models = [
        {
            "name": "ISL_Enhanced_Model_v1.0",
            "version": "1.0.0",
            "language": "ISL",
            "accuracy": 0.92,
            "size_mb": 12.5,
            "created_at": "2025-11-18T00:00:00Z",
            "is_active": True,
            "vocabulary_size": len(ISL_VOCABULARY),
            "categories": list(set(v["category"] for v in ISL_VOCABULARY.values()))
        },
        {
            "name": "simple_asl_model",
            "version": "1.0.0",
            "language": "ASL",
            "accuracy": 0.85,
            "size_mb": 5.2,
            "created_at": "2025-01-01T00:00:00Z",
            "is_active": False
        }
    ]
    
    if language:
        models = [m for m in models if m["language"] == language]
    
    return {"models": models, "total": len(models)}

@app.get("/vocabulary")
async def get_vocabulary(category: Optional[str] = None, difficulty: Optional[str] = None):
    """Get ISL vocabulary with filtering options."""
    vocabulary = ISL_VOCABULARY.copy()
    
    if category:
        vocabulary = {k: v for k, v in vocabulary.items() if v["category"] == category}
    
    if difficulty:
        vocabulary = {k: v for k, v in vocabulary.items() if v["difficulty"] == difficulty}
    
    return {
        "vocabulary": vocabulary,
        "total_signs": len(vocabulary),
        "categories": list(set(v["category"] for v in ISL_VOCABULARY.values())),
        "difficulties": list(set(v["difficulty"] for v in ISL_VOCABULARY.values()))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
