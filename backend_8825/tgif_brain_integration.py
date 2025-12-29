"""
TGIF Brain Integration for Maestra Backend

Routes TGIF-specific requests through the unified Maestra Backend on port 8825.
Consolidates TGIF brain functionality into the canonical endpoint with mode_hint="focus_coach".
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class TGIFRequest(BaseModel):
    """TGIF brain request"""
    user_id: str
    conversation_id: str
    message: str
    context: Optional[str] = None  # TGIF context (restaurant, project, etc.)
    focus_area: Optional[str] = None  # TGIF, RAL, LHL, 76


class TGIFResponse(BaseModel):
    """TGIF brain response"""
    reply: str
    focus_area: str
    conversation_id: str
    context: Optional[Dict[str, Any]] = None


def convert_tgif_to_canonical(tgif_request: TGIFRequest) -> Dict[str, Any]:
    """
    Convert TGIF brain request to canonical Maestra Backend format.
    
    Routes through /api/maestra/core with mode_hint="focus_coach"
    """
    return {
        "user_id": tgif_request.user_id,
        "surface_id": "tgif_brain",
        "conversation_id": tgif_request.conversation_id,
        "message": tgif_request.message,
        "mode_hint": "focus_coach",  # Routes to focus coach handler
        "surface_context": {
            "focus_area": tgif_request.focus_area or "TGIF",
            "context": tgif_request.context
        }
    }


def convert_canonical_to_tgif(canonical_response: Dict[str, Any]) -> TGIFResponse:
    """Convert canonical Maestra Backend response to TGIF format"""
    return TGIFResponse(
        reply=canonical_response.get("reply", ""),
        focus_area=canonical_response.get("surface_context", {}).get("focus_area", "TGIF"),
        conversation_id=canonical_response.get("conversation_id", ""),
        context=canonical_response.get("surface_context", {})
    )


# Integration instructions:
# 1. Add to Maestra Backend server.py:
#    @app.post("/tgif/ask", response_model=TGIFResponse)
#    async def tgif_ask(request: TGIFRequest) -> TGIFResponse:
#        canonical_request = convert_tgif_to_canonical(request)
#        canonical_response = await maestra_core(canonical_request)
#        return convert_canonical_to_tgif(canonical_response)
#
# 2. Update Replit .replit to run Maestra Backend:
#    run = "python -m maestra_backend --mode cloud --port 8000"
#
# 3. TGIF brain on Replit should call:
#    POST http://localhost:8000/tgif/ask
#    or
#    POST http://localhost:8000/api/maestra/core with mode_hint="focus_coach"
