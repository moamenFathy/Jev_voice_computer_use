# Product Roadmap & Future Architecture

This document outlines the architectural enhancements planned for **Jev Voice Computer Use**.

---

## 🎯 High-Priority Capabilities

### 1. Universal Web Navigator (Autonomous Result Clicker)
- **Goal:** Enable natural navigation to any website without per-site hardcoding (e.g., *"خش على موقع أنغامي وافتح كذا"* or *"ادخل على موقع بنك مصر"*).
- **Architecture:**
  1. Detect navigation intent from colloquial verbs (`خش على`, `ادخل على`, `روح لموقع`, `افتح موقع`).
  2. If the query contains a known domain or matches a common top-level domain (`.com`, `.org`, `.gov.eg`), launch directly.
  3. Otherwise, perform a Google Search, then immediately scan the active browser window using UIAutomation to **click the top search result link** automatically, bringing the user directly into the target website.

### 2. General-Purpose Web Search Fallback for Media Platforms
- **Goal:** Support arbitrary media platforms (Anghami, SoundCloud, Apple Music, Deezer) generically.
- **Architecture:** Route search requests to the platform's query URL pattern (e.g. `play.anghami.com/search?query=...`, `soundcloud.com/search?q=...`) rather than dumping full conversational sentences into Google.

### 3. Vision Grounding (Hybrid UIA + Screenshot OCR)
- **Goal:** Complement UIA with local OCR / Vision grounding for custom-drawn canvas applications (like games or non-standard legacy apps) that do not expose accessibility elements.

### 4. Fully Local / Offline Mode
- **Goal:** Provide offline speech recognition via local Whisper models (`faster-whisper-small`) and offline TTS via Piper / Coqui TTS when internet access is unavailable.
