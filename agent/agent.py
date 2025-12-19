"""
SahAI Agent - LLM-Powered Hindi Government Scheme Assistant
Everything is processed by Gemini - simple wrapper around LLM
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re


@dataclass
class AgentResponse:
    """Response from the agent"""
    text: str
    schemes_mentioned: List[str] = None
    
    def __post_init__(self):
        if self.schemes_mentioned is None:
            self.schemes_mentioned = []


class Agent:
    """
    Simple Agent - Gemini handles everything
    Just maintains context and lets LLM do all the work
    """
    
    def __init__(self, memory, ai_service, scheme_db):
        self.memory = memory
        self.ai_service = ai_service
        self.scheme_db = scheme_db
    
    def process(self, user_input: str) -> str:
        """
        Process user input through Gemini LLM
        
        Args:
            user_input: User's Hindi text input
            
        Returns:
            Hindi response text from Gemini
        """
        # Add to conversation history
        self.memory.add_turn("user", user_input)
        
        # Get all schemes as context for the LLM
        schemes_context = self._get_schemes_context()
        
        # Get conversation history
        history = self.memory.get_history_text()
        
        # Let Gemini handle everything
        response = self.ai_service.process_query(
            user_input=user_input,
            schemes_context=schemes_context,
            conversation_history=history,
            user_data=self.memory.user_data
        )
        
        # Extract any user data mentioned (for context tracking)
        self._extract_user_data(user_input)
        
        # Add response to history
        self.memory.add_turn("assistant", response)
        
        return response
    
    def _get_schemes_context(self) -> str:
        """Get all schemes formatted for LLM context"""
        schemes_text = []
        
        for scheme in self.scheme_db.schemes:
            eligibility = scheme.eligibility
            scheme_info = f"""
योजना: {scheme.get_name('hi')} ({scheme.get_name('en')})
श्रेणी: {scheme.category}
विवरण: {scheme.get_description('hi')}
लाभ: {scheme.get_benefit('hi')}
पात्रता:
  - न्यूनतम उम्र: {eligibility.get('min_age', 'कोई सीमा नहीं')} वर्ष
  - अधिकतम उम्र: {eligibility.get('max_age', 'कोई सीमा नहीं')} वर्ष
  - अधिकतम वार्षिक आय: ₹{eligibility.get('max_income', 'कोई सीमा नहीं')}
  - लिंग: {eligibility.get('gender', 'सभी')}
  - श्रेणी: {', '.join(eligibility.get('category', ['सभी']))}
  - BPL आवश्यक: {eligibility.get('bpl_required', 'नहीं')}
दस्तावेज़: {', '.join(scheme.documents)}
हेल्पलाइन: {scheme.helpline}
आवेदन लिंक: {scheme.application_url}
---"""
            schemes_text.append(scheme_info)
        
        return "\n".join(schemes_text)
    
    def _extract_user_data(self, user_input: str):
        """Extract user information from conversation for context tracking"""
        text = user_input.lower()
        
        # Age patterns
        age_patterns = [
            r'(\d+)\s*(?:साल|वर्ष|years?|yrs?)',
            r'उम्र\s*(?:है)?\s*(\d+)',
            r'मेरी\s*उम्र\s*(\d+)',
        ]
        for pattern in age_patterns:
            match = re.search(pattern, text)
            if match:
                age = int(match.group(1))
                if 1 <= age <= 120:
                    self.memory.update_user_data("age", age)
                break
        
        # Income patterns
        income_patterns = [
            r'(\d+)\s*(?:लाख|lakh)',
            r'आय\s*(?:है)?\s*(\d+)',
            r'(\d+)\s*(?:हज़ार|हजार|thousand)',
        ]
        for pattern in income_patterns:
            match = re.search(pattern, text)
            if match:
                income = int(match.group(1))
                if 'लाख' in text or 'lakh' in text.lower():
                    income *= 100000
                elif 'हज़ार' in text or 'हजार' in text or 'thousand' in text.lower():
                    income *= 1000
                self.memory.update_user_data("income", income)
                break
        
        # Gender
        if any(word in text for word in ['महिला', 'female', 'woman', 'औरत', 'लड़की']):
            self.memory.update_user_data("gender", "female")
        elif any(word in text for word in ['पुरुष', 'male', 'man', 'आदमी', 'लड़का']):
            self.memory.update_user_data("gender", "male")
        
        # Category
        if any(word in text for word in ['एससी', 'sc', 'अनुसूचित जाति']):
            self.memory.update_user_data("category", "SC")
        elif any(word in text for word in ['एसटी', 'st', 'अनुसूचित जनजाति']):
            self.memory.update_user_data("category", "ST")
        elif any(word in text for word in ['ओबीसी', 'obc', 'अन्य पिछड़ा वर्ग']):
            self.memory.update_user_data("category", "OBC")
        elif any(word in text for word in ['सामान्य', 'general', 'जनरल']):
            self.memory.update_user_data("category", "General")
        
        # BPL
        if any(word in text for word in ['बीपीएल', 'bpl', 'गरीबी रेखा']):
            self.memory.update_user_data("bpl", True)
    
    def get_greeting(self) -> str:
        """Get initial greeting from LLM"""
        return self.ai_service.get_greeting()
