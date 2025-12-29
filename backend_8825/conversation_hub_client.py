"""
Conversation Hub Client for Maestra Backend
Handles conversation logging, state persistence, and continuity across surfaces

Integrates with Conversation Hub for durable storage and cross-surface context.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

logger = logging.getLogger('MaestraConversationHub')

# Configuration
CONVERSATION_HUB_ROOT = Path.home() / ".8825" / "conversations"
CONVERSATION_HUB_ROOT.mkdir(parents=True, exist_ok=True)


class ConversationHubClient:
    """
    Client for Maestra to interact with Conversation Hub.
    
    Responsibilities:
    - Create/retrieve conversations
    - Append messages to conversations
    - Maintain conversation metadata
    - Link artifacts (Library entries)
    - Track conversation status
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """Initialize Conversation Hub client"""
        self.root_path = root_path or CONVERSATION_HUB_ROOT
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root_path / "index.json"
        logger.info(f"[ConversationHubClient] Initialized with root: {self.root_path}")
    
    def _get_conversation_path(self, conversation_id: str) -> Path:
        """Get file path for a conversation"""
        return self.root_path / f"{conversation_id}.json"
    
    def _load_index(self) -> Dict[str, Any]:
        """Load conversation index"""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
        
        return {
            "conversations": [],
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    def _save_index(self, index: Dict[str, Any]):
        """Save conversation index"""
        try:
            index["last_updated"] = datetime.utcnow().isoformat() + "Z"
            with open(self.index_path, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _update_index(self, conversation_id: str, topic: str, surfaces: List[str]):
        """Update index with conversation summary"""
        index = self._load_index()
        
        # Find or create entry
        entry = None
        for conv in index["conversations"]:
            if conv["id"] == conversation_id:
                entry = conv
                break
        
        if not entry:
            entry = {
                "id": conversation_id,
                "topic": topic,
                "surfaces": surfaces,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "message_count": 0,
                "status": "active"
            }
            index["conversations"].append(entry)
        else:
            entry["updated_at"] = datetime.utcnow().isoformat() + "Z"
            entry["surfaces"] = list(set(entry.get("surfaces", []) + surfaces))
        
        self._save_index(index)
    
    def create_conversation(
        self,
        topic: str,
        user_id: str,
        surface_id: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            topic: Conversation topic/title
            user_id: User identifier
            surface_id: Source surface (windsurf, browser_ext, goose, mobile)
            tags: Optional tags for categorization
        
        Returns:
            Conversation ID
        """
        conversation_id = f"conv_{datetime.utcnow().strftime('%Y-%m-%d')}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        conversation = {
            "id": conversation_id,
            "topic": topic,
            "owner": user_id,
            "surfaces": [surface_id],
            "tags": tags or [],
            "messages": [],
            "artifacts": [],
            "meta": {
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "status": "active",
                "message_count": 0
            }
        }
        
        # Save conversation
        conv_path = self._get_conversation_path(conversation_id)
        with open(conv_path, 'w') as f:
            json.dump(conversation, f, indent=2)
        
        # Update index
        self._update_index(conversation_id, topic, [surface_id])
        
        logger.info(f"[ConversationHubClient] Created conversation: {conversation_id}")
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation by ID.
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            Conversation dict or None if not found
        """
        conv_path = self._get_conversation_path(conversation_id)
        
        if not conv_path.exists():
            logger.warning(f"Conversation not found: {conversation_id}")
            return None
        
        try:
            with open(conv_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
            return None
    
    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        surface_id: str,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Append a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant)
            content: Message content
            surface_id: Source surface
            mode: Optional mode (advisor, tutorial, etc.)
            metadata: Optional metadata (latency_ms, tokens, cost_usd, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            return False
        
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "surface": surface_id,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "meta": metadata or {}
        }
        
        conversation["messages"].append(message)
        conversation["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        conversation["meta"]["message_count"] = len(conversation["messages"])
        
        # Update surfaces list
        if surface_id not in conversation["surfaces"]:
            conversation["surfaces"].append(surface_id)
        
        # Save conversation
        try:
            conv_path = self._get_conversation_path(conversation_id)
            with open(conv_path, 'w') as f:
                json.dump(conversation, f, indent=2)
            
            # Update index
            self._update_index(
                conversation_id,
                conversation["topic"],
                conversation["surfaces"]
            )
            
            logger.debug(f"[ConversationHubClient] Appended message to {conversation_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to append message: {e}")
            return False
    
    def link_artifact(
        self,
        conversation_id: str,
        artifact_type: str,
        artifact_id: str,
        title: Optional[str] = None,
        confidence: float = 1.0
    ) -> bool:
        """
        Link a Library artifact to a conversation.
        
        Args:
            conversation_id: Conversation ID
            artifact_type: Artifact type (knowledge, decision, pattern, project, achievement)
            artifact_id: Artifact ID
            title: Optional artifact title
            confidence: Confidence score (0-1)
        
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            return False
        
        artifact = {
            "type": artifact_type,
            "id": artifact_id,
            "title": title,
            "confidence": confidence,
            "linked_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Check for duplicates
        for existing in conversation["artifacts"]:
            if existing["id"] == artifact_id:
                logger.debug(f"Artifact already linked: {artifact_id}")
                return True
        
        conversation["artifacts"].append(artifact)
        conversation["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Save conversation
        try:
            conv_path = self._get_conversation_path(conversation_id)
            with open(conv_path, 'w') as f:
                json.dump(conversation, f, indent=2)
            
            logger.debug(f"[ConversationHubClient] Linked artifact {artifact_id} to {conversation_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to link artifact: {e}")
            return False
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages
        
        Returns:
            List of messages
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        messages = conversation.get("messages", [])
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def close_conversation(self, conversation_id: str) -> bool:
        """
        Mark a conversation as closed.
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation["meta"]["status"] = "closed"
        conversation["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        try:
            conv_path = self._get_conversation_path(conversation_id)
            with open(conv_path, 'w') as f:
                json.dump(conversation, f, indent=2)
            
            logger.info(f"[ConversationHubClient] Closed conversation: {conversation_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to close conversation: {e}")
            return False
    
    def list_conversations(
        self,
        user_id: Optional[str] = None,
        surface_id: Optional[str] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """
        List conversations with optional filtering.
        
        Args:
            user_id: Filter by user
            surface_id: Filter by surface
            status: Filter by status (default: active)
        
        Returns:
            List of conversation summaries
        """
        index = self._load_index()
        results = []
        
        for conv_summary in index.get("conversations", []):
            if status and conv_summary.get("status") != status:
                continue
            if user_id and conv_summary.get("owner") != user_id:
                continue
            if surface_id and surface_id not in conv_summary.get("surfaces", []):
                continue
            
            results.append(conv_summary)
        
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)


# Global client instance
_client: Optional[ConversationHubClient] = None


def get_client() -> ConversationHubClient:
    """Get or create global Conversation Hub client"""
    global _client
    if _client is None:
        _client = ConversationHubClient()
    return _client
