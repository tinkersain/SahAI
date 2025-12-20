"""
SahAI Agentic Agent - Planner-Executor-Evaluator Implementation
True agentic workflow with tool usage, memory, and failure handling
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import re

from agent.state_machine import (
    AgentState, IntentType, ExecutionPlan, ExecutionResult,
    EvaluationResult, StateContext, get_state_machine
)
from agent.tools import ToolRegistry, ToolResult, ToolStatus
from agent.failure_handler import FailureHandler, FailureType, get_failure_handler


@dataclass
class AgentResponse:
    """Response from the agent"""
    text: str
    schemes_mentioned: List[str] = None
    tools_used: List[str] = None
    state_transitions: List[str] = None
    user_data_updated: Dict[str, Any] = None
    needs_clarification: bool = False
    clarification_field: Optional[str] = None
    
    def __post_init__(self):
        if self.schemes_mentioned is None:
            self.schemes_mentioned = []
        if self.tools_used is None:
            self.tools_used = []
        if self.state_transitions is None:
            self.state_transitions = []


class AgenticAgent:
    """
    Agentic Agent implementing Planner-Executor-Evaluator loop
    
    Architecture:
    1. PLANNER: Analyzes intent, selects tools, creates execution plan
    2. EXECUTOR: Executes tools, gathers information
    3. EVALUATOR: Checks completeness, detects contradictions, decides next action
    """
    
    def __init__(self, memory, ai_service, scheme_db):
        self.memory = memory
        self.ai_service = ai_service
        self.scheme_db = scheme_db
        self.tools = ToolRegistry(scheme_db)
        self.failure_handler = get_failure_handler()
        self.state_machine = get_state_machine()
        
        # Current processing context
        self._context: Optional[StateContext] = None
    
    def process(self, user_input: str, input_confidence: float = 1.0) -> str:
        """
        Main entry point - Process user input through the agentic loop
        
        Args:
            user_input: User's Hindi text input
            input_confidence: Confidence score from STT (1.0 if from text)
            
        Returns:
            Hindi response text
        """
        # Initialize state context
        self._context = StateContext(
            session_id=self.memory.session_id,
            current_state=AgentState.RECEIVING_INPUT,
            current_input=user_input,
            input_confidence=input_confidence
        )
        
        try:
            # Check for pending contradictions first
            if self.memory.has_pending_contradictions():
                response = self._handle_contradiction_resolution(user_input)
                if response:
                    return response
            
            # ===== PHASE 1: PLANNER =====
            self._context.transition_to(AgentState.PLANNING, "Starting planning phase")
            plan = self._plan(user_input)
            self._context.current_plan = plan
            
            # ===== PHASE 2: EXECUTOR =====
            self._context.transition_to(AgentState.EXECUTING, "Starting execution phase")
            execution_results = self._execute(plan)
            self._context.execution_results = execution_results
            
            # ===== PHASE 3: EVALUATOR =====
            self._context.transition_to(AgentState.EVALUATING, "Starting evaluation phase")
            evaluation = self._evaluate(plan, execution_results)
            self._context.evaluation = evaluation
            
            # Handle evaluation outcomes
            if evaluation.contradiction_detected:
                self._context.transition_to(AgentState.HANDLING_CONTRADICTION)
                return self._generate_contradiction_response(evaluation)
            
            if evaluation.needs_clarification:
                self._context.transition_to(AgentState.CLARIFICATION_NEEDED)
                return self._generate_clarification_request(plan, evaluation)
            
            # ===== PHASE 4: RESPONSE GENERATION =====
            self._context.transition_to(AgentState.GENERATING_RESPONSE)
            response = self._generate_response(plan, execution_results, evaluation)
            
            # Record in memory
            self.memory.add_turn(
                "user", user_input,
                extracted_data=plan.available_info,
                intent=plan.intent.value,
                tools_used=self._context.tools_called
            )
            self.memory.add_turn(
                "assistant", response,
                tools_used=self._context.tools_called
            )
            
            self._context.transition_to(AgentState.COMPLETE)
            return response
            
        except Exception as e:
            self._context.transition_to(AgentState.ERROR_RECOVERY, str(e))
            return self._handle_error(e)
    
    # ==================== PLANNER PHASE ====================
    
    def _plan(self, user_input: str) -> ExecutionPlan:
        """
        PLANNER: Analyze input, determine intent, select tools, create plan
        """
        self._context.transition_to(AgentState.ANALYZING_INTENT)
        
        # Step 1: Extract user data from input
        extractor_result = self.tools.execute(
            "user_data_extractor",
            {"text": user_input}
        )
        extracted_data = extractor_result.data if extractor_result.status == ToolStatus.SUCCESS else {}
        
        # Update memory with extracted data
        for key, value in extracted_data.items():
            success, contradiction = self.memory.set(key, value)
            if contradiction and not contradiction.resolved:
                # Mark for handling
                pass
        
        # Step 2: Determine intent using LLM
        intent = self._analyze_intent(user_input, extracted_data)
        
        # Step 3: Select tools based on intent
        self._context.transition_to(AgentState.SELECTING_TOOLS)
        required_tools, required_info = self._select_tools_for_intent(intent, user_input)
        
        # Step 4: Create execution plan
        available_info = {**self.memory.user_data, **extracted_data}
        
        plan = ExecutionPlan(
            intent=intent,
            required_tools=required_tools,
            required_info=required_info,
            available_info=available_info,
            missing_info=[],  # Will be calculated by __post_init__
            steps=self._create_execution_steps(intent, required_tools),
            confidence=self._context.input_confidence
        )
        
        return plan
    
    def _analyze_intent(self, user_input: str, extracted_data: Dict) -> IntentType:
        """Analyze user intent from input"""
        text = user_input.lower()
        
        # Greeting patterns
        greeting_words = ['नमस्ते', 'hello', 'hi', 'हेलो', 'नमस्कार', 'प्रणाम']
        if any(word in text for word in greeting_words) and len(text.split()) < 5:
            return IntentType.GREETING
        
        # Farewell patterns
        farewell_words = ['धन्यवाद', 'thank', 'bye', 'अलविदा', 'शुक्रिया']
        if any(word in text for word in farewell_words):
            return IntentType.FAREWELL
        
        # Eligibility check patterns
        eligibility_words = ['पात्र', 'eligible', 'मिल सकत', 'योग्य', 'क्या मुझे', 'क्या मैं']
        if any(word in text for word in eligibility_words):
            return IntentType.ELIGIBILITY_CHECK
        
        # Scheme inquiry patterns
        scheme_words = ['योजना', 'scheme', 'स्कीम', 'कौन सी', 'बताओ', 'जानकारी', 'क्या है']
        if any(word in text for word in scheme_words):
            return IntentType.SCHEME_INQUIRY
        
        # Application help patterns  
        application_words = ['आवेदन', 'apply', 'कैसे करें', 'कहां करें', 'रजिस्टर']
        if any(word in text for word in application_words):
            return IntentType.APPLICATION_HELP
        
        # Document info patterns
        document_words = ['दस्तावेज़', 'document', 'कागज़', 'प्रमाण पत्र']
        if any(word in text for word in document_words):
            return IntentType.DOCUMENT_INFO
        
        # User providing info patterns
        if extracted_data:
            return IntentType.PROVIDE_INFO
        
        # Correction patterns
        correction_words = ['गलत', 'सही', 'correction', 'नहीं', 'दरअसल', 'असल में']
        if any(word in text for word in correction_words):
            return IntentType.CORRECTION
        
        # Default to general question
        return IntentType.GENERAL_QUESTION
    
    def _select_tools_for_intent(self, intent: IntentType, user_input: str) -> tuple[List[str], List[str]]:
        """Select appropriate tools based on intent"""
        
        tool_map = {
            IntentType.GREETING: ([], []),
            IntentType.FAREWELL: ([], []),
            
            IntentType.ELIGIBILITY_CHECK: (
                ["eligibility_engine", "scheme_retrieval"],
                ["age", "income"]  # Required for accurate check
            ),
            
            IntentType.SCHEME_INQUIRY: (
                ["scheme_retrieval"],
                []
            ),
            
            IntentType.APPLICATION_HELP: (
                ["scheme_retrieval", "document_checker"],
                []
            ),
            
            IntentType.DOCUMENT_INFO: (
                ["document_checker", "scheme_retrieval"],
                []
            ),
            
            IntentType.PROVIDE_INFO: (
                ["eligibility_engine"],  # Re-check eligibility with new info
                []
            ),
            
            IntentType.GENERAL_QUESTION: (
                ["scheme_retrieval"],
                []
            ),
            
            IntentType.CORRECTION: (
                [],
                []
            ),
            
            IntentType.CLARIFICATION: (
                [],
                []
            )
        }
        
        return tool_map.get(intent, (["scheme_retrieval"], []))
    
    def _create_execution_steps(self, intent: IntentType, tools: List[str]) -> List[Dict]:
        """Create ordered execution steps"""
        steps = []
        
        for i, tool_name in enumerate(tools):
            steps.append({
                "step": i + 1,
                "tool": tool_name,
                "purpose": self._get_tool_purpose(tool_name, intent),
                "depends_on": list(range(i)) if i > 0 else []
            })
        
        return steps
    
    def _get_tool_purpose(self, tool_name: str, intent: IntentType) -> str:
        """Get purpose description for a tool in context"""
        purposes = {
            "eligibility_engine": "Check user eligibility for schemes",
            "scheme_retrieval": "Get scheme information",
            "document_checker": "List required documents",
            "application_status": "Check application status",
            "user_data_extractor": "Extract user information"
        }
        return purposes.get(tool_name, "Process request")
    
    # ==================== EXECUTOR PHASE ====================
    
    def _execute(self, plan: ExecutionPlan) -> List[ExecutionResult]:
        """
        EXECUTOR: Execute the plan's tools and gather results
        """
        results = []
        
        for step in plan.steps:
            tool_name = step["tool"]
            
            self._context.transition_to(AgentState.CALLING_TOOL, f"Calling {tool_name}")
            
            # Prepare inputs for the tool
            inputs = self._prepare_tool_inputs(tool_name, plan)
            
            # Execute tool
            tool_result = self.tools.execute(tool_name, inputs, self.memory.get_context())
            
            # Track tool usage
            self._context.tools_called.append(tool_name)
            
            # Convert to ExecutionResult
            exec_result = ExecutionResult(
                tool_name=tool_name,
                success=tool_result.status in [ToolStatus.SUCCESS, ToolStatus.PARTIAL],
                data=tool_result.data,
                error=tool_result.message if tool_result.status == ToolStatus.ERROR else None,
                needs_more_info=tool_result.missing_fields
            )
            results.append(exec_result)
            
            # Check if we need to stop (e.g., missing required info)
            if tool_result.status == ToolStatus.NEEDS_INFO:
                self._context.transition_to(AgentState.WAITING_FOR_INFO)
                break
        
        return results
    
    def _prepare_tool_inputs(self, tool_name: str, plan: ExecutionPlan) -> Dict[str, Any]:
        """Prepare inputs for a specific tool"""
        
        base_inputs = plan.available_info.copy()
        
        if tool_name == "scheme_retrieval":
            # Add query from user input
            base_inputs["query"] = self._context.current_input
            
            # Check if user mentioned specific scheme
            scheme_id = self._extract_scheme_reference(self._context.current_input)
            if scheme_id:
                base_inputs["scheme_id"] = scheme_id
        
        elif tool_name == "document_checker":
            # Need scheme ID
            if self.memory.current_scheme:
                base_inputs["scheme_id"] = self.memory.current_scheme
        
        elif tool_name == "eligibility_engine":
            # Use all available user data
            pass
        
        return base_inputs
    
    def _extract_scheme_reference(self, text: str) -> Optional[str]:
        """Extract scheme ID if user mentions specific scheme"""
        text_lower = text.lower()
        
        scheme_keywords = {
            "pm-kisan": ["किसान", "kisan", "pm kisan", "पीएम किसान"],
            "pm-awas-gramin": ["आवास", "awas", "घर", "मकान", "ग्रामीण"],
            "pm-awas-urban": ["शहरी आवास", "urban", "शहर"],
            "old-age-pension": ["वृद्धावस्था", "बुढ़ापा", "old age", "बुजुर्ग"],
            "widow-pension": ["विधवा", "widow"],
            "disability-pension": ["विकलांग", "दिव्यांग", "disability"],
            "ayushman-bharat": ["आयुष्मान", "ayushman", "स्वास्थ्य बीमा"],
        }
        
        for scheme_id, keywords in scheme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                self.memory.current_scheme = scheme_id
                return scheme_id
        
        return None
    
    # ==================== EVALUATOR PHASE ====================
    
    def _evaluate(self, plan: ExecutionPlan, results: List[ExecutionResult]) -> EvaluationResult:
        """
        EVALUATOR: Check completeness and quality of execution
        """
        self._context.transition_to(AgentState.CHECKING_COMPLETENESS)
        
        # Check tool execution success
        failed_tools = [r for r in results if not r.success]
        successful_tools = [r for r in results if r.success]
        
        # Collect all missing information
        all_missing = []
        for r in results:
            all_missing.extend(r.needs_more_info)
        all_missing.extend(plan.missing_info)
        all_missing = list(set(all_missing))  # Deduplicate
        
        # Filter out info that is already available!
        available = plan.available_info
        actually_missing = []
        for field in all_missing:
            if field == "age" and available.get("age"):
                continue  # Already have age
            if field == "income" and available.get("income"):
                continue  # Already have income
            if field == "gender" and available.get("gender"):
                continue
            if field == "category" and available.get("category"):
                continue
            actually_missing.append(field)
        all_missing = actually_missing
        
        # Check for contradictions
        has_contradiction = self.memory.has_pending_contradictions()
        contradiction_details = None
        if has_contradiction:
            pending = self.memory.get_pending_contradictions()
            if pending:
                c = pending[0]
                contradiction_details = {
                    "field": c.field,
                    "old_value": c.old_value,
                    "new_value": c.new_value
                }
        
        # Determine completeness
        is_complete = (
            len(failed_tools) == 0 and
            len(all_missing) == 0 and
            not has_contradiction
        )
        
        # Calculate quality score
        if not results:
            quality_score = 0.5  # No tools executed
        else:
            success_rate = len(successful_tools) / len(results)
            info_completeness = 1.0 - (len(all_missing) / max(len(plan.required_info), 1))
            quality_score = (success_rate * 0.6) + (info_completeness * 0.4)
        
        # Determine if clarification needed
        needs_clarification = (
            len(all_missing) > 0 and
            plan.intent in [IntentType.ELIGIBILITY_CHECK, IntentType.APPLICATION_HELP]
        )
        
        # Build issues and suggestions
        issues = []
        suggestions = []
        
        for r in failed_tools:
            issues.append(f"Tool {r.tool_name} failed: {r.error}")
        
        if all_missing:
            issues.append(f"Missing information: {', '.join(all_missing)}")
            suggestions.append("Ask user for missing information")
        
        if has_contradiction:
            issues.append("Contradiction detected in user data")
            suggestions.append("Ask user to clarify")
        
        # Determine next action
        if has_contradiction:
            next_action = "ask_clarification"
        elif needs_clarification:
            next_action = "ask_user"
        elif failed_tools and self._context.can_retry():
            next_action = "re-execute"
        else:
            next_action = "respond"
        
        return EvaluationResult(
            is_complete=is_complete,
            quality_score=quality_score,
            issues=issues,
            suggestions=suggestions,
            needs_clarification=needs_clarification,
            contradiction_detected=has_contradiction,
            contradiction_details=contradiction_details,
            next_action=next_action
        )
    
    # ==================== RESPONSE GENERATION ====================
    
    def _generate_response(self, plan: ExecutionPlan, results: List[ExecutionResult], 
                          evaluation: EvaluationResult) -> str:
        """Generate final response based on plan execution"""
        
        # Simple responses for greetings/farewells
        if plan.intent == IntentType.GREETING:
            return self._get_greeting_response()
        
        if plan.intent == IntentType.FAREWELL:
            return self._get_farewell_response()
        
        # If we need more info but can still give partial response
        if evaluation.needs_clarification and results:
            return self._generate_partial_response_with_question(plan, results, evaluation)
        
        # Use LLM to generate contextual response
        return self._generate_llm_response(plan, results, evaluation)
    
    def _generate_llm_response(self, plan: ExecutionPlan, results: List[ExecutionResult],
                              evaluation: EvaluationResult) -> str:
        """Use LLM to generate natural response"""
        
        # Build context for LLM
        tool_outputs = []
        for r in results:
            if r.success and r.data:
                tool_outputs.append({
                    "tool": r.tool_name,
                    "result": r.data
                })
        
        # Get scheme context
        schemes_context = self._get_schemes_context()
        
        # Conversation history
        history = self.memory.get_history_text()
        
        # Build info already collected message
        collected_info = plan.available_info
        collected_fields = []
        if collected_info.get('age'):
            collected_fields.append(f"उम्र: {collected_info['age']} वर्ष")
        if collected_info.get('income'):
            collected_fields.append(f"आय: ₹{collected_info['income']}")
        if collected_info.get('gender'):
            collected_fields.append(f"लिंग: {collected_info['gender']}")
        if collected_info.get('category'):
            collected_fields.append(f"श्रेणी: {collected_info['category']}")
        if collected_info.get('bpl'):
            collected_fields.append("BPL: हां")
        
        collected_info_text = ", ".join(collected_fields) if collected_fields else "कोई जानकारी नहीं"
        
        # Determine what is still missing for eligibility check
        missing_fields = []
        if plan.intent == IntentType.ELIGIBILITY_CHECK:
            if not collected_info.get('age'):
                missing_fields.append("उम्र")
            if not collected_info.get('income'):
                missing_fields.append("वार्षिक आय")
        
        missing_info_text = ", ".join(missing_fields) if missing_fields else "कुछ नहीं"
        
        # Create prompt - optimized for SHORT voice-friendly responses
        prompt = f"""संदर्भ:
