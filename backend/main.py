from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.profiler import PerformanceProfilerMiddleware, get_perf_stats, reset_perf_stats, SLOW_THRESHOLD_MS
from app.ai.emotion_detector import emotion_engine
from app.api import auth, emotions, journal, interventions, analytics, chatbot, sos, safe_links, users, websockets, companion

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    logger.info("Starting MINDTRACE AI+ Backend...")
    try:
        await connect_to_mongo()
        await emotion_engine.initialize()
        logger.info(f"[OK] CORS Allowed Origins: {settings.CORS_ORIGINS}")
        logger.info("[OK] All services initialized")
    except Exception as e:
        logger.error(f"Startup failure: {e}")
    yield
    logger.info("Shutting down MINDTRACE AI+ Backend...")
    await close_mongo_connection()
    logger.info("[OK] Shutdown complete")

app = FastAPI(
    title=settings.APP_NAME,
    description="Realtime Emotional Intelligence and Adaptive Wellness Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = [
    "https://mindtrace-frontend.netlify.app",
    "https://mindtrace-ai.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
]
# Add any origins from settings
for origin in settings.CORS_ORIGINS:
    if str(origin) not in origins:
        origins.append(str(origin))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance Profiling Middleware
app.add_middleware(PerformanceProfilerMiddleware)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    # SECURITY: Redact sensitive headers to prevent token leakage in logs
    safe_headers = {
        k: ("***REDACTED***" if k.lower() in ("authorization", "cookie", "x-api-key") else v)
        for k, v in request.headers.items()
    }
    logger.debug(f"Headers: {safe_headers}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/")
async def root():
    return {
        "message": "Welcome to MINDTRACE AI+",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/perf/stats")
async def performance_stats():
    """Returns real-time performance metrics for all API routes."""
    return {
        "stats": get_perf_stats(),
        "slow_threshold_ms": SLOW_THRESHOLD_MS
    }


@app.post("/api/perf/reset")
async def reset_performance_stats():
    """Reset all performance counters (use between test runs)."""
    reset_perf_stats()
    return {"status": "reset"}

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(emotions.router, prefix="/api/emotions", tags=["Emotions"])
app.include_router(journal.router, prefix="/api/journal", tags=["Journaling"])
app.include_router(interventions.router, prefix="/api/interventions", tags=["Interventions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])
app.include_router(sos.router, prefix="/api/sos", tags=["SOS"])
app.include_router(safe_links.router, prefix="/api/safe-links", tags=["Safe Links"])
app.include_router(companion.router, prefix="/api/companion", tags=["Companion"])
app.include_router(websockets.router, prefix="/api/ws", tags=["WebSockets"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
