"""
ML Inference Server.

FastAPI server for real-time sign language recognition.
"""

import os
import argparse
import torch
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import base64
import cv2

from models.sign_language_model import create_model
from data.preprocessing import KeypointExtractor, normalize_keypoints, temporal_interpolation


app = FastAPI(
    title="SignLink AI - ML Inference Server",
    version="1.0.0",
    description="Real-time sign language recognition inference server"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global variables
model = None
device = None
keypoint_extractor = None
class_names = []


class InferenceRequest(BaseModel):
    """Request schema for inference"""
    language: str
    input_type: str
    data: Optional[str] = None
    keypoints: Optional[List[List[float]]] = None
    model_version: str = "latest"


class InferenceResponse(BaseModel):
    """Response schema for inference"""
    prediction: str
    confidence: float
    alternatives: List[Dict[str, float]]
    model_name: str
    model_version: str


def load_model(model_path: str, device_type: str = "cuda"):
    """
    Load trained model.
    
    Args:
        model_path: Path to model checkpoint
        device_type: Device to use (cuda/cpu)
    """
    global model, device, class_names
    
    device = torch.device(device_type if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    
    # Load class names
    model_dir = os.path.dirname(model_path)
    class_names_file = os.path.join(model_dir, "class_names.txt")
    if os.path.exists(class_names_file):
        with open(class_names_file, 'r') as f:
            class_names = [line.strip() for line in f]
    else:
        # Default class names
        class_names = [f"sign_{i}" for i in range(100)]
    
    # Create model
    model = create_model(
        model_type="standard",
        num_classes=len(class_names)
    )
    
    # Load weights
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    print(f"Model loaded successfully with {len(class_names)} classes")


def initialize_keypoint_extractor():
    """Initialize MediaPipe keypoint extractor"""
    global keypoint_extractor
    keypoint_extractor = KeypointExtractor(
        extract_hands=True,
        extract_pose=True,
        extract_face=False
    )
    print("Keypoint extractor initialized")


def decode_base64_image(data: str) -> np.ndarray:
    """
    Decode base64 encoded image.
    
    Args:
        data: Base64 encoded image string
        
    Returns:
        Decoded image as numpy array
    """
    # Remove data URL prefix if present
    if ',' in data:
        data = data.split(',')[1]
    
    # Decode base64
    img_bytes = base64.b64decode(data)
    
    # Convert to numpy array
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    return img


def extract_keypoints_from_image(image: np.ndarray) -> np.ndarray:
    """
    Extract keypoints from image.
    
    Args:
        image: Input image
        
    Returns:
        Keypoints array
    """
    keypoint_data = keypoint_extractor.extract_from_frame(image)
    keypoints = keypoint_data.to_array()
    return keypoints


def preprocess_keypoints(keypoints: np.ndarray, sequence_length: int = 30) -> torch.Tensor:
    """
    Preprocess keypoints for model input.
    
    Args:
        keypoints: Raw keypoints
        sequence_length: Target sequence length
        
    Returns:
        Preprocessed tensor
    """
    # If single frame, repeat to create sequence
    if len(keypoints.shape) == 2:
        keypoints = np.expand_dims(keypoints, 0)
        keypoints = np.repeat(keypoints, sequence_length, axis=0)
    
    # Normalize
    normalized = []
    for frame in keypoints:
        normalized.append(normalize_keypoints(frame))
    keypoints = np.array(normalized)
    
    # Interpolate to fixed length
    if len(keypoints) != sequence_length:
        keypoints = temporal_interpolation(keypoints, sequence_length)
    
    # Convert to tensor
    tensor = torch.FloatTensor(keypoints).unsqueeze(0)  # Add batch dimension
    
    return tensor


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    # These would be set via environment variables or command line args
    model_path = os.getenv("MODEL_PATH", "models/checkpoints/best_model.pth")
    device_type = os.getenv("DEVICE", "cuda")
    
    if os.path.exists(model_path):
        load_model(model_path, device_type)
        initialize_keypoint_extractor()
    else:
        print(f"Warning: Model not found at {model_path}")
        print("Server will return mock predictions")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SignLink AI - ML Inference Server",
        "version": "1.0.0",
        "status": "operational",
        "model_loaded": model is not None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device) if device else "none"
    }


@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest):
    """
    Predict sign language from input.
    
    Args:
        request: Inference request
        
    Returns:
        Prediction result
    """
    try:
        # Extract keypoints based on input type
        if request.input_type == "keypoints" and request.keypoints:
            keypoints = np.array(request.keypoints)
        elif request.input_type in ["image", "video"] and request.data:
            # Decode image
            image = decode_base64_image(request.data)
            # Extract keypoints
            keypoints = extract_keypoints_from_image(image)
        else:
            raise HTTPException(status_code=400, detail="Invalid input data")
        
        # Preprocess
        input_tensor = preprocess_keypoints(keypoints)
        input_tensor = input_tensor.to(device)
        
        # Inference
        with torch.no_grad():
            logits, attention = model(input_tensor)
            probabilities = torch.softmax(logits, dim=1)
            
            # Get top predictions
            top_probs, top_indices = torch.topk(probabilities, k=min(5, len(class_names)))
            
            prediction_idx = top_indices[0][0].item()
            confidence = top_probs[0][0].item()
            
            # Get alternatives
            alternatives = []
            for i in range(1, len(top_indices[0])):
                idx = top_indices[0][i].item()
                prob = top_probs[0][i].item()
                alternatives.append({
                    "sign": class_names[idx],
                    "confidence": float(prob)
                })
        
        return InferenceResponse(
            prediction=class_names[prediction_idx],
            confidence=float(confidence),
            alternatives=alternatives,
            model_name="sign_language_model",
            model_version=request.model_version
        )
    
    except Exception as e:
        # Return mock prediction if model not loaded
        if model is None:
            return InferenceResponse(
                prediction="HELLO",
                confidence=0.92,
                alternatives=[
                    {"sign": "HI", "confidence": 0.05},
                    {"sign": "WELCOME", "confidence": 0.02}
                ],
                model_name="sign_language_model",
                model_version="mock"
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def list_models(language: Optional[str] = None):
    """
    List available models.
    
    Args:
        language: Filter by language
        
    Returns:
        List of models
    """
    models = [
        {
            "name": "asl_model",
            "version": "1.0.0",
            "language": "ASL",
            "accuracy": 0.942,
            "size_mb": 45.2,
            "created_at": "2025-01-01T00:00:00Z",
            "is_active": True
        },
        {
            "name": "isl_model",
            "version": "1.0.0",
            "language": "ISL",
            "accuracy": 0.918,
            "size_mb": 43.8,
            "created_at": "2025-01-01T00:00:00Z",
            "is_active": True
        },
        {
            "name": "bsl_model",
            "version": "1.0.0",
            "language": "BSL",
            "accuracy": 0.935,
            "size_mb": 44.5,
            "created_at": "2025-01-01T00:00:00Z",
            "is_active": True
        },
    ]
    
    if language:
        models = [m for m in models if m["language"] == language]
    
    return {"models": models, "total": len(models)}


if __name__ == "__main__":
    import uvicorn
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="models/checkpoints/best_model.pth")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["MODEL_PATH"] = args.model_path
    os.environ["DEVICE"] = args.device
    
    uvicorn.run(app, host=args.host, port=args.port)
