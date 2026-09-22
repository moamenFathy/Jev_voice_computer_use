# Developer & Setup Guide

This guide provides instructions for setting up the development environment, running tests, following project standards, and extending capabilities.

---

## 🚀 Environment Setup

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10+ (Recommended: Python 3.11)
- Working Microphone & Speaker

### Virtual Environment Setup
```powershell
# 1. Clone repository (or navigate to workspace)
cd C:\Users\moame\arabic_voice_computer_use

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Verify installed dependencies
pip list
```

### Core Dependencies
- `typesafe-sdk`: TypeSafe AI System One decision engine.
- `uiautomation`: Windows UI Automation COM apartment inspection.
- `comtypes`: COM threading and apartment initialization.
- `speechrecognition`, `pyaudio`: STT capture and speech recognition.
- `edge-tts`, `pygame`: Neural TTS synthesis and async playback.
- `pyautogui`, `pyperclip`, `pygetwindow`: Mouse/keyboard automation and clipboard injection.

---

## ⚙️ Configuration (`src/config.py`)

Key settings configurable in `src/config.py` or `.env`:

```python
# API Keys
TYPESAFE_API_KEY = "..."

# Voice Settings
VOICE_LANGUAGE = "ar-EG"
TTS_VOICE = "ar-EG-ShakirNeural"
TTS_ENABLED = True

# Automation Safety
FAILSAFE_ENABLED = True
STEP_PAUSE_SECONDS = 0.5
MAX_STEPS_PER_COMMAND = 5
```

---

## 🧪 Running Automated Tests

Run the test suite from the repository root:

```powershell
# 1. Test bilingual UI synonym matching
.\venv\Scripts\python.exe -m unittest tests/test_bilingual_matching.py

# 2. Test multi-step decomposition and entity extraction
.\venv\Scripts\python.exe -m unittest tests/test_multistep_and_entities.py

# 3. Test direct media routing & YouTube ID resolution
.\venv\Scripts\python.exe -m unittest tests/test_play_routing.py
```

---

## 📜 Development & Coding Rules

1. **Strict Git Rule:** **NEVER** run `git commit` or `git push` without explicit user permission.
2. **Terminal Language Rule:** **100% English** for all terminal prints, log outputs, and startup banners.
3. **COM Thread Safety:** Always wrap UIAutomation calls in background threads with `@ensure_com_initialized` or `with auto.UIAutomationInitializerInThread():`.
4. **Safe Unicode Typing:** Always use `OSController.type_arabic()` (clipboard injection) for Arabic or rich text entry into Windows apps.
5. **No Per-App Custom Scrapers:** Rely on universal accessibility tree inspection (`AccessibilityScanner`) rather than creating isolated, brittle app controllers.
