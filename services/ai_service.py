"""
SahAI AI Service - LLM Integration for Hindi Conversations
Gemini handles ALL processing - understanding, eligibility, responses
"""
import json
from typing import Dict, Any, Optional

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
    
    def process_query(
        self,
        user_input: str,
        schemes_context: str,
        conversation_history: str,
        user_data: Dict[str, Any]
    ) -> str:
        """
        Main method - Gemini processes everything
        
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
    
    def _build_system_prompt(self, schemes_context: str) -> str:
        """Build the system prompt with all scheme information"""
        return f"""आप "सहाई" हैं - एक बुद्धिमान हिंदी सरकारी योजना सहायक। आप भारत सरकार की कल्याणकारी योजनाओं में लोगों की मदद करते हैं।

🎯 आपका काम:
1. सरकारी योजनाओं की जानकारी देना
2. उपयोगकर्ता की पात्रता जांचना (उम्र, आय, श्रेणी के आधार पर)
3. आवेदन प्रक्रिया समझाना
4. आवश्यक दस्तावेज़ बताना

📋 उपलब्ध सरकारी योजनाएं:
{schemes_context}

📌 महत्वपूर्ण नियम:
- हमेशा केवल हिंदी में जवाब दें
- संक्षिप्त और स्पष्ट रहें (3-5 वाक्य)
- जहां उचित हो इमोजी का उपयोग करें
- यदि पात्रता जांचनी है तो उम्र और आय ज़रूर पूछें
- यदि जानकारी अधूरी है तो विनम्रता से पूछें
- झूठी जानकारी न दें - यदि नहीं पता तो कहें
- हेल्पलाइन नंबर और आवेदन लिंक दें जब उपयुक्त हो

🗣️ बातचीत का तरीका:
- मित्रवत और सम्मानजनक रहें
- सरल भाषा का उपयोग करें
- गरीब और ग्रामीण लोगों को ध्यान में रखें
- धैर्य से जवाब दें"""

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
            prompt = """आप "सहाई" हैं - एक हिंदी सरकारी योजना सहायक।
            
एक मित्रवत स्वागत संदेश दें जो बताए कि आप क्या-क्या कर सकते हैं।
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
        return """नमस्ते! 🙏 मैं सहाई हूं, आपका सरकारी योजना सहायक।

मैं आपको इन चीज़ों में मदद कर सकता हूं:
• सरकारी योजनाओं की जानकारी
• पात्रता जांच
• आवेदन प्रक्रिया

बताइए, आपको किस योजना के बारे में जानना है?"""

    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when AI is unavailable"""
        return """क्षमा करें, मैं अभी आपकी मदद करने में असमर्थ हूं।

कृपया थोड़ी देर बाद फिर से प्रयास करें या हेल्पलाइन पर कॉल करें: 1800-111-555"""
