"""
SahAI Memory - Conversation Memory Management with Contradiction Handling
Handles session data, user info, conversation history, and contradictions
"""
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ContradictionType(Enum):
    """Types of contradictions that can occur"""
    VALUE_CONFLICT = "value_conflict"  # User gave different value for same field
    LOGICAL_CONFLICT = "logical_conflict"  # Values don't make logical sense
    TEMPORAL_CONFLICT = "temporal_conflict"  # Info changed over time


@dataclass
class Contradiction:
    """Record of a detected contradiction"""
    field: str
    old_value: Any
    new_value: Any
    contradiction_type: ContradictionType
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: Optional[str] = None  # "kept_old", "used_new", "user_clarified"
    user_explanation: Optional[str] = None


@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = field(default_factory=time.time)
    extracted_data: Dict[str, Any] = field(default_factory=dict)  # Data extracted from this turn
    intent: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)


@dataclass
class FieldHistory:
    """History of values for a field"""
    field: str
    values: List[Tuple[Any, float, str]] = field(default_factory=list)  # (value, timestamp, source)
    
    def add(self, value: Any, source: str = "user"):
        self.values.append((value, time.time(), source))
    
    def latest(self) -> Optional[Any]:
        return self.values[-1][0] if self.values else None
    
    def has_changes(self) -> bool:
        if len(self.values) < 2:
            return False
        return self.values[-1][0] != self.values[-2][0]


