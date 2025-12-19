"""
SahAI Speech-to-Text - Hindi Voice Recognition
Uses Gemini model for Hindi speech transcription via base64 audio
"""
import os
import base64
from typing import Optional

try:
    from config.settings import settings
except ImportError:
    class MockSettings:
        class AI:
            gemini_api_key = ""
            gemini_model = "gemini-2.0-flash"
        ai = AI()
    settings = MockSettings()


class SpeechToText:
    """
    Hindi Speech-to-Text service
    Uses Gemini model for transcription via base64 encoded audio
    """
    
    def __init__(self):
        self.client = None
        self.model_name = None
        self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini client for audio transcription"""
        api_key = getattr(settings.ai, 'gemini_api_key', '') or ""
        
        if not api_key:
            print("⚠️ Gemini API key not set - STT will not work")
            return
        
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model_name = getattr(settings.ai, 'gemini_model', 'gemini-2.0-flash')
            print(f"✅ Gemini STT initialized: {self.model_name}")
        except ImportError:
            print("⚠️ google-genai not installed")
        except Exception as e:
            print(f"⚠️ Gemini STT init failed: {e}")
    
    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to Hindi text using Gemini
        
        Args:
            audio_path: Path to audio file (wav, webm, mp3, etc.)
            
        Returns:
            Transcribed Hindi text or None
        """
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return None
        
        if not self.client:
            print("❌ Gemini client not initialized")
            return self._fallback_transcribe(audio_path)
        
        try:
            return self._transcribe_gemini(audio_path)
        except Exception as e:
            print(f"Gemini transcription error: {e}")
            return self._fallback_transcribe(audio_path)
    
    def _transcribe_gemini(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using Gemini with base64 encoding"""
        from google.genai import types
        
        # Read audio bytes
        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
        
        # Determine MIME type
        mime_type = self._get_mime_type(audio_path)
        
        # Create the prompt for transcription
        prompt = """आप एक हिंदी speech-to-text transcriber हैं।

इस ऑडियो को सुनें और केवल हिंदी में transcribe करें।

नियम:
1. केवल बोले गए शब्द लिखें
2. कोई अतिरिक्त टिप्पणी न करें
3. अगर कुछ समझ न आए तो [unclear] लिखें
4. अंग्रेजी शब्द भी देवनागरी में लिखें

Transcription:"""

        # Send audio to Gemini using inline data
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                {
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": base64.standard_b64encode(audio_bytes).decode("utf-8")}},
                        {"text": prompt}
                    ]
                }
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=500
            )
        )
        
        text = response.text.strip()
        
        # Clean up response
        text = self._clean_transcription(text)
        
        if text:
            print(f"📝 Transcribed (Gemini): {text[:50]}...")
            return text
        return None
    
    def _get_mime_type(self, audio_path: str) -> str:
        """Get MIME type based on file extension"""
        ext = audio_path.lower().rsplit('.', 1)[-1]
        mime_types = {
            'wav': 'audio/wav',
            'mp3': 'audio/mp3',
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
            'm4a': 'audio/mp4',
            'flac': 'audio/flac',
            'aac': 'audio/aac'
        }
        return mime_types.get(ext, 'audio/wav')
    
    def _clean_transcription(self, text: str) -> str:
        """Clean up Gemini transcription output"""
        # Remove common prefixes that Gemini might add
        prefixes_to_remove = [
            "Transcription:",
            "transcription:",
            "Hindi transcription:",
            "हिंदी ट्रांसक्रिप्शन:",
        ]
        
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Remove quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        
        return text.strip()
    
    def _fallback_transcribe(self, audio_path: str) -> Optional[str]:
        """Fallback transcription using Google Speech Recognition"""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            
            # Convert to WAV if needed
            wav_path = self._ensure_wav(audio_path)
            
            try:
                with sr.AudioFile(wav_path) as source:
                    audio = recognizer.record(source)
                
                # Use Hindi for recognition
                text = recognizer.recognize_google(audio, language="hi-IN")
                print(f"📝 Transcribed (Google fallback): {text[:50]}...")
                return text
                
            finally:
                # Cleanup converted file
                if wav_path != audio_path and os.path.exists(wav_path):
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                        
        except ImportError:
            print("❌ SpeechRecognition library not installed")
            return None
        except Exception as e:
            print(f"Google STT error: {e}")
            return None
    
    def _ensure_wav(self, audio_path: str) -> str:
        """Convert audio to WAV if needed for fallback"""
        if audio_path.lower().endswith('.wav'):
            return audio_path
        
        try:
            from pydub import AudioSegment
            
            # Determine format
            if audio_path.lower().endswith('.webm'):
                audio = AudioSegment.from_file(audio_path, format="webm")
            else:
                audio = AudioSegment.from_file(audio_path)
            
            # Convert to mono 16kHz WAV
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            wav_path = audio_path.rsplit('.', 1)[0] + '_converted.wav'
            audio.export(wav_path, format="wav")
            return wav_path
            
        except Exception as e:
            print(f"Audio conversion failed: {e}")
            return audio_path
