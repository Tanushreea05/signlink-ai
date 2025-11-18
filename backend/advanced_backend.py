"""
SignLink AI - Advanced Enterprise Backend
Production-ready FastAPI backend with microservices architecture, advanced authentication,
real-time features, and enterprise scalability.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import jwt
import bcrypt
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr, validator
import httpx
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import structlog

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Metrics
REQUEST_COUNTER = Counter('signlink_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('signlink_request_duration_seconds', 'Request latency')
ACTIVE_USERS = Gauge('signlink_active_users', 'Active users')
WEBSOCKET_CONNECTIONS = Gauge('signlink_websocket_connections', 'Active WebSocket connections')

# Configuration
JWT_SECRET = "your-super-secret-jwt-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    preferred_language: str = Field(default="indian_english")
    phone: Optional[str] = None
    organization: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    preferred_language: str
    phone: Optional[str]
    organization: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    subscription_tier: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile

class AdvancedInferenceRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: str = Field(default="ISL")
    input_type: str = Field(default="keypoints")
    keypoints: Optional[List[List[float]]] = None
    video_frames: Optional[List[str]] = None
    model_version: str = Field(default="latest")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_alternatives: int = Field(default=5, ge=1, le=10)
    output_language: str = Field(default="indian_english")
    context: Optional[Dict[str, Any]] = None

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

# In-memory databases (replace with real databases in production)
users_db: Dict[str, Dict] = {}
sessions_db: Dict[str, Dict] = {}
websocket_connections: Dict[str, WebSocket] = {}

class AuthService:
    """Advanced authentication service"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

