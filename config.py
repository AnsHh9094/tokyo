"""
Centralized configuration management for Jarvis AI Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Base directories
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
MEMORY_DIR = BASE_DIR / "memory" / "data"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"

# Create directories if they don't exist
for dir_path in [CONFIG_DIR, MEMORY_DIR, LOGS_DIR, ASSETS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # or "deepseek-reasoner"
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Assistant Configuration
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Tokyo")
WAKE_WORD = os.getenv("WAKE_WORD", "tokyo").lower()

# Speech Configuration
VOSK_MODEL_PATH = BASE_DIR / "vosk-model-small-en-us-0.15"
TTS_VOICE = os.getenv("TTS_VOICE", "en-GB-RyanNeural") # JARVIS-like British Male Voice
TTS_RATE = os.getenv("TTS_RATE", "-5%")    # Calm, measured pace (like JARVIS)
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")
TTS_PITCH = os.getenv("TTS_PITCH", "-3Hz") # Deep, refined tone

# Hotkey Configuration
HOTKEY = os.getenv("HOTKEY", "ctrl+shift+j")

# Memory Configuration
LONG_TERM_MEMORY_FILE = MEMORY_DIR / "long_term_memory.json"
CONVERSATION_HISTORY_SIZE = 10  # Number of recent messages to keep in memory

# Safety Configuration
FORBIDDEN_COMMANDS = [
    "format c:",
    "del c:\\",
    "rm -rf /",
    "shutdown /s /f"
]

REQUIRE_CONFIRMATION = [
    "delete",
    "remove",
    "shutdown",
    "restart",
    "format"
]

# UI Configuration
UI_WINDOW_SIZE = (760, 900)
FACE_IMAGE_SIZE = (760, 760)
FACE_IMAGE_PATH = ASSETS_DIR / "face.png"

# Logging Configuration
LOG_FILE = LOGS_DIR / "jarvis.log"
LOG_LEVEL = "INFO"

# Token tracking (for staying within free tier)
MAX_DAILY_TOKENS = 100000  # Conservative limit for free tier
TOKEN_TRACKING_FILE = MEMORY_DIR / "token_usage.json"
