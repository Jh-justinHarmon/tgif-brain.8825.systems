"""
Maestra Backend - Unified Request/Response Models
Canonical data structures for all Maestra API interactions
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class SurfaceContext(BaseModel):
    """Context from the calling surface (Windsurf, extension, CLI, etc.)"""
    file_path: Optional[str] = None
    workspace: Optional[str] = None
    screen_context: Optional[str] = None
    page_url: Optional[str] = None
    selection: Optional[str] = None


class MaestraRequest(BaseModel):
    """Unified request model for all Maestra interactions"""
    user_id: str = Field(..., description="User identifier (e.g., 'justinharmon')")
    surface_id: str = Field(..., description="Source surface (windsurf, browser_ext, goose, mobile)")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    message: str = Field(..., description="User message/question")
    mode_hint: Optional[str] = Field(None, description="Suggested mode (advisor, tutorial, router, etc.)")
    surface_context: Optional[SurfaceContext] = Field(default_factory=SurfaceContext, description="Context from surface")


# ============================================================================
# Response Models
# ============================================================================

class ArtifactReference(BaseModel):
    """Reference to a Library artifact (Knowledge, Decision, Pattern, etc.)"""
    type: str = Field(..., description="Artifact type (knowledge, decision, pattern, project, achievement)")
    id: str = Field(..., description="Artifact ID")
    title: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ActionReference(BaseModel):
    """Reference to an action Maestra can take"""
    type: str = Field(..., description="Action type (create_library_entry, run_tool, deploy, etc.)")
    id: str = Field(..., description="Action ID")
    requires_confirmation: bool = Field(default=False)


class MaestraEnvelope(BaseModel):
    """Unified response envelope for all Maestra interactions"""
    reply: str = Field(..., description="The response text")
    mode: str = Field(..., description="Mode used (advisor, tutorial, router, etc.)")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    source: str = Field(default="local", description="Source (local or cloud)")
    version: str = Field(default="2.0.0", description="Backend version")
    artifacts: List[ArtifactReference] = Field(default_factory=list, description="Referenced artifacts")
    actions: List[ActionReference] = Field(default_factory=list, description="Suggested actions")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata (latency_ms, model, tokens, cost_usd, etc.)")


# ============================================================================
# Legacy Models (for backward compatibility)
# ============================================================================

class AdvisorAskRequest(BaseModel):
    """Legacy request model for /api/maestra/advisor/ask"""
    session_id: str = Field(default="default", description="Session identifier")
    user_id: str = Field(default="anonymous", description="User identifier")
    question: Optional[str] = Field(None, description="The question (legacy field)")
    message: Optional[str] = Field(None, description="The question (new field)")
    mode: Literal["quick", "deep"] = Field(default="quick", description="Response mode")
    context_hints: List[str] = Field(default_factory=list, description="Optional context hints")

    @property
    def get_question(self) -> str:
        """Get the question from either field."""
        return self.message or self.question or ""


class SourceReference(BaseModel):
    """Source reference for answers"""
    title: str
    type: str
    confidence: float = 1.0
    excerpt: Optional[str] = None
    url: Optional[str] = None


class AdvisorAskResponse(BaseModel):
    """Legacy response model for /api/maestra/advisor/ask"""
    answer: str = Field(..., description="The advisor's answer")
    session_id: str = Field(..., description="Session ID for follow-up")
    job_id: Optional[str] = None
    sources: List[SourceReference] = Field(default_factory=list)
    trace_id: str = Field(..., description="Unique trace ID")
    mode: str = Field(..., description="Mode used")
    processing_time_ms: int = Field(..., description="Processing time")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    service: str = Field(default="maestra-backend", description="Service name")
    version: str = Field(default="2.0.0", description="Backend version")
    brain_id: str = Field(default="maestra", description="Brain identifier")
    uptime_seconds: int = Field(default=0, description="Service uptime in seconds")
    port: int = Field(default=8825, description="Service port")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency health status")
