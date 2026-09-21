import os
from pathlib import Path
from dotenv import load_dotenv

# Root Directory of the Project
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# Load .env file from root
load_dotenv(PROJECT_ROOT / ".env")

# Jev Configuration
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "").strip()
DECISION_MODEL = os.getenv("DECISION_MODEL", "jev-latest")

# Voice Configuration
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "ar-EG")
TTS_VOICE = os.getenv("TTS_VOICE", "ar-EG-SalmaNeural")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

# Safety & Execution Settings
FAILSAFE_ENABLED = os.getenv("FAILSAFE_ENABLED", "true").lower() == "true"
MAX_STEPS_PER_COMMAND = int(os.getenv("MAX_STEPS_PER_COMMAND", "10"))
STEP_PAUSE_SECONDS = 0.5

# Directories
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)
