"""
SahAI Text-to-Speech - Hindi Voice Synthesis
Converts Hindi text to speech using gTTS
"""
import os
import re
import uuid
import time
from pathlib import Path
from typing import Optional

try:
    from config.settings import settings
    OUTPUT_DIR = Path(settings.audio.audio_output_dir)
except:
    OUTPUT_DIR = Path("audio_output")

OUTPUT_DIR.mkdir(exist_ok=True)


class TextToSpeech:
    """
    Hindi Text-to-Speech service
    Uses gTTS (Google TTS) for natural Hindi speech
    """
    
    def __init__(self):
        self._gtts_available = self._check_gtts()
        if not self._gtts_available:
            print("⚠️ gTTS not available - TTS disabled")
    
    def _check_gtts(self) -> bool:
        """Check if gTTS is available"""
        try:
            from gtts import gTTS
            return True
        except ImportError:
            return False
    
    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for TTS - remove emojis, symbols, markdown
        Keep only speakable content
        """
        # Remove emojis (Unicode emoji ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U0001F1E0-\U0001F1FF"  # Flags
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        
        # Remove markdown bold: **text** -> text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        # Remove markdown italic: *text* -> text  
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        # Remove underline markdown
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # Remove URLs
        text = re.sub(r'https?://[^\s]+', '', text)
        
        # Remove special bullet symbols
        text = text.replace('•', ',')
        text = text.replace('●', ',')
        text = text.replace('○', ',')
        text = text.replace('◆', ',')
        text = text.replace('★', '')
        text = text.replace('☆', '')
        text = text.replace('→', '')
        text = text.replace('✓', '')
        text = text.replace('✔', '')
        text = text.replace('✗', '')
        text = text.replace('✘', '')
        text = text.replace('📋', '')
        text = text.replace('📄', '')
        text = text.replace('📞', '')
        text = text.replace('🔗', '')
        text = text.replace('💰', '')
        text = text.replace('🏠', '')
        text = text.replace('👴', '')
        text = text.replace('👵', '')
        text = text.replace('🙏', '')
        text = text.replace('🎉', '')
        text = text.replace('✅', '')
        text = text.replace('❌', '')
        text = text.replace('⚠️', '')
        text = text.replace('ℹ️', '')
        text = text.replace('🇮🇳', '')
        
        # Clean up dashes used as bullets
        text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def synthesize(self, text: str, slow: bool = False) -> Optional[str]:
        """
        Convert Hindi text to speech
        
        Args:
            text: Hindi text to synthesize
            slow: Whether to speak slowly
            
        Returns:
            Path to generated audio file or None
        """
        if not text or not text.strip():
            return None
        
        if not self._gtts_available:
            print("TTS not available")
            return None
        
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            
            # Clean text for speech (remove emojis, symbols, markdown)
            clean_text = self._clean_text_for_speech(text)
            
            if not clean_text:
                return None
            
            # For long text, split into chunks and combine
            # gTTS can fail or truncate with very long text
            MAX_CHUNK_LENGTH = 500  # Characters per chunk
            
            if len(clean_text) > MAX_CHUNK_LENGTH:
                return self._synthesize_long_text(clean_text, slow)
            
            # Generate speech (Hindi)
            tts = gTTS(text=clean_text, lang="hi", slow=slow)
            
            # Save to file
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            filepath = OUTPUT_DIR / filename
            tts.save(str(filepath))
            
            print(f"🔊 Generated audio: {filename} ({len(clean_text)} chars)")
            return str(filepath)
            
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    def _synthesize_long_text(self, text: str, slow: bool = False) -> Optional[str]:
        """
        Handle long text by splitting into chunks and combining audio
        """
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            
            # Split text into sentences/chunks
            chunks = self._split_into_chunks(text, max_length=500)
            
            if not chunks:
                return None
            
            print(f"🔊 Long text: splitting into {len(chunks)} chunks")
            
            # Generate audio for each chunk
            audio_segments = []
            temp_files = []
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                    
                try:
                    tts = gTTS(text=chunk, lang="hi", slow=slow)
                    temp_file = OUTPUT_DIR / f"temp_{uuid.uuid4().hex[:8]}.mp3"
                    tts.save(str(temp_file))
                    temp_files.append(temp_file)
                    
                    # Load audio segment
                    segment = AudioSegment.from_mp3(str(temp_file))
                    audio_segments.append(segment)
                    
                except Exception as e:
                    print(f"Chunk {i} TTS error: {e}")
                    continue
            
            if not audio_segments:
                return None
            
            # Combine all segments
            combined = audio_segments[0]
            for segment in audio_segments[1:]:
                # Add small pause between chunks
                combined += AudioSegment.silent(duration=200) + segment
            
            # Save combined audio
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            filepath = OUTPUT_DIR / filename
            combined.export(str(filepath), format="mp3")
            
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except:
                    pass
            
            print(f"🔊 Generated combined audio: {filename} ({len(chunks)} chunks)")
            return str(filepath)
            
        except ImportError:
            print("⚠️ pydub not available for long text - using truncated version")
            # Fallback: just use first chunk
            return self._synthesize_fallback(text[:500], slow)
            
        except Exception as e:
            print(f"Long text TTS error: {e}")
            return self._synthesize_fallback(text[:500], slow)
    
    def _split_into_chunks(self, text: str, max_length: int = 500) -> list:
        """
        Split text into speakable chunks at sentence boundaries
        """
        # Split by sentence-ending punctuation
        sentences = re.split(r'([।.!?\n])', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # Add punctuation back if exists
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [c for c in chunks if c.strip()]
    
    def _synthesize_fallback(self, text: str, slow: bool = False) -> Optional[str]:
        """Fallback synthesis for when chunking fails"""
        try:
            from gtts import gTTS
            
            tts = gTTS(text=text, lang="hi", slow=slow)
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            filepath = OUTPUT_DIR / filename
            tts.save(str(filepath))
            return str(filepath)
        except:
            return None
    
    def cleanup(self, max_age_hours: int = 1):
        """Remove old TTS files"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file in OUTPUT_DIR.glob("tts_*.mp3"):
                try:
                    file_age = current_time - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file.unlink()
                except:
                    pass
        except Exception as e:
            print(f"Cleanup error: {e}")