class MLService:
    """ML service integration"""
    
    def __init__(self):
        self.ml_server_url = "http://localhost:8001"
        self.client = None
    
    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def predict(self, request: AdvancedInferenceRequest, user_id: str) -> Dict:
        """Make prediction request to ML server"""
        try:
            # Add user context
            request_data = request.dict()
            request_data["user_id"] = user_id
            
            response = await self.client.post(
                f"{self.ml_server_url}/predict",
                json=request_data
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"ML server request failed: {e}")
            raise HTTPException(status_code=503, detail="ML service unavailable")
        except httpx.HTTPStatusError as e:
            logger.error(f"ML server error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="ML service error")
    
    async def get_vocabulary(self, **params) -> Dict:
        """Get vocabulary from ML server"""
        try:
            response = await self.client.get(
                f"{self.ml_server_url}/vocabulary",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Vocabulary request failed: {e}")
            raise HTTPException(status_code=503, detail="Vocabulary service unavailable")

class WebSocketManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect user WebSocket"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        self.user_sessions[user_id] = connection_id
        WEBSOCKET_CONNECTIONS.set(len(self.connections))
        logger.info(f"WebSocket connected: {user_id}")
        return connection_id
    
    def disconnect(self, connection_id: str, user_id: str):
        """Disconnect WebSocket"""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        WEBSOCKET_CONNECTIONS.set(len(self.connections))
        logger.info(f"WebSocket disconnected: {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.user_sessions:
            connection_id = self.user_sessions[user_id]
            if connection_id in self.connections:
                websocket = self.connections[connection_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to {user_id}: {e}")
                    self.disconnect(connection_id, user_id)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected users"""
        disconnected = []
        for connection_id, websocket in self.connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            if connection_id in self.connections:
                del self.connections[connection_id]

# Global services
auth_service = AuthService()
ml_service = MLService()
websocket_manager = WebSocketManager()
redis_client = None

# Security dependency
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    payload = auth_service.verify_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if not user_id or user_id not in users_db:
        raise HTTPException(status_code=401, detail="User not found")
    
    user = users_db[user_id]
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting SignLink AI Advanced Backend...")
    
    # Initialize services
    await ml_service.initialize()
    
    # Initialize Redis
    global redis_client
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None
    
    logger.info("Backend startup complete")
    yield
    
    # Cleanup
    logger.info("Shutting down backend...")
    if ml_service.client:
        await ml_service.client.aclose()
    if redis_client:
        await redis_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="SignLink AI - Advanced Backend",
    version="2.0.0",
    description="Enterprise-grade backend for Indian Sign Language platform",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add processing time and request metrics"""
    start_time = time.time()
    
    # Update request counter
    REQUEST_COUNTER.labels(method=request.method, endpoint=request.url.path).inc()
    
    response = await call_next(request)
    
    # Update latency histogram
    process_time = time.time() - start_time
    REQUEST_LATENCY.observe(process_time)
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

@app.get("/")
async def root():
    """Root endpoint with comprehensive API info"""
    return {
        "name": "SignLink AI - Advanced Backend",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Advanced JWT authentication",
            "Real-time WebSocket support",
            "Multilingual ISL processing",
            "Enterprise monitoring",
            "Scalable microservices architecture",
            "Production-ready security"
        ],
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "inference": "/api/v1/inference/*",
            "websocket": "/ws",
            "health": "/health",
            "metrics": "/metrics"
        },
        "supported_languages": ["ISL", "ASL", "BSL"],
        "output_languages": ["english", "indian_english", "tamil"]
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "ml_server": "unknown",
            "redis": "available" if redis_client else "unavailable",
            "websocket": "active"
        },
        "metrics": {
            "active_users": len(users_db),
            "websocket_connections": len(websocket_manager.connections),
            "total_requests": REQUEST_COUNTER._value._value
        }
    }
    
    # Check ML server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8001/health")
            health_status["services"]["ml_server"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        health_status["services"]["ml_server"] = "unavailable"
    
    return health_status

# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegistration, background_tasks: BackgroundTasks):
    """Register new user with advanced validation"""
    # Check if user exists
    if any(u["email"] == user_data.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = auth_service.hash_password(user_data.password)
    
    user = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "preferred_language": user_data.preferred_language,
        "phone": user_data.phone,
        "organization": user_data.organization,
        "hashed_password": hashed_password,
        "created_at": datetime.now(),
        "last_login": None,
        "is_active": True,
        "subscription_tier": "free",
        "usage_stats": {
            "total_predictions": 0,
            "total_sessions": 0
        }
    }
    
    users_db[user_id] = user
    ACTIVE_USERS.set(len(users_db))
    
    # Create tokens
    access_token = auth_service.create_access_token({"sub": user_id})
    refresh_token = auth_service.create_refresh_token({"sub": user_id})
    
    # Background task for welcome email (mock)
    background_tasks.add_task(send_welcome_email, user_data.email, user_data.full_name)
    
    user_profile = UserProfile(**{k: v for k, v in user.items() if k != "hashed_password"})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_profile
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user with advanced security"""
    # Find user
    user = None
    for u in users_db.values():
        if u["email"] == login_data.email:
            user = u
            break
    
    if not user or not auth_service.verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    # Update last login
    user["last_login"] = datetime.now()
    
    # Create tokens
    access_token = auth_service.create_access_token({"sub": user["id"]})
    refresh_token = auth_service.create_refresh_token({"sub": user["id"]})
    
    user_profile = UserProfile(**{k: v for k, v in user.items() if k != "hashed_password"})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_profile
    )

@app.get("/api/v1/auth/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile"""
    return UserProfile(**{k: v for k, v in current_user.items() if k != "hashed_password"})

# Inference endpoints
@app.post("/api/v1/inference/predict")
async def predict(
    request: AdvancedInferenceRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Advanced prediction with user context"""
    try:
        # Add user context to request
        request.output_language = current_user.get("preferred_language", "indian_english")
        
        # Make prediction
        result = await ml_service.predict(request, current_user["id"])
        
        # Update user stats
        current_user["usage_stats"]["total_predictions"] += 1
        
        # Send real-time update via WebSocket
        background_tasks.add_task(
            websocket_manager.send_to_user,
            current_user["id"],
            {
                "type": "prediction_complete",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction failed for user {current_user['id']}: {e}")
        raise

@app.get("/api/v1/inference/vocabulary")
async def get_vocabulary(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get vocabulary with user preferences"""
    params = {
        "category": category,
        "difficulty": difficulty,
        "output_language": current_user.get("preferred_language", "indian_english")
    }
    
    return await ml_service.get_vocabulary(**{k: v for k, v in params.items() if v})

@app.get("/api/v1/inference/models")
async def get_models():
    """Get available models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8001/models")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Models request failed: {e}")
        raise HTTPException(status_code=503, detail="Models service unavailable")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time communication"""
    try:
        # Verify token
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id or user_id not in users_db:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Connect user
        connection_id = await websocket_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                message = WebSocketMessage(**data)
                
                # Handle different message types
                if message.type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif message.type == "prediction_request":
                    # Handle real-time prediction request
                    request = AdvancedInferenceRequest(**message.data)
                    result = await ml_service.predict(request, user_id)
                    await websocket.send_json({
                        "type": "prediction_result",
                        "data": result,
                        "timestamp": datetime.now().isoformat()
                    })
                
        except WebSocketDisconnect:
            websocket_manager.disconnect(connection_id, user_id)
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
            websocket_manager.disconnect(connection_id, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")

# Analytics endpoints
@app.get("/api/v1/analytics/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """Get user dashboard analytics"""
    user_stats = current_user.get("usage_stats", {})
    
    return {
        "user_stats": user_stats,
        "recent_activity": [],  # Implement based on requirements
        "achievements": [],     # Implement gamification
        "learning_progress": {
            "signs_learned": user_stats.get("total_predictions", 0) // 10,
            "accuracy_trend": [],
            "favorite_categories": []
        }
    }

# Background tasks
async def send_welcome_email(email: str, name: str):
    """Send welcome email (mock implementation)"""
    logger.info(f"Sending welcome email to {email} ({name})")
    # Implement actual email sending logic

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "advanced_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
        log_level="info"
    )
