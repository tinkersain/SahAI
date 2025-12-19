"""
SahAI Failure Handler - Robust Error Recovery System
Handles STT errors, incomplete information, and various failure scenarios
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import time


class FailureType(Enum):
    """Types of failures the system can encounter"""
    # STT Failures
    STT_NO_AUDIO = "stt_no_audio"
    STT_UNCLEAR = "stt_unclear"
    STT_LANGUAGE_ERROR = "stt_language_error"
    STT_PARTIAL = "stt_partial"  # Only partial transcription
    
    # Input Failures
    INPUT_EMPTY = "input_empty"
    INPUT_UNCLEAR = "input_unclear"
    INPUT_OFF_TOPIC = "input_off_topic"
    
    # Data Failures
    MISSING_REQUIRED_INFO = "missing_required_info"
    CONTRADICTION_DETECTED = "contradiction_detected"
    INVALID_DATA = "invalid_data"
    
    # Tool Failures
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    TOOL_TIMEOUT = "tool_timeout"
    
    # LLM Failures
    LLM_ERROR = "llm_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    
    # System Failures
    SYSTEM_ERROR = "system_error"
    RATE_LIMIT = "rate_limit"


@dataclass
class FailureContext:
    """Context about a failure for recovery"""
    failure_type: FailureType
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    user_input: Optional[str] = None
    last_successful_state: Optional[str] = None


@dataclass
class RecoveryAction:
    """Action to take for recovery"""
    action_type: str  # "retry", "ask_clarification", "simplify", "fallback", "escalate"
    message_hi: str
    message_en: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_user_input: bool = True


class FailureHandler:
    """
    Handles various failure scenarios with appropriate recovery strategies
    """
    
    def __init__(self):
        self._failure_history: List[FailureContext] = []
        self._recovery_strategies = self._init_strategies()
    
    def _init_strategies(self) -> Dict[FailureType, List[RecoveryAction]]:
        """Initialize recovery strategies for each failure type"""
        return {
            # STT Failures
            FailureType.STT_NO_AUDIO: [
                RecoveryAction(
                    action_type="ask_retry",
                    message_hi="कुछ सुनाई नहीं दिया। कृपया माइक के पास बोलें।",
                    message_en="Couldn't hear anything. Please speak closer to the mic."
                ),
                RecoveryAction(
                    action_type="offer_text",
                    message_hi="आवाज़ नहीं आ रही? आप टाइप भी कर सकते हैं।",
                    message_en="No audio? You can also type your question."
                )
            ],
            
            FailureType.STT_UNCLEAR: [
                RecoveryAction(
                    action_type="ask_repeat",
                    message_hi="समझ नहीं आया। कृपया धीरे और साफ़ बोलें।",
                    message_en="Didn't understand. Please speak slowly and clearly."
                ),
                RecoveryAction(
                    action_type="ask_rephrase",
                    message_hi="कृपया दूसरे शब्दों में बताएं।",
                    message_en="Please say it in different words."
                ),
                RecoveryAction(
                    action_type="offer_text",
                    message_hi="आप चाहें तो लिखकर भी बता सकते हैं।",
                    message_en="You can also type if you prefer."
                )
            ],
            
            FailureType.STT_PARTIAL: [
                RecoveryAction(
                    action_type="confirm_partial",
                    message_hi="मुझे यह सुनाई दिया: '{partial}' - क्या यह सही है?",
                    message_en="I heard: '{partial}' - Is this correct?",
                    parameters={"needs_partial": True}
                )
            ],
            
            # Missing Information
            FailureType.MISSING_REQUIRED_INFO: [
                RecoveryAction(
                    action_type="ask_specific",
                    message_hi="पात्रता जांचने के लिए कृपया {missing_fields} बताएं।",
                    message_en="Please provide {missing_fields} to check eligibility.",
                    parameters={"needs_fields": True}
                ),
                RecoveryAction(
                    action_type="explain_why",
                    message_hi="{field_name} जानना ज़रूरी है क्योंकि {reason}।",
                    message_en="We need {field_name} because {reason}.",
                    parameters={"needs_explanation": True}
                )
            ],
            
            # Contradictions
            FailureType.CONTRADICTION_DETECTED: [
                RecoveryAction(
                    action_type="ask_clarification",
                    message_hi="आपने पहले {field} '{old_value}' बताया था, अब '{new_value}' बता रहे हैं। कौन सा सही है?",
                    message_en="You earlier said {field} was '{old_value}', now saying '{new_value}'. Which is correct?",
                    parameters={"needs_contradiction_details": True}
                )
            ],
            
            # Input Issues
            FailureType.INPUT_EMPTY: [
                RecoveryAction(
                    action_type="prompt",
                    message_hi="कृपया अपना सवाल बताएं। मैं सरकारी योजनाओं में मदद कर सकता हूं।",
                    message_en="Please ask your question. I can help with government schemes."
                )
            ],
            
            FailureType.INPUT_OFF_TOPIC: [
                RecoveryAction(
                    action_type="redirect",
                    message_hi="मैं केवल सरकारी योजनाओं में मदद कर सकता हूं। क्या आप किसी योजना के बारे में जानना चाहते हैं?",
                    message_en="I can only help with government schemes. Would you like to know about any scheme?"
                )
            ],
            
            # Tool Failures
            FailureType.TOOL_EXECUTION_ERROR: [
                RecoveryAction(
                    action_type="retry_tool",
                    message_hi="एक पल रुकें, फिर से कोशिश कर रहा हूं...",
                    message_en="One moment, trying again...",
                    requires_user_input=False
                ),
                RecoveryAction(
                    action_type="use_fallback",
                    message_hi="कुछ तकनीकी समस्या है। मैं दूसरे तरीके से मदद करता हूं।",
                    message_en="Technical issue. Let me help another way."
                )
            ],
            
            # LLM Failures
            FailureType.LLM_ERROR: [
                RecoveryAction(
                    action_type="retry",
                    message_hi="एक पल...",
                    message_en="One moment...",
                    requires_user_input=False
                ),
                RecoveryAction(
                    action_type="use_fallback_response",
                    message_hi="क्षमा करें, अभी जवाब देने में समस्या हो रही है। कृपया थोड़ी देर बाद प्रयास करें या हेल्पलाइन पर कॉल करें।",
                    message_en="Sorry, having trouble responding. Please try again later or call the helpline."
                )
            ],
            
            # System Failures
            FailureType.SYSTEM_ERROR: [
                RecoveryAction(
                    action_type="apologize_retry",
                    message_hi="क्षमा करें, कुछ गड़बड़ हुई। कृपया दोबारा प्रयास करें।",
                    message_en="Sorry, something went wrong. Please try again."
                ),
                RecoveryAction(
                    action_type="provide_alternative",
                    message_hi="आप हेल्पलाइन 1800-111-555 पर भी कॉल कर सकते हैं।",
                    message_en="You can also call helpline 1800-111-555."
                )
            ],
            
            FailureType.RATE_LIMIT: [
                RecoveryAction(
                    action_type="wait",
                    message_hi="बहुत सारे अनुरोध आ रहे हैं। कृपया 30 सेकंड बाद प्रयास करें।",
                    message_en="Too many requests. Please wait 30 seconds."
                )
            ]
        }
    
    def handle_failure(self, failure_type: FailureType, context: Dict[str, Any] = None) -> RecoveryAction:
        """
        Handle a failure and return appropriate recovery action
        
        Args:
            failure_type: Type of failure that occurred
            context: Additional context about the failure
            
        Returns:
            RecoveryAction with message and next steps
        """
        context = context or {}
        
        # Create failure context
        failure_ctx = FailureContext(
            failure_type=failure_type,
            details=context,
            user_input=context.get("user_input")
        )
        
        # Check if this is a repeated failure
        recent_same_failures = [
            f for f in self._failure_history[-5:]
            if f.failure_type == failure_type
        ]
        failure_ctx.recovery_attempts = len(recent_same_failures)
        
        self._failure_history.append(failure_ctx)
        
        # Get recovery strategies
        strategies = self._recovery_strategies.get(failure_type, [])
        if not strategies:
            return self._default_recovery()
        
        # Select strategy based on attempt number
        attempt_idx = min(failure_ctx.recovery_attempts, len(strategies) - 1)
        action = strategies[attempt_idx]
        
        # Format message with context
        action = self._format_action(action, context)
        
        return action
    
    def _format_action(self, action: RecoveryAction, context: Dict[str, Any]) -> RecoveryAction:
        """Format recovery action message with context variables"""
        message_hi = action.message_hi
        message_en = action.message_en
        
        # Replace placeholders
        for key, value in context.items():
            message_hi = message_hi.replace(f"{{{key}}}", str(value))
            message_en = message_en.replace(f"{{{key}}}", str(value))
        
        # Handle missing fields formatting
        if context.get("missing_fields"):
            fields = context["missing_fields"]
            field_names_hi = {
                "age": "उम्र",
                "income": "वार्षिक आय",
                "gender": "लिंग",
                "category": "वर्ग (SC/ST/OBC/General)"
            }
            fields_str = ", ".join(field_names_hi.get(f, f) for f in fields)
            message_hi = message_hi.replace("{missing_fields}", fields_str)
            message_en = message_en.replace("{missing_fields}", ", ".join(fields))
        
        return RecoveryAction(
            action_type=action.action_type,
            message_hi=message_hi,
            message_en=message_en,
            parameters=action.parameters,
            requires_user_input=action.requires_user_input
        )
    
    def _default_recovery(self) -> RecoveryAction:
        """Default recovery when no specific strategy exists"""
        return RecoveryAction(
            action_type="default",
            message_hi="क्षमा करें, कुछ समस्या हुई। कृपया दोबारा प्रयास करें।",
            message_en="Sorry, something went wrong. Please try again."
        )
    
    def get_stt_error_response(self, error_type: str, partial_text: str = None) -> str:
        """Get appropriate response for STT errors in Hindi"""
        
        if error_type == "no_audio":
            action = self.handle_failure(FailureType.STT_NO_AUDIO)
        elif error_type == "unclear" or error_type == "recognition":
            action = self.handle_failure(FailureType.STT_UNCLEAR)
        elif error_type == "partial" and partial_text:
            action = self.handle_failure(
                FailureType.STT_PARTIAL, 
                {"partial": partial_text}
            )
        else:
            action = self.handle_failure(FailureType.STT_UNCLEAR)
        
        return action.message_hi
    
    def get_missing_info_response(self, missing_fields: List[str], for_scheme: str = None) -> str:
        """Get response asking for missing information"""
        
        context = {"missing_fields": missing_fields}
        if for_scheme:
            context["scheme"] = for_scheme
        
        action = self.handle_failure(FailureType.MISSING_REQUIRED_INFO, context)
        return action.message_hi
    
    def get_contradiction_response(self, field: str, old_value: Any, new_value: Any) -> str:
        """Get response for handling contradiction"""
        
        field_names_hi = {
            "age": "उम्र",
            "income": "आय",
            "gender": "लिंग",
            "category": "श्रेणी"
        }
        
        context = {
            "field": field_names_hi.get(field, field),
            "old_value": old_value,
            "new_value": new_value
        }
        
        action = self.handle_failure(FailureType.CONTRADICTION_DETECTED, context)
        return action.message_hi
    
    def should_escalate(self) -> bool:
        """Check if we should escalate (too many failures)"""
        recent_failures = [
            f for f in self._failure_history
            if time.time() - f.timestamp < 300  # Last 5 minutes
        ]
        return len(recent_failures) >= 5
    
    def get_escalation_message(self) -> str:
        """Get message when escalating due to repeated failures"""
        return """लगता है कि आपको समस्या हो रही है। 

आप इन विकल्पों का उपयोग कर सकते हैं:
• हेल्पलाइन: 1800-111-555 (टोल-फ्री)
• नज़दीकी CSC केंद्र पर जाएं
• ग्राम पंचायत कार्यालय से संपर्क करें

क्या मैं किसी और तरह से मदद कर सकता हूं?"""
    
    def clear_history(self):
        """Clear failure history (e.g., on session reset)"""
        self._failure_history = []


# Global failure handler instance
_failure_handler = FailureHandler()


def get_failure_handler() -> FailureHandler:
    """Get the global failure handler instance"""
    return _failure_handler
