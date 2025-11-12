"""
SignLink AI Backend - Main Application Entry Point

This module initializes the FastAPI application with all middleware,
routers, and configurations for the SignLink AI platform.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.v1 import auth, users, inference, admin, websocket
from app.core.config import settings
from app.core.database import engine, Base
from app.core.cache import redis_client
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Database connection initialization
    - Redis connection
    - Model loading
    - Cleanup on shutdown
    """
    logger.info("Starting SignLink AI Backend...")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Cleanup
    logger.info("Shutting down SignLink AI Backend...")
    await redis_client.close()
    await engine.dispose()
    logger.info("Application shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Based Multi Sign Language Communication Platform",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Add custom middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

app.add_middleware(LoggingMiddleware)


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["Users"]
)

app.include_router(
    inference.router,
    prefix=f"{settings.API_V1_PREFIX}/inference",
    tags=["ML Inference"]
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin"]
)

if settings.ENABLE_WEBSOCKET:
    app.include_router(
        websocket.router,
        prefix=f"{settings.API_V1_PREFIX}/ws",
        tags=["WebSocket"]
    )


# Mount Prometheus metrics endpoint
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        dict: Health status of the application and dependencies
    """
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
    
    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        await redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["redis"] = "disconnected"
    
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.
    
    Returns:
        dict: Readiness status
    """
    return {"status": "ready"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
        
    Returns:
        JSONResponse: Error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "request_id": request.state.request_id if hasattr(request.state, "request_id") else None,
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )
