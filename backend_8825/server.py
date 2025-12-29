"""
8825 Backend - FastAPI Server
Unified HTTP service for all 8825 surfaces and functions

Canonical endpoint: POST /api/maestra/core
Legacy endpoints: /api/maestra/advisor/ask (aliased for backward compatibility)
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models import (
    MaestraRequest,
    MaestraEnvelope,
    AdvisorAskRequest,
    AdvisorAskResponse,
    HealthResponse,
)
from .conversation_hub_client import get_client as get_conversation_hub
from .observability import (
    get_metrics_collector,
    get_slack_alerter,
    RequestMetrics,
    JSONLogger
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger('8825Backend')

# Configuration
MAESTRA_MODE = os.getenv("MAESTRA_MODE", "local")  # local or cloud
MAESTRA_API_KEY = os.getenv("MAESTRA_API_KEY", "")
RATE_LIMIT_REQUESTS = int(os.getenv("MAESTRA_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("MAESTRA_RATE_LIMIT_WINDOW", "60"))

# Initialize FastAPI
app = FastAPI(
    title="8825 Backend",
    description="Unified HTTP service for all 8825 surfaces and functions",
    version="2.0.0"
)

# Rate limiting (cloud only)
if MAESTRA_MODE == "cloud":
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
else:
    limiter = None

# CORS middleware for all surfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service state
SERVICE_START_TIME = datetime.utcnow()


# ============================================================================
# Metrics Endpoint
# ============================================================================

@app.get("/metrics")
async def metrics_endpoint() -> Dict[str, Any]:
    """
    Metrics endpoint for observability.
    Returns system metrics, request counts, latency, costs, etc.
    """
    metrics_collector = get_metrics_collector()
    hub = get_conversation_hub()
    
    # Count active conversations
    active_convs = hub.list_conversations(status="active")
    
    system_metrics = metrics_collector.get_system_metrics(len(active_convs))
    
    return {
        "timestamp": system_metrics.timestamp,
        "uptime_seconds": system_metrics.uptime_seconds,
        "total_requests": system_metrics.total_requests,
        "total_errors": system_metrics.total_errors,
        "avg_latency_ms": system_metrics.avg_latency_ms,
        "total_cost_usd": system_metrics.total_cost_usd,
        "active_conversations": system_metrics.active_conversations,
        "service": "8825-backend",
        "version": "2.0.0"
    }


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Returns service status, version, and dependency health.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    return HealthResponse(
        status="healthy",
        service="8825-backend",
        version="2.0.0",
        brain_id="maestra",
        uptime_seconds=int(uptime),
        port=8825,
        timestamp=datetime.utcnow(),
        dependencies={
            "jh_brain": "unknown",
            "memory_hub": "unknown",
            "conversation_hub": "unknown",
            "deep_research": "unknown"
        }
    )


# ============================================================================
# Canonical Endpoint: /api/maestra/core
# ============================================================================

@app.post("/api/maestra/core")
async def maestra_core(
    request: MaestraRequest,
    x_api_key: Optional[str] = Header(None)
) -> MaestraEnvelope:
    """
    Canonical Maestra endpoint.
    
    Unified entry point for all surfaces (Windsurf, browser extension, CLI, mobile).
    Integrates with Conversation Hub for state persistence and cross-surface continuity.
    
    Request:
    - user_id: User identifier
    - surface_id: Source surface (windsurf, browser_ext, goose, mobile)
    - conversation_id: Conversation ID for continuity
    - message: User message/question
    - mode_hint: Optional mode suggestion (advisor, tutorial, router, etc.)
    - surface_context: Optional context from the surface
    
    Response:
    - reply: The response text
    - mode: Mode used
    - conversation_id: Conversation ID for continuity
    - source: "local" or "cloud"
    - version: Backend version
    - artifacts: Referenced Library artifacts
    - actions: Suggested actions
    - meta: Metadata (latency_ms, model, tokens, cost_usd, etc.)
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate API key for cloud deployment
        if MAESTRA_MODE == "cloud":
            if not MAESTRA_API_KEY:
                logger.error("[MaestraCore] Cloud mode but MAESTRA_API_KEY not set")
                raise HTTPException(status_code=500, detail="Server misconfiguration")
            
            if not x_api_key or x_api_key != MAESTRA_API_KEY:
                logger.warning(f"[MaestraCore] Invalid API key from {request.surface_id}")
                raise HTTPException(status_code=401, detail="Invalid API key")
        
        logger.info(f"[MaestraCore] Request from {request.surface_id}: {request.message[:50]}...")
        
        # Get Conversation Hub client
        hub = get_conversation_hub()
        
        # Get or create conversation
        conversation = hub.get_conversation(request.conversation_id)
        if not conversation:
            logger.info(f"[MaestraCore] Creating new conversation: {request.conversation_id}")
            request.conversation_id = hub.create_conversation(
                topic=request.message[:100],
                user_id=request.user_id,
                surface_id=request.surface_id
            )
        else:
            logger.info(f"[MaestraCore] Resuming conversation: {request.conversation_id}")
        
        # Log user message to Conversation Hub
        hub.append_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message,
            surface_id=request.surface_id,
            mode=request.mode_hint,
            metadata={
                "file_path": request.surface_context.file_path if request.surface_context else None,
                "workspace": request.surface_context.workspace if request.surface_context else None
            }
        )
        
        # TODO: Wire to actual Maestra Core orchestration
        # For now, return a placeholder response
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        mode = request.mode_hint or "advisor"
        reply = "Maestra Core is operational. This is a placeholder response. Wire to actual orchestration logic."
        cost_usd = 0.0
        tokens = 0
        status_code = 200
        
        # Log assistant response to Conversation Hub
        hub.append_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=reply,
            surface_id=request.surface_id,
            mode=mode,
            metadata={
                "latency_ms": latency_ms,
                "model": "placeholder",
                "tokens": tokens,
                "cost_usd": cost_usd
            }
        )
        
        # Record metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.record_request(
            RequestMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                request_id=str(uuid.uuid4()),
                surface_id=request.surface_id,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                mode=mode,
                latency_ms=latency_ms,
                status_code=status_code,
                tokens=tokens,
                cost_usd=cost_usd
            )
        )
        
        return MaestraEnvelope(
            reply=reply,
            mode=mode,
            conversation_id=request.conversation_id,
            source="local",
            version="2.0.0",
            artifacts=[],
            actions=[],
            meta={
                "latency_ms": latency_ms,
                "model": "placeholder",
                "tokens": tokens,
                "cost_usd": cost_usd
            }
        )
    
    except HTTPException as e:
        # HTTP exceptions (auth errors, etc.) - record metrics and re-raise
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        metrics_collector = get_metrics_collector()
        metrics_collector.record_request(
            RequestMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                request_id=str(uuid.uuid4()),
                surface_id=request.surface_id,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                mode=request.mode_hint or "error",
                latency_ms=latency_ms,
                status_code=e.status_code,
                tokens=0,
                cost_usd=0.0,
                error=e.detail
            )
        )
        raise
    
    except Exception as e:
        # Unexpected errors
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.error(f"[MaestraCore] Error: {e}", exc_info=True)
        
        # Record error metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.record_request(
            RequestMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                request_id=str(uuid.uuid4()),
                surface_id=request.surface_id,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                mode=request.mode_hint or "error",
                latency_ms=latency_ms,
                status_code=500,
                tokens=0,
                cost_usd=0.0,
                error=str(e)
            )
        )
        
        return MaestraEnvelope(
            reply=f"Error: {str(e)}",
            mode="error",
            conversation_id=request.conversation_id,
            source="local",
            version="2.0.0",
            artifacts=[],
            actions=[],
            meta={"error": str(e)}
        )


# ============================================================================
# Legacy Endpoint: /api/maestra/advisor/ask (Backward Compatibility)
# ============================================================================

@app.post("/api/maestra/advisor/ask")
async def advisor_ask(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Legacy advisor endpoint for backward compatibility.
    Proxies to /api/maestra/core with mode_hint='advisor'.
    """
    try:
        logger.info(f"[AdvisorLegacy] Request: {request.get_question[:50]}...")
        
        # Convert legacy request to canonical request
        canonical_request = MaestraRequest(
            user_id=request.user_id,
            surface_id="legacy_advisor",
            conversation_id=request.session_id,
            message=request.get_question,
            mode_hint="advisor"
        )
        
        # Call canonical endpoint
        envelope = await maestra_core(canonical_request)
        
        # Convert canonical response to legacy response
        return AdvisorAskResponse(
            answer=envelope.reply,
            session_id=envelope.conversation_id,
            job_id=None,
            sources=[],
            trace_id=envelope.conversation_id,
            mode="quick",
            processing_time_ms=envelope.meta.get("latency_ms", 0)
        )
    
    except Exception as e:
        logger.error(f"[AdvisorLegacy] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Alias Routes (for extension compatibility)
# ============================================================================

@app.post("/api/maestra/advisor/ask", response_model=AdvisorAskResponse)
async def advisor_ask_alias(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """Alias for /api/maestra/advisor/ask"""
    return await advisor_ask(request)


# ============================================================================
# Consolidated Endpoints (from builder_mcp, ingestion_orchestrator, etc.)
# ============================================================================

@app.get("/notifications")
async def get_notifications():
    """Get orchestrator notifications (consolidated from ingestion_orchestrator)"""
    return {
        "notifications": [],
        "total": 0,
        "service": "maestra-backend",
        "version": "2.0.0"
    }


@app.get("/workflows")
async def list_workflows():
    """List all workflows (consolidated from builder_mcp)"""
    return {
        "workflows": [],
        "total": 0,
        "service": "maestra-backend",
        "version": "2.0.0"
    }


@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow status (consolidated from builder_mcp)"""
    return {
        "id": workflow_id,
        "status": "unknown",
        "service": "maestra-backend",
        "version": "2.0.0"
    }


@app.get("/conversations/{conversation_id}")
async def get_conversation_web(conversation_id: str):
    """Get conversation (web endpoint, consolidated from ingestion_orchestrator)"""
    hub = get_conversation_hub()
    conversation = hub.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


# ============================================================================
# TGIF Brain Integration (consolidated from separate MCP server)
# ============================================================================

@app.post("/tgif/ask")
async def tgif_ask(request: MaestraRequest):
    """TGIF brain endpoint (consolidated from separate MCP server)"""
    # Route through canonical endpoint with focus_coach mode
    request.mode_hint = "focus_coach"
    request.surface_id = "tgif_brain"
    return await maestra_core(request)


@app.get("/tgif/health")
async def tgif_health():
    """TGIF brain health check"""
    return {
        "status": "healthy",
        "service": "maestra-backend-tgif",
        "version": "2.0.0",
        "mode": "focus_coach",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("[8825Backend] Starting 8825 Backend v2.0.0")
    logger.info(f"[8825Backend] Listening on http://localhost:8825")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("[8825Backend] Shutting down 8825 Backend")