class Memory:
    """
    Session memory for a user conversation
    Tracks: user info, conversation history, current context, and contradictions
    """
    
    # Valid user data fields
    VALID_FIELDS = {
        "age", "income", "gender", "category", "state", 
        "occupation", "disability", "bpl", "area", "name"
    }
    
    # Fields that are unlikely to change (should prompt for confirmation)
    STABLE_FIELDS = {"age", "gender", "category", "disability"}
    
    # Fields that might legitimately change
    MUTABLE_FIELDS = {"income", "state", "area", "occupation", "bpl"}
    
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
        
        # Confirmation and contradiction tracking
        self._confirmed: Dict[str, bool] = {}
        self._field_history: Dict[str, FieldHistory] = {}
        self._contradictions: List[Contradiction] = []
        self._pending_contradictions: List[Contradiction] = []  # Awaiting resolution
        
        # Error and failure tracking
        self._stt_errors: int = 0
        self._clarification_requests: int = 0
        self._last_failure: Optional[Dict[str, Any]] = None
    
    # ==================== User Data Management with Contradiction Handling ====================
    
    def set(self, key: str, value: Any, confirmed: bool = False, source: str = "user") -> Tuple[bool, Optional[Contradiction]]:
        """
        Set a user data field with contradiction detection
        
        Returns:
            (success, contradiction) - If contradiction detected, returns the Contradiction object
        """
        if key not in self.VALID_FIELDS:
            return False, None
        
        # Track field history
        if key not in self._field_history:
            self._field_history[key] = FieldHistory(field=key)
        
        # Check for contradiction
        contradiction = None
        if key in self._data and self._data[key] is not None and self._data[key] != value:
            old_value = self._data[key]
            
            # Determine contradiction type
            if key in self.STABLE_FIELDS:
                # Stable fields shouldn't change - likely an error or correction
                contradiction = Contradiction(
                    field=key,
                    old_value=old_value,
                    new_value=value,
                    contradiction_type=ContradictionType.VALUE_CONFLICT
                )
            elif key in self.MUTABLE_FIELDS:
                # Mutable fields might change - check if it's a significant difference
                if key == "income" and abs(old_value - value) > 50000:
                    contradiction = Contradiction(
                        field=key,
                        old_value=old_value,
                        new_value=value,
                        contradiction_type=ContradictionType.VALUE_CONFLICT
                    )
                elif key == "age" and abs(old_value - value) > 1:
                    contradiction = Contradiction(
                        field=key,
                        old_value=old_value,
                        new_value=value,
                        contradiction_type=ContradictionType.VALUE_CONFLICT
                    )
            
            if contradiction:
                self._contradictions.append(contradiction)
                
                # If confirmed data is being changed, add to pending
                if self._confirmed.get(key):
                    self._pending_contradictions.append(contradiction)
                    return False, contradiction  # Don't update, ask user first
        
        # Update the data
        self._data[key] = value
        self._confirmed[key] = confirmed
        self._field_history[key].add(value, source)
        self.last_activity = time.time()
        
        return True, contradiction
    
    def resolve_contradiction(self, field: str, use_new_value: bool, user_explanation: str = "") -> bool:
        """Resolve a pending contradiction"""
        for contradiction in self._pending_contradictions:
            if contradiction.field == field and not contradiction.resolved:
                if use_new_value:
                    self._data[field] = contradiction.new_value
                    contradiction.resolution = "used_new"
                else:
                    contradiction.resolution = "kept_old"
                
                contradiction.resolved = True
                contradiction.user_explanation = user_explanation
                self._pending_contradictions.remove(contradiction)
                self._confirmed[field] = True  # Mark as confirmed after resolution
                return True
        return False
    
    def has_pending_contradictions(self) -> bool:
        """Check if there are unresolved contradictions"""
        return len(self._pending_contradictions) > 0
    
    def get_pending_contradictions(self) -> List[Contradiction]:
        """Get all pending contradictions"""
        return self._pending_contradictions.copy()
    
    def get_contradiction_message_hi(self) -> Optional[str]:
        """Get Hindi message for pending contradiction"""
        if not self._pending_contradictions:
            return None
        
        c = self._pending_contradictions[0]
        field_names_hi = {
            "age": "उम्र",
            "income": "आय",
            "gender": "लिंग",
            "category": "श्रेणी",
            "occupation": "व्यवसाय",
            "area": "क्षेत्र"
        }
        field_name = field_names_hi.get(c.field, c.field)
        
        return f"आपने पहले {field_name} '{c.old_value}' बताई थी, अब '{c.new_value}' बता रहे हैं। कौन सी सही है?"
    
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
        self._field_history = {}
        self._contradictions = []
        self._pending_contradictions = []
    
    # ==================== Failure Tracking ====================
    
    def record_stt_error(self, error_type: str = "recognition"):
        """Record an STT failure"""
        self._stt_errors += 1
        self._last_failure = {
            "type": "stt_error",
            "error_type": error_type,
            "timestamp": time.time(),
            "count": self._stt_errors
        }
    
    def record_clarification_request(self, field: str):
        """Record that we asked for clarification"""
        self._clarification_requests += 1
        self._last_failure = {
            "type": "clarification_needed",
            "field": field,
            "timestamp": time.time()
        }
    
    def get_failure_context(self) -> Dict[str, Any]:
        """Get context about recent failures for better error handling"""
        return {
            "stt_errors": self._stt_errors,
            "clarification_requests": self._clarification_requests,
            "last_failure": self._last_failure,
            "has_pending_contradictions": self.has_pending_contradictions()
        }
    
    # ==================== Conversation History ====================
    
    def add_turn(self, role: str, content: str, extracted_data: Dict[str, Any] = None, 
                 intent: str = None, tools_used: List[str] = None):
        """Add a conversation turn with metadata"""
        turn = ConversationTurn(
            role=role, 
            content=content,
            extracted_data=extracted_data or {},
            intent=intent,
            tools_used=tools_used or []
        )
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
            "recent_history": self.get_recent_history(3),
            "has_contradictions": self.has_pending_contradictions(),
            "failure_context": self.get_failure_context()
        }
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get complete memory state for debugging/logging"""
        return {
            "session_id": self.session_id,
            "user_data": self._data,
            "confirmed_fields": self._confirmed,
            "history_length": len(self.history),
            "contradictions": [
                {
                    "field": c.field,
                    "old": c.old_value,
                    "new": c.new_value,
                    "resolved": c.resolved
                } for c in self._contradictions
            ],
            "pending_contradictions": len(self._pending_contradictions),
            "failure_context": self.get_failure_context()
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
