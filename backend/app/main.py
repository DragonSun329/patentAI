"""PatentAI - Patent Infringement Detection System.

A full-stack application for detecting potential patent infringements
using hybrid search (vector + fuzzy) and LLM-powered analysis.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response

from app.core.config import settings
from app.core.database import init_db
from app.api.patents import router as patents_router
from app.api.claims import router as claims_router
from app.api.ingest import router as ingest_router
from app.api.priorart import router as priorart_router
from app.services.cache import cache_service


# Prometheus custom metrics
REQUEST_COUNT = Counter(
    "patentai_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
SEARCH_LATENCY = Histogram(
    "patentai_search_latency_seconds",
    "Search request latency",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
EMBEDDING_LATENCY = Histogram(
    "patentai_embedding_latency_seconds",
    "Embedding generation latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)
LLM_LATENCY = Histogram(
    "patentai_llm_latency_seconds",
    "LLM analysis latency",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)
PATENTS_INDEXED = Counter(
    "patentai_patents_indexed_total",
    "Total patents indexed"
)
SEARCHES_PERFORMED = Counter(
    "patentai_searches_total",
    "Total searches performed",
    ["search_type"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Connect to Redis
    try:
        await cache_service.connect()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
    
    yield
    
    # Shutdown
    await cache_service.disconnect()
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
# PatentAI - Intelligent Patent Infringement Detection

## Features
- 🔍 **Hybrid Search**: Combines vector similarity with fuzzy text matching
- 🤖 **LLM Analysis**: AI-powered infringement risk assessment
- 📊 **Prometheus Metrics**: Full observability
- ⚡ **Redis Caching**: Fast repeated queries

## Tech Stack
- FastAPI + SQLAlchemy + PostgreSQL/pgvector
- Ollama (nomic-embed-text) for embeddings
- OpenRouter (GPT-4o-mini) for LLM analysis
- Redis for caching
- Prometheus for metrics
    """,
    lifespan=lifespan,
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus instrumentation
if settings.metrics_enabled:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# Include routers
app.include_router(patents_router)
app.include_router(claims_router)
app.include_router(ingest_router)
app.include_router(priorart_router)


# Health check
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Prometheus metrics endpoint (custom)
@app.get("/metrics/custom", tags=["system"])
async def custom_metrics():
    """Custom Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """API root - returns basic info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
