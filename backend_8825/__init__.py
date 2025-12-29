"""
Maestra Backend - Unified HTTP Service
Single canonical backend for all Maestra surfaces (Windsurf, browser extension, CLI, mobile)

Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "8825 Team"

from .server import app
from .models import MaestraRequest, MaestraEnvelope

__all__ = ["app", "MaestraRequest", "MaestraEnvelope"]
