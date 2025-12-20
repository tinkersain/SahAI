"""
SahAI Agentic State Machine - Planner-Executor-Evaluator Loop
Implements a true agentic workflow with explicit states and transitions
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
import time


class AgentState(Enum):
    """Agent states in the Planner-Executor-Evaluator loop"""
    # Initial states
    IDLE = "idle"
    RECEIVING_INPUT = "receiving_input"
    
    # Planner states
    PLANNING = "planning"
    ANALYZING_INTENT = "analyzing_intent"
    SELECTING_TOOLS = "selecting_tools"
    
    # Executor states  
    EXECUTING = "executing"
    CALLING_TOOL = "calling_tool"
    WAITING_FOR_INFO = "waiting_for_info"
    
    # Evaluator states
    EVALUATING = "evaluating"
    CHECKING_COMPLETENESS = "checking_completeness"
    HANDLING_CONTRADICTION = "handling_contradiction"
    
    # Response states
    GENERATING_RESPONSE = "generating_response"
    COMPLETE = "complete"
    
    # Error states
    ERROR_RECOVERY = "error_recovery"
    CLARIFICATION_NEEDED = "clarification_needed"


class IntentType(Enum):
    """Types of user intents"""
    GREETING = "greeting"
    SCHEME_INQUIRY = "scheme_inquiry"
    ELIGIBILITY_CHECK = "eligibility_check"
    APPLICATION_HELP = "application_help"
    DOCUMENT_INFO = "document_info"
    GENERAL_QUESTION = "general_question"
    PROVIDE_INFO = "provide_info"  # User is providing their info
    CLARIFICATION = "clarification"  # User clarifying previous info
    CORRECTION = "correction"  # User correcting information
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


@dataclass
class ExecutionPlan:
    """Plan created by the Planner"""
    intent: IntentType
    required_tools: List[str]
    required_info: List[str]  # What info we need from user
    available_info: Dict[str, Any]  # What we already have
    missing_info: List[str]  # What we still need
    steps: List[Dict[str, Any]]
    confidence: float
    fallback_strategy: str = "ask_clarification"
    
    def __post_init__(self):
        self.missing_info = [
            info for info in self.required_info 
            if info not in self.available_info
        ]


@dataclass
class ExecutionResult:
    """Result from tool execution"""
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    needs_more_info: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result from the Evaluator"""
    is_complete: bool
    quality_score: float  # 0-1
    issues: List[str]
    suggestions: List[str]
    needs_clarification: bool
    contradiction_detected: bool
    contradiction_details: Optional[Dict[str, Any]] = None
    next_action: str = "respond"  # respond, re-execute, ask_user


@dataclass 
class StateContext:
    """Context maintained across state transitions"""
    session_id: str
    current_state: AgentState
    previous_states: List[AgentState] = field(default_factory=list)
    
    # Input tracking
    current_input: str = ""
    input_confidence: float = 1.0  # From STT
    
    # Planning
    current_plan: Optional[ExecutionPlan] = None
    
    # Execution  
    execution_results: List[ExecutionResult] = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    
    # Evaluation
    evaluation: Optional[EvaluationResult] = None
    
    # Response
    final_response: str = ""
    
    # Error tracking
    error_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    
    # Timestamps
    started_at: float = field(default_factory=time.time)
    state_history: List[Dict] = field(default_factory=list)
    
    def transition_to(self, new_state: AgentState, reason: str = ""):
        """Transition to a new state with logging"""
        self.previous_states.append(self.current_state)
        self.state_history.append({
            "from": self.current_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": time.time()
        })
        self.current_state = new_state
    
    def can_retry(self) -> bool:
        """Check if we can retry after an error"""
        return self.error_count < self.max_retries


class StateMachine:
    """
    Agentic State Machine implementing Planner-Executor-Evaluator loop
    """
    
    def __init__(self):
        self.state_handlers: Dict[AgentState, Callable] = {}
        self.transition_rules: Dict[AgentState, List[AgentState]] = self._init_transitions()
    
    def _init_transitions(self) -> Dict[AgentState, List[AgentState]]:
        """Define valid state transitions"""
        return {
            AgentState.IDLE: [AgentState.RECEIVING_INPUT],
            
            AgentState.RECEIVING_INPUT: [
                AgentState.PLANNING, 
                AgentState.ERROR_RECOVERY
            ],
            
            AgentState.PLANNING: [
                AgentState.ANALYZING_INTENT,
                AgentState.ERROR_RECOVERY
            ],
            
            AgentState.ANALYZING_INTENT: [
                AgentState.SELECTING_TOOLS,
                AgentState.GENERATING_RESPONSE,  # For simple greetings
                AgentState.CLARIFICATION_NEEDED
            ],
            
            AgentState.SELECTING_TOOLS: [
                AgentState.EXECUTING,
                AgentState.WAITING_FOR_INFO,
                AgentState.GENERATING_RESPONSE
            ],
            
            AgentState.EXECUTING: [
                AgentState.CALLING_TOOL,
                AgentState.EVALUATING,
                AgentState.ERROR_RECOVERY
            ],
            
            AgentState.CALLING_TOOL: [
                AgentState.EXECUTING,  # More tools to call
                AgentState.EVALUATING,
                AgentState.WAITING_FOR_INFO,
                AgentState.ERROR_RECOVERY
            ],
            
            AgentState.WAITING_FOR_INFO: [
                AgentState.GENERATING_RESPONSE,
                AgentState.CLARIFICATION_NEEDED
            ],
            
            AgentState.EVALUATING: [
                AgentState.CHECKING_COMPLETENESS,
                AgentState.HANDLING_CONTRADICTION,
                AgentState.GENERATING_RESPONSE
            ],
            
            AgentState.CHECKING_COMPLETENESS: [
                AgentState.GENERATING_RESPONSE,
                AgentState.EXECUTING,  # Re-execute if incomplete
                AgentState.CLARIFICATION_NEEDED
            ],
            
            AgentState.HANDLING_CONTRADICTION: [
                AgentState.CLARIFICATION_NEEDED,
                AgentState.GENERATING_RESPONSE
            ],
            
            AgentState.CLARIFICATION_NEEDED: [
                AgentState.GENERATING_RESPONSE
            ],
            
            AgentState.GENERATING_RESPONSE: [
                AgentState.COMPLETE
            ],
            
            AgentState.ERROR_RECOVERY: [
                AgentState.GENERATING_RESPONSE,
                AgentState.PLANNING,  # Retry
                AgentState.CLARIFICATION_NEEDED
            ],
            
            AgentState.COMPLETE: [
                AgentState.IDLE  # Ready for next input
            ]
        }
    
    def can_transition(self, from_state: AgentState, to_state: AgentState) -> bool:
        """Check if a transition is valid"""
        allowed = self.transition_rules.get(from_state, [])
        return to_state in allowed
    
    def register_handler(self, state: AgentState, handler: Callable):
        """Register a handler for a state"""
        self.state_handlers[state] = handler
    
    def get_handler(self, state: AgentState) -> Optional[Callable]:
        """Get the handler for a state"""
        return self.state_handlers.get(state)


# Singleton state machine instance
_state_machine = StateMachine()


def get_state_machine() -> StateMachine:
    """Get the global state machine instance"""
    return _state_machine
