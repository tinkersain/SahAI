"""
SahAI Settings - Application Configuration
Simple configuration management
"""
import os
from pathlib import Path
from dataclasses import dataclass

# Load .env file if exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class AudioConfig:
    """Audio settings"""
    whisper_model: str = "base"  # base, small, medium
    audio_output_dir: str = "audio_output"


@dataclass 
class AIConfig:
    """AI service settings"""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"


@dataclass
class Settings:
    """Main application settings"""
    app_name: str = "SahAI"
    version: str = "2.0.0"
    debug: bool = True
    
    audio: AudioConfig = None
    ai: AIConfig = None
    
    def __post_init__(self):
        # Initialize with environment variables
        self.audio = AudioConfig(
            whisper_model=os.getenv("WHISPER_MODEL", "base"),
            audio_output_dir=os.getenv("AUDIO_OUTPUT_DIR", "audio_output")
        )
        
        self.ai = AIConfig(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        )


# Global settings instance
settings = Settings()
