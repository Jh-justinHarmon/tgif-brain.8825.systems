#!/usr/bin/env python3
"""
8825 User Context Utilities

Provides a canonical way to resolve the current user identity across all 8825 components.
This is the single source of truth for "who is the current user" in multi-user scenarios.

Usage:
    from utils.user_context import get_current_user_id
    
    user_id = get_current_user_id()  # Returns resolved user ID
    user_id = get_current_user_id(explicit_id="alice")  # Uses explicit if provided
"""

import os
from typing import Optional


# Default user ID when no other source is available
DEFAULT_USER_ID = "local"


def get_current_user_id(explicit_id: Optional[str] = None) -> str:
    """
    Resolve the current user ID from available sources.
    
    Priority order:
    1. Explicit ID passed as parameter (highest priority)
    2. USER_ID environment variable
    3. USER_NAME environment variable (8825 convention)
    4. USER environment variable (system username)
    5. DEFAULT_USER_ID ("local")
    
    Args:
        explicit_id: If provided, this is returned directly (allows callers to override)
    
    Returns:
        Resolved user ID string
    
    Examples:
        >>> get_current_user_id()  # Returns from env or "local"
        'local'
        
        >>> get_current_user_id(explicit_id="alice")  # Returns explicit
        'alice'
        
        >>> os.environ["USER_ID"] = "bob"
        >>> get_current_user_id()  # Returns from env
        'bob'
    """
    # Priority 1: Explicit parameter
    if explicit_id:
        return explicit_id
    
    # Priority 2: USER_ID env var (most specific)
    user_id = os.environ.get("USER_ID")
    if user_id:
        return user_id
    
    # Priority 3: USER_NAME env var (8825 convention from paths.py)
    user_name = os.environ.get("USER_NAME")
    if user_name:
        return user_name
    
    # Priority 4: System USER env var
    system_user = os.environ.get("USER")
    if system_user:
        return system_user
    
    # Priority 5: Default
    return DEFAULT_USER_ID


def get_user_context() -> dict:
    """
    Get full user context for logging/debugging.
    
    Returns:
        Dict with user_id and source information
    """
    explicit_id = None
    
    if os.environ.get("USER_ID"):
        source = "USER_ID env"
        user_id = os.environ["USER_ID"]
    elif os.environ.get("USER_NAME"):
        source = "USER_NAME env"
        user_id = os.environ["USER_NAME"]
    elif os.environ.get("USER"):
        source = "USER env (system)"
        user_id = os.environ["USER"]
    else:
        source = "default"
        user_id = DEFAULT_USER_ID
    
    return {
        "user_id": user_id,
        "source": source,
        "is_default": user_id == DEFAULT_USER_ID,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_user_context(), indent=2))
