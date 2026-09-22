# Arabic & English Voice Computer Use Documentation

Welcome to the comprehensive architecture and developer documentation for **Jev Voice Computer Use**, an intelligent, low-latency, bilingual (Egyptian Arabic + English) voice-controlled Windows desktop assistant powered by **Jev (TypeSafe AI System One)** and the **Windows UI Automation (UIA) Accessibility Tree**.

---

## 📚 Documentation Index

| Document | Description |
| :--- | :--- |
| [**1. System Architecture**](ARCHITECTURE.md) | High-level system design, data & action lifecycle, layered hierarchy, and thread safety. |
| [**2. Command Taxonomy & Voice Grammar**](COMMAND_TAXONOMY.md) | Official 5-category voice command reference, Egyptian Arabic triggers, and multi-step patterns. |
| [**3. Jev Decision Engine & Planning**](JEV_DECISION_ENGINE.md) | TypeSafe AI System One integration, state context payloads, decision schemas, and compound multi-step goal decomposition. |
| [**4. Windows UI Automation & Accessibility**](ACCESSIBILITY_AND_UI_AUTOMATION.md) | Universal in-app inspection, bilingual control matching, COM apartment management, and control dispatch. |
| [**5. Voice & Speech Pipeline**](VOICE_AND_AUDIO.md) | Dual-language speech recognition (`ar-EG` & `en-US`), edge-TTS neural voice synthesis, and audio visualizer. |
| [**6. Developer & Setup Guide**](DEVELOPER_GUIDE.md) | Installation, environment configuration, running tests, coding rules, and adding new capabilities. |
| [**7. Product Roadmap & Future Architecture**](ROADMAP.md) | Upcoming features including Universal Web Navigator (Autonomous Result Clicker), Vision Grounding, and Offline Support. |

---

## ⚡ Core Philosophy & Design Principles

1. **Sub-Second Decision Latency:** Fast-path pattern matching and TypeSafe AI System One decision classification deliver decisions in <300ms without slow multi-turn LLM agent loops.
2. **General-Purpose UI Automation:** Avoid brittle per-app hardcoded scrapers. Inspect Windows Accessibility Tree to discover buttons, text inputs, and menus dynamically across any desktop application.
3. **Bilingual Egyptian Arabic + English:** Seamless support for Egyptian Arabic idioms, phonetics, and mixed English/Arabic tech terms without polluted query strings.
4. **Thread-Safe COM Architecture:** Explicit initialization of COM apartments across Tkinter UI threads and background worker threads using `auto.UIAutomationInitializerInThread()`.
5. **100% English Logs & Developer Interface:** All terminal outputs, startup banners, and log messages remain strictly in English for clean debugging and telemetry.
