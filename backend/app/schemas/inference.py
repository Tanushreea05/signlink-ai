"""
Pydantic schemas for ML Inference API.

Defines request/response models for inference endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class SignLanguage(str, Enum):
    """Supported sign languages"""
    ASL = "ASL"
    ISL = "ISL"
    BSL = "BSL"


class InputType(str, Enum):
    """Input data types"""
    VIDEO = "video"
    IMAGE = "image"
    KEYPOINTS = "keypoints"
    WEBCAM = "webcam"


class InferenceRequest(BaseModel):
    """Schema for inference request"""
    language: SignLanguage = Field(..., description="Sign language to recognize")
    input_type: InputType = Field(..., description="Type of input data")
    data: Optional[str] = Field(None, description="Base64 encoded data or URL")
    keypoints: Optional[List[List[float]]] = Field(None, description="Pre-extracted keypoints")
    model_version: Optional[str] = Field("latest", description="Model version to use")
    
    @validator("data", "keypoints")
    def validate_input(cls, v, values):
        """Ensure either data or keypoints is provided"""
        if values.get("input_type") == InputType.KEYPOINTS and not values.get("keypoints"):
            raise ValueError("Keypoints required for keypoints input type")
        return v


class InferenceResponse(BaseModel):
    """Schema for inference response"""
    prediction: str = Field(..., description="Predicted sign or phrase")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    language: SignLanguage
    alternatives: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative predictions with confidence scores"
    )
    latency_ms: int = Field(..., description="Inference latency in milliseconds")
    model_version: str = Field(..., description="Model version used")
    inference_id: str = Field(..., description="Unique inference ID")


class BatchInferenceRequest(BaseModel):
    """Schema for batch inference request"""
    requests: List[InferenceRequest] = Field(..., max_items=32)


class BatchInferenceResponse(BaseModel):
    """Schema for batch inference response"""
    results: List[InferenceResponse]
    total_latency_ms: int


class KeypointData(BaseModel):
    """Schema for keypoint data"""
    hand_left: Optional[List[List[float]]] = None
    hand_right: Optional[List[List[float]]] = None
    pose: Optional[List[List[float]]] = None
    face: Optional[List[List[float]]] = None


class StreamFrame(BaseModel):
    """Schema for streaming frame data"""
    frame_id: int
    timestamp: float
    data: str  # Base64 encoded frame
    language: SignLanguage


class StreamResponse(BaseModel):
    """Schema for streaming response"""
    frame_id: int
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    is_processing: bool = True


class ModelInfo(BaseModel):
    """Schema for model information"""
    name: str
    version: str
    language: SignLanguage
    accuracy: float
    size_mb: float
    created_at: str
    is_active: bool


class ModelsListResponse(BaseModel):
    """Schema for models list response"""
    models: List[ModelInfo]
    total: int
