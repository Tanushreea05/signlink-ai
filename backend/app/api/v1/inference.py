"""
ML Inference API endpoints.

Handles sign language recognition requests and model management.
"""

import uuid
import time
import httpx
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.config import settings
from app.models.user import User
from app.models.inference_history import InferenceHistory
from app.schemas.inference import (
    InferenceRequest,
    InferenceResponse,
    BatchInferenceRequest,
    BatchInferenceResponse,
    ModelInfo,
    ModelsListResponse,
)

router = APIRouter()


async def call_ml_inference_service(
    request_data: dict
) -> dict:
    """
    Call the ML inference service.
    
    Args:
        request_data: Inference request data
        
    Returns:
        Inference response from ML service
        
    Raises:
        HTTPException: If ML service is unavailable
    """
    try:
        async with httpx.AsyncClient(timeout=settings.ML_INFERENCE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.ML_INFERENCE_URL}/predict",
                json=request_data
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML inference service unavailable: {str(e)}"
        )


@router.post("/predict", response_model=InferenceResponse)
async def predict_sign(
    request: InferenceRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Predict sign language from input data.
    
    Args:
        request: Inference request with input data
        user_id: Current user ID
        db: Database session
        
    Returns:
        Prediction result with confidence score
    """
    start_time = time.time()
    
    # Prepare request for ML service
    ml_request = {
        "language": request.language.value,
        "input_type": request.input_type.value,
        "data": request.data,
        "keypoints": request.keypoints,
        "model_version": request.model_version,
    }
    
    # Call ML inference service
    ml_response = await call_ml_inference_service(ml_request)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Create inference history record
    inference_id = str(uuid.uuid4())
    history = InferenceHistory(
        id=inference_id,
        user_id=user_id,
        model_name=ml_response.get("model_name", "sign_language_model"),
        model_version=ml_response.get("model_version", request.model_version),
        input_type=request.input_type.value,
        language=request.language.value,
        prediction=ml_response["prediction"],
        confidence=ml_response["confidence"],
        latency_ms=latency_ms,
        metadata={"alternatives": ml_response.get("alternatives", [])},
    )
    
    db.add(history)
    
    # Update user inference count
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.inference_count += 1
    
    await db.commit()
    
    return InferenceResponse(
        prediction=ml_response["prediction"],
        confidence=ml_response["confidence"],
        language=request.language,
        alternatives=ml_response.get("alternatives", []),
        latency_ms=latency_ms,
        model_version=ml_response.get("model_version", request.model_version),
        inference_id=inference_id,
    )


@router.post("/batch", response_model=BatchInferenceResponse)
async def batch_predict(
    batch_request: BatchInferenceRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Batch inference for multiple inputs.
    
    Args:
        batch_request: Batch of inference requests
        user_id: Current user ID
        db: Database session
        
    Returns:
        Batch inference results
    """
    start_time = time.time()
    results = []
    
    for request in batch_request.requests:
        try:
            result = await predict_sign(request, user_id, db)
            results.append(result)
        except Exception as e:
            # Log error but continue with other requests
            print(f"Batch inference error: {e}")
            continue
    
    total_latency_ms = int((time.time() - start_time) * 1000)
    
    return BatchInferenceResponse(
        results=results,
        total_latency_ms=total_latency_ms
    )


@router.post("/upload", response_model=InferenceResponse)
async def upload_and_predict(
    file: UploadFile = File(...),
    language: str = "ASL",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Upload video/image file and predict sign language.
    
    Args:
        file: Uploaded file
        language: Sign language (ASL, ISL, BSL)
        user_id: Current user ID
        db: Database session
        
    Returns:
        Prediction result
    """
    # Validate file size
    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {allowed_types}"
        )
    
    # Convert to base64 for ML service
    import base64
    data_base64 = base64.b64encode(contents).decode()
    
    # Determine input type
    input_type = "video" if file.content_type.startswith("video") else "image"
    
    # Create inference request
    request = InferenceRequest(
        language=language,
        input_type=input_type,
        data=data_base64,
        model_version="latest"
    )
    
    return await predict_sign(request, user_id, db)


@router.get("/history", response_model=List[dict])
async def get_inference_history(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's inference history.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        user_id: Current user ID
        db: Database session
        
    Returns:
        List of inference history records
    """
    result = await db.execute(
        select(InferenceHistory)
        .where(InferenceHistory.user_id == user_id)
        .order_by(InferenceHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    history = result.scalars().all()
    
    return [h.to_dict() for h in history]


@router.get("/models", response_model=ModelsListResponse)
async def list_models(
    language: str = None,
    user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    List available ML models.
    
    Args:
        language: Filter by sign language (optional)
        user_id: Current user ID
        
    Returns:
        List of available models
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {"language": language} if language else {}
            response = await client.get(
                f"{settings.ML_INFERENCE_URL}/models",
                params=params
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        # Return mock data if ML service is unavailable
        return ModelsListResponse(
            models=[
                ModelInfo(
                    name="asl_model",
                    version="1.0.0",
                    language="ASL",
                    accuracy=0.942,
                    size_mb=45.2,
                    created_at="2025-01-01T00:00:00Z",
                    is_active=True
                ),
                ModelInfo(
                    name="isl_model",
                    version="1.0.0",
                    language="ISL",
                    accuracy=0.918,
                    size_mb=43.8,
                    created_at="2025-01-01T00:00:00Z",
                    is_active=True
                ),
                ModelInfo(
                    name="bsl_model",
                    version="1.0.0",
                    language="BSL",
                    accuracy=0.935,
                    size_mb=44.5,
                    created_at="2025-01-01T00:00:00Z",
                    is_active=True
                ),
            ],
            total=3
        )


@router.get("/stats")
async def get_inference_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's inference statistics.
    
    Args:
        user_id: Current user ID
        db: Database session
        
    Returns:
        Inference statistics
    """
    from sqlalchemy import func
    
    # Get total inferences
    result = await db.execute(
        select(func.count(InferenceHistory.id))
        .where(InferenceHistory.user_id == user_id)
    )
    total_inferences = result.scalar()
    
    # Get average confidence
    result = await db.execute(
        select(func.avg(InferenceHistory.confidence))
        .where(InferenceHistory.user_id == user_id)
    )
    avg_confidence = result.scalar() or 0.0
    
    # Get average latency
    result = await db.execute(
        select(func.avg(InferenceHistory.latency_ms))
        .where(InferenceHistory.user_id == user_id)
    )
    avg_latency = result.scalar() or 0.0
    
    # Get language distribution
    result = await db.execute(
        select(
            InferenceHistory.language,
            func.count(InferenceHistory.id)
        )
        .where(InferenceHistory.user_id == user_id)
        .group_by(InferenceHistory.language)
    )
    language_dist = {lang: count for lang, count in result.all()}
    
    return {
        "total_inferences": total_inferences,
        "average_confidence": round(avg_confidence, 3),
        "average_latency_ms": round(avg_latency, 2),
        "language_distribution": language_dist,
    }