इरादा: {plan.intent.value}

✅ उपयोगकर्ता ने पहले से यह जानकारी दी है: {collected_info_text}
❌ अभी भी चाहिए: {missing_info_text}

⚠️ बहुत महत्वपूर्ण:
- जो जानकारी पहले से है (✅) उसे दोबारा मत पूछें!
- सिर्फ ❌ में दी गई चीज़ें ही पूछें (अगर जरूरी हो)
- अगर उम्र और आय दोनों मिल गई है, तो पात्रता बताएं, न कि फिर से पूछें

टूल परिणाम:
{json.dumps(tool_outputs, ensure_ascii=False)}

उपयोगकर्ता का संदेश: "{self._context.current_input}"

⚠️ Voice Output के लिए:
- आप एक महिला सहायिका हैं, महिला की भाषा शैली में बोलें
- जवाब बहुत छोटा रखें (अधिकतम 2-3 वाक्य)
- सिर्फ सबसे जरूरी जानकारी दें
- लंबी सूची न दें
- फेमिनिन वर्ब्स इस्तेमाल करें (जैसे: "मैं बताती हूं", "मैंने देखा", "मैं आपकी मदद करूंगी")

हिंदी में छोटा जवाब:"""

        response = self.ai_service.generate_response(prompt)
        return response
    
    def _generate_partial_response_with_question(self, plan: ExecutionPlan, 
                                                  results: List[ExecutionResult],
                                                  evaluation: EvaluationResult) -> str:
        """Generate response that includes what we found + asks for missing info"""
        
        response_parts = []
        
        # Include any useful results
        for r in results:
            if r.success and r.data:
                if r.tool_name == "eligibility_engine":
                    eligible = r.data.get("eligible", [])
                    if eligible:
                        response_parts.append(f"आप {len(eligible)} योजनाओं के लिए पात्र हो सकते हैं।")
                elif r.tool_name == "scheme_retrieval":
                    schemes = r.data.get("schemes", [])
                    if schemes:
                        response_parts.append(f"{len(schemes)} योजनाएं मिलीं।")
        
        # Filter out info that's already collected - don't ask again!
        available = plan.available_info
        all_missing = list(set(plan.missing_info + sum([r.needs_more_info for r in results], [])))
        
        # Only include truly missing fields
        actually_missing = []
        for field in all_missing:
            if field == "age" and available.get("age"):
                continue  # Already have age
            if field == "income" and available.get("income"):
                continue  # Already have income
            actually_missing.append(field)
        
        if actually_missing:
            question = self.failure_handler.get_missing_info_response(actually_missing)
            response_parts.append(question)
        
        # Default response only if we truly have nothing
        if not response_parts:
            if not available.get("age") and not available.get("income"):
                return "कृपया अपनी उम्र और वार्षिक आय बताएं।"
            elif not available.get("age"):
                return "कृपया अपनी उम्र बताएं।"
            elif not available.get("income"):
                return "कृपया अपनी वार्षिक आय बताएं।"
            else:
                return "मैं आपकी पात्रता जांच रही हूं।"
        
        return " ".join(response_parts)
    
    def _generate_contradiction_response(self, evaluation: EvaluationResult) -> str:
        """Generate response for handling contradiction"""
        details = evaluation.contradiction_details
        if details:
            return self.failure_handler.get_contradiction_response(
                details["field"],
                details["old_value"],
                details["new_value"]
            )
        return self.memory.get_contradiction_message_hi() or "कृपया अपनी जानकारी स्पष्ट करें।"
    
    def _generate_clarification_request(self, plan: ExecutionPlan, 
                                        evaluation: EvaluationResult) -> str:
        """Generate request for clarification/missing info"""
        # Filter out already collected info
        available = plan.available_info
        actually_missing = []
        for field in plan.missing_info:
            if field == "age" and available.get("age"):
                continue
            if field == "income" and available.get("income"):
                continue
            actually_missing.append(field)
        
        if not actually_missing:
            return "मैं आपकी पात्रता जांच रही हूं।"
        
        return self.failure_handler.get_missing_info_response(actually_missing)
    
    def _handle_contradiction_resolution(self, user_input: str) -> Optional[str]:
        """Handle user's response to a contradiction"""
        pending = self.memory.get_pending_contradictions()
        if not pending:
            return None
        
        contradiction = pending[0]
        text = user_input.lower()
        
        # Check if user confirmed old value
        old_str = str(contradiction.old_value).lower()
        new_str = str(contradiction.new_value).lower()
        
        # Simple heuristics - can be improved
        if old_str in text or "पहले वाली" in text or "पुरानी" in text:
            self.memory.resolve_contradiction(contradiction.field, use_new_value=False, 
                                             user_explanation=user_input)
            return f"ठीक है, मैंने {contradiction.field} = {contradiction.old_value} रखा है।"
        
        elif new_str in text or "नई" in text or "अभी" in text or "सही" in text:
            self.memory.resolve_contradiction(contradiction.field, use_new_value=True,
                                             user_explanation=user_input)
            return f"ठीक है, मैंने {contradiction.field} = {contradiction.new_value} अपडेट किया है।"
        
        # If unclear, ask again
        return None
    
    def _handle_error(self, error: Exception) -> str:
        """Handle errors gracefully"""
        print(f"Agent error: {error}")
        self._context.error_count += 1
        self._context.last_error = str(error)
        
        if self.failure_handler.should_escalate():
            return self.failure_handler.get_escalation_message()
        
        return self.failure_handler.handle_failure(
            FailureType.SYSTEM_ERROR,
            {"error": str(error)}
        ).message_hi
    
    def _get_greeting_response(self) -> str:
        """Get greeting response"""
        user_data = self.memory.user_data
        if user_data:
            return """नमस्ते! 🙏 आपकी जानकारी मेरे पास है। 

क्या आप पात्रता जांचना चाहते हैं या किसी योजना के बारे में पूछना चाहते हैं?"""
        
        return """नमस्ते! 🙏 मैं सहाई हूं - आपकी सरकारी योजना सहायिका।

मैं आपकी मदद कर सकती हूं:
• योजनाओं की जानकारी देने में
• पात्रता जांचने में  
• आवेदन प्रक्रिया समझाने में

बताइए, आपको किस बारे में जानना है?"""
    
    def _get_farewell_response(self) -> str:
        """Get farewell response"""
        return """धन्यवाद! 🙏 

याद रखें:
• हेल्पलाइन: 1800-111-555 (टोल-फ्री)
• वेबसाइट: india.gov.in

फिर मिलेंगे! शुभकामनाएं!"""
    
    def _get_schemes_context(self) -> str:
        """Get schemes formatted for LLM context"""
        schemes_text = []
        
        for scheme in self.scheme_db.schemes[:10]:  # Limit for context
            eligibility = scheme.eligibility
            scheme_info = f"""
योजना: {scheme.get_name('hi')} ({scheme.id})
श्रेणी: {scheme.category}
लाभ: {scheme.get_benefit('hi')}
पात्रता: उम्र {eligibility.get('age_min', '-')}-{eligibility.get('age_max', '-')}, आय ≤₹{eligibility.get('income_max', '-')}
हेल्पलाइन: {scheme.helpline}"""
            schemes_text.append(scheme_info)
        
        return "\n".join(schemes_text)
    
    def get_greeting(self) -> str:
        """Get initial greeting"""
        return self._get_greeting_response()


# Backward compatibility alias
Agent = AgenticAgent
