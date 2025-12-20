"""
SahAI AI Service - LLM Integration for Hindi Conversations
Gemini handles ALL processing - understanding, eligibility, responses
Supports the agentic workflow with tool orchestration
"""
import json
from typing import Dict, Any, Optional, List

try:
    from config.settings import settings
except ImportError:
    class MockSettings:
        class AI:
            gemini_api_key = ""
            gemini_model = "gemini-2.0-flash"
        ai = AI()
    settings = MockSettings()


class AIService:
    """
    AI Service - Gemini handles everything
    All scheme logic, eligibility checks, and responses are done by LLM
    Supports agentic workflow with planning and response generation
    """
    
    def __init__(self):
        self.client = None
        self.model_name = None
        self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini model"""
        api_key = getattr(settings.ai, 'gemini_api_key', '') or ""
        
        if not api_key:
            print("⚠️ Gemini API key not set - AI features limited")
            return
        
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model_name = getattr(settings.ai, 'gemini_model', 'gemini-2.0-flash')
            print(f"✅ Gemini initialized: {self.model_name}")
        except ImportError:
            print("⚠️ google-genai not installed")
        except Exception as e:
            print(f"⚠️ Gemini init failed: {e}")
    
    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate a response from the LLM
        
        Args:
            prompt: The complete prompt with all context
            temperature: Creativity level (0-1)
            
        Returns:
            Generated response text
        """
        if not self.client:
            return self._fallback_response("")
        
        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=2000
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"LLM generation error: {e}")
            return self._fallback_response("")
    
    def analyze_intent(self, user_input: str, conversation_history: str = "") -> Dict[str, Any]:
        """
        Analyze user intent using LLM
        
        Returns:
            Dict with intent, confidence, entities
        """
        if not self.client:
            return {"intent": "unknown", "confidence": 0.5, "entities": {}}
        
        prompt = f"""आप एक intent classifier हैं। उपयोगकर्ता के संदेश का विश्लेषण करें।

संदेश: "{user_input}"

पिछली बातचीत:
{conversation_history}

JSON में जवाब दें:
{{
    "intent": "greeting|farewell|eligibility_check|scheme_inquiry|application_help|document_info|provide_info|correction|general",
    "confidence": 0.0-1.0,
    "entities": {{
        "scheme_mentioned": "scheme_id or null",
        "age_mentioned": number or null,
        "income_mentioned": number or null,
        "category_mentioned": "SC|ST|OBC|General or null"
    }},
    "requires_tools": ["tool1", "tool2"]
}}

केवल JSON दें, कुछ और नहीं:"""

        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=500
                )
            )
            
            # Parse JSON response
            text = response.text.strip()
            # Clean up markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
            
        except Exception as e:
            print(f"Intent analysis error: {e}")
            return {"intent": "general", "confidence": 0.5, "entities": {}}
    
    def generate_tool_selection(self, intent: str, user_input: str, 
                                available_tools: List[str]) -> List[str]:
        """
        Use LLM to select appropriate tools for a task
        
        Returns:
            List of tool names to execute
        """
        if not self.client:
            # Fallback logic
            if "पात्र" in user_input or "eligible" in user_input.lower():
                return ["eligibility_engine", "scheme_retrieval"]
            return ["scheme_retrieval"]
        
        prompt = f"""आप एक tool selector हैं। उपयोगकर्ता के intent के आधार पर सही tools चुनें।

Intent: {intent}
User query: "{user_input}"

Available tools:
{json.dumps(available_tools)}

Tool descriptions:
- eligibility_engine: Check if user is eligible for schemes based on their data
- scheme_retrieval: Get information about schemes
- document_checker: List required documents for a scheme
- application_status: Check status of an application
- user_data_extractor: Extract user info from text

Return JSON array of tool names to use (in order):"""

        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200
                )
            )
            
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            tools = json.loads(text)
            return [t for t in tools if t in available_tools]
            
        except Exception as e:
            print(f"Tool selection error: {e}")
            return ["scheme_retrieval"]
    
    def process_query(
        self,
        user_input: str,
        schemes_context: str,
        conversation_history: str,
        user_data: Dict[str, Any]
    ) -> str:
        """
        Main method - Gemini processes everything (backward compatible)
        
        Args:
            user_input: User's current query in Hindi
            schemes_context: All scheme information as context
            conversation_history: Previous conversation turns
            user_data: Extracted user information (age, income, etc.)
            
        Returns:
            Complete Hindi response from Gemini
        """
        if not self.client:
            return self._fallback_response(user_input)
        
        try:
            system_prompt = self._build_system_prompt(schemes_context)
            user_context = self._build_user_context(user_data, conversation_history)
            
            full_prompt = f"""{system_prompt}

{user_context}

उपयोगकर्ता का वर्तमान संदेश: "{user_input}"

कृपया उपयुक्त हिंदी में जवाब दें:"""

            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"AI process error: {e}")
            return self._fallback_response(user_input)
    
    def evaluate_response_quality(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate quality of a generated response
        
        Returns:
            Dict with quality_score, issues, suggestions
        """
        if not self.client:
            return {"quality_score": 0.5, "issues": [], "suggestions": []}
        
        prompt = f"""Evaluate this Hindi response for quality:

Response: "{response}"

Context: {json.dumps(context, ensure_ascii=False)}

Rate on:
1. Relevance (0-1): Does it answer the query?
2. Completeness (0-1): Is the information complete?
3. Clarity (0-1): Is it clear and easy to understand?
4. Helpfulness (0-1): Does it help the user?

Return JSON:
{{
    "quality_score": 0.0-1.0,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1"]
}}"""

        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=300
                )
            )
            
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
            
        except Exception as e:
            print(f"Quality evaluation error: {e}")
            return {"quality_score": 0.7, "issues": [], "suggestions": []}
    
    def _build_system_prompt(self, schemes_context: str) -> str:
        """Build the system prompt with all scheme information"""
        return f"""आप "सहाई" हैं - एक महिला हिंदी सरकारी योजना सहायिका। आप एक मददगार बहन की तरह बात करती हैं।

🎯 आपका काम:
1. सरकारी योजनाओं की जानकारी देना
2. पात्रता जांचना
3. आवेदन प्रक्रिया समझाना

📋 योजनाएं:
{schemes_context}

⚠️ बहुत महत्वपूर्ण - Voice Output के लिए:
- जवाब बहुत छोटा रखें (अधिकतम 3-4 वाक्य)
- सिर्फ सबसे जरूरी बात बताएं
- लंबी सूची न दें, सिर्फ 1-2 योजना बताएं
- इमोजी कम से कम उपयोग करें
- यदि जानकारी चाहिए तो सीधे पूछें
- महिला के रूप में बात करें (जैसे: "मैं बताती हूं", "मैंने समझा", "मैं आपकी मदद करूंगी")

📌 नियम:
- केवल हिंदी में जवाब दें
- बहुत संक्षिप्त रहें
- यदि पात्रता जांचनी है तो पहले उम्र और आय पूछें
- हमेशा महिला की भाषा शैली में बोलें (feminine verbs)"""

    def _build_user_context(self, user_data: Dict[str, Any], conversation_history: str) -> str:
        """Build context about the user"""
        context_parts = []
        
        if user_data:
            context_parts.append(f"उपयोगकर्ता की जानकारी: {json.dumps(user_data, ensure_ascii=False)}")
        
        if conversation_history:
            context_parts.append(f"पिछली बातचीत:\n{conversation_history}")
        
        if context_parts:
            return "📝 संदर्भ:\n" + "\n".join(context_parts)
        return ""
    
    def get_greeting(self) -> str:
        """Get initial greeting"""
        if not self.client:
            return self._default_greeting()
        
        try:
            prompt = """आप "सहाई" हैं - एक महिला हिंदी सरकारी योजना सहायिका। आप एक मददगार बहन की तरह बात करती हैं।
            
एक मित्रवत स्वागत संदेश दें जो बताए कि आप क्या-क्या कर सकती हैं।
महिला के रूप में बात करें (जैसे: "मैं बताती हूं", "मैं आपकी मदद करूंगी")।
संक्षिप्त रखें (4-5 वाक्य)। इमोजी का उपयोग करें।"""

            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=300
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Greeting error: {e}")
            return self._default_greeting()
    
    def _default_greeting(self) -> str:
        """Default greeting when AI is unavailable"""
        return """नमस्ते! 🙏 मैं सहाई हूं, आपकी सरकारी योजना सहायिका।

मैं आपको इन चीज़ों में मदद कर सकती हूं:
• सरकारी योजनाओं की जानकारी
• पात्रता जांच
• आवेदन प्रक्रिया

बताइए, आपको किस योजना के बारे में जानना है?"""

    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when AI is unavailable"""
        return """क्षमा करें, मैं अभी आपकी मदद करने में असमर्थ हूं।

कृपया थोड़ी देर बाद फिर से प्रयास करें या हेल्पलाइन पर कॉल करें: 1800-111-555"""
