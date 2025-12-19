"""
SahAI Memory - Conversation Memory Management
Handles session data, user info, and conversation history
"""
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = field(default_factory=time.time)


class Memory:
    """
    Session memory for a user conversation
    Tracks: user info, conversation history, current context
    """
    
    # Valid user data fields
    VALID_FIELDS = {
        "age", "income", "gender", "category", "state", 
        "occupation", "disability", "bpl", "area"
    }
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = time.time()
        self.last_activity = time.time()
        
        # User data storage
        self._data: Dict[str, Any] = {}
        
        # Conversation history
        self.history: List[ConversationTurn] = []
        
        # Current context
        self.current_scheme: Optional[str] = None
        self.current_intent: Optional[str] = None
        
        # Contradiction tracking (for handling conflicting info)
        self._confirmed: Dict[str, bool] = {}
    
    # ==================== User Data Management ====================
    
    def set(self, key: str, value: Any, confirmed: bool = False) -> bool:
        """
        Set a user data field
        Handles contradictions: won't overwrite confirmed data
        """
        if key not in self.VALID_FIELDS:
            return False
        
        # Check for contradiction
        if key in self._data and self._confirmed.get(key) and self._data[key] != value:
            # Don't overwrite confirmed data - this is a contradiction
            print(f"Contradiction detected for {key}: {self._data[key]} vs {value}")
            return False
        
        self._data[key] = value
        self._confirmed[key] = confirmed
        self.last_activity = time.time()
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a user data field"""
        return self._data.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if a field has a value"""
        return key in self._data and self._data[key] is not None
    
    def get_user_data(self) -> Dict[str, Any]:
        """Get all user data"""
        return self._data.copy()
    
    def clear_user_data(self):
        """Clear all user data"""
        self._data = {}
        self._confirmed = {}
    
    # ==================== Conversation History ====================
    
    def add_turn(self, role: str, content: str):
        """Add a conversation turn"""
        turn = ConversationTurn(role=role, content=content)
        self.history.append(turn)
        self.last_activity = time.time()
        
        # Keep only last 20 turns to manage memory
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get_recent_history(self, n: int = 5) -> List[Dict[str, str]]:
        """Get last n conversation turns"""
        return [
            {"role": t.role, "content": t.content}
            for t in self.history[-n:]
        ]
    
    def get_history_text(self, n: int = 10) -> str:
        """Get conversation history as formatted text for LLM"""
        if not self.history:
            return ""
        
        lines = []
        for turn in self.history[-n:]:
            role_label = "उपयोगकर्ता" if turn.role == "user" else "सहाई"
            lines.append(f"{role_label}: {turn.content}")
        
        return "\n".join(lines)
    
    def update_user_data(self, key: str, value: Any):
        """Update user data field (alias for set)"""
        self.set(key, value)
    
    @property
    def user_data(self) -> Dict[str, Any]:
        """Property to access user data directly"""
        return self._data
    
    def get_context(self) -> Dict[str, Any]:
        """Get full context for AI"""
        return {
            "user_data": self._data,
            "current_scheme": self.current_scheme,
            "current_intent": self.current_intent,
            "recent_history": self.get_recent_history(3)
        }
    
    # ==================== Session Management ====================
    
    def is_expired(self, timeout_seconds: int = 1800) -> bool:
        """Check if session is expired (default 30 min)"""
        return (time.time() - self.last_activity) > timeout_seconds
    
    def reset(self):
        """Reset memory for new conversation"""
        self._data = {}
        self._confirmed = {}
        self.history = []
        self.current_scheme = None
        self.current_intent = None


class SessionManager:
    """
    Manages multiple user sessions
    """
    
    def __init__(self):
        self._sessions: Dict[str, Memory] = {}
    
    def get(self, session_id: str) -> Optional[Memory]:
        """Get session by ID"""
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            return session
        return None
    
    def add(self, memory: Memory):
        """Add a new session"""
        self._sessions[memory.session_id] = memory
    
    def remove(self, session_id: str):
        """Remove a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def cleanup_expired(self):
        """Remove all expired sessions"""
        expired = [
            sid for sid, mem in self._sessions.items()
            if mem.is_expired()
        ]
        for sid in expired:
            del self._sessions[sid]
        
        if expired:
            print(f"Cleaned up {len(expired)} expired sessions")
