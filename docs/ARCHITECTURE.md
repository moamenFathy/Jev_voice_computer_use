# System Architecture

This document details the architectural layout, communication pipelines, and lifecycle of voice commands within the **Jev Voice Computer Use** system.

---

## 🏗️ Layered Architecture Diagram

```mermaid
graph TD
    subgraph Voice_Layer["1. Voice & Speech Input/Output"]
        Mic["Microphone Input"] --> STT["Bilingual STT (ar-EG / en-US Fallback)"]
        TTS["Edge-TTS (Arabic ShakirNeural)"] --> Speaker["System Audio Speaker"]
    end

    subgraph UI_Layer["2. Glassmorphism Dynamic Island UI"]
        DI["DynamicIsland (Tkinter App)"]
        DI --> StreamToggle["Streaming / Push-to-Talk Toggle"]
        DI --> WaveAnim["Animated Sine Audio Visualizer"]
    end

    subgraph Decision_Layer["3. Decision & Planning Engine"]
        Planner["Step Decomposer (Multi-step Sequential Split)"]
        EntityExt["Sanitized Entity & Platform Extractor"]
        FastPath{"Fast-Path Candidate?"}
        JevModel["Jev System One (TypeSafe AI Decision Model)"]
    end

    subgraph Execution_Layer["4. OS & UI Automation Controllers"]
        UIA["Accessibility Scanner (UI Automation COM Tree)"]
        AppRes["Windows App Resolver (Path & Protocol Indexer)"]
        OSCtrl["OS Controller (Win32 Virtual Keys & Clipboard Injection)"]
        BrowserNav["Web & Media Dispatcher (YouTube, Music, Chrome)"]
    end

    STT --> DI
    DI --> Planner
    Planner --> EntityExt
    EntityExt --> FastPath

    FastPath -->|"Media Controls / Direct Track URLs"| BrowserNav
    FastPath -->|"Local UI Synonyms Match"| UIA
    FastPath -->|"Complex / Ambiguous Goal"| JevModel

    JevModel --> AppRes
    JevModel --> UIA
    JevModel --> OSCtrl
    JevModel --> BrowserNav

    UIA --> OSCtrl
    BrowserNav --> TTS
    UIA --> TTS
```

---

## 🔄 End-to-End Command Lifecycle

1. **Audio Ingestion (`src/voice/voice_engine.py`):**
   - User speaks into the microphone in either Egyptian Arabic, Modern Standard Arabic (MSA), or English.
   - `VoiceEngine.listen_command()` or `start_streaming_listen()` processes the audio stream with ambient noise calibration.
   - Primary recognition runs with `language="ar-EG"`. If `sr.UnknownValueError` occurs, it automatically falls back to `language="en-US"`.

2. **Sequential Step Decomposition (`src/decision/jev_engine.py`):**
   - The recognized string is passed to `_decompose_into_steps()`.
   - Sequential connectors (`وبعدين`, `ثم`, `وبعدها`, `and then`) and secondary verb conjuncts (`واكتب`, `وافتح`, `واحفظ`) split compound instructions into ordered atomic tasks (`[Step 1, Step 2, ...]`).
   - Playback modifiers (`وشغلها`, `وشغله`, `and play it`) are detected and tagged as `auto_play = True` on the target step.

3. **Entity Extraction & Dialect Sanitization:**
   - `_extract_clean_entities()` extracts the target platform (`youtube_music`, `spotify`, `youtube`, `google`, or `default`).
   - Strips conversational prepositions (`في`, `على`, `علي`, `غلي`, `من`, `عن`), action verbs (`سيرش`, `ابحث`, `شغل`, `افتح`), and entity labels (`اغنية`, `تراك`) to yield the pure target entity (e.g. `"اغيب"`).

4. **Multi-Level Dispatching:**
   - **Level 1 (Fast-Path Multimedia):**
     - Hardware multimedia controls (`playpause`, `nexttrack`, `prevtrack`) are sent directly via Win32 Virtual Key codes (`0xB0`, `0xB1`, `0xB3`).
     - Direct YouTube / YouTube Music track resolution: Queries top video ID in <1s and opens `music.youtube.com/watch?v={id}` directly.
     - Spotify Quick Search: Focuses Spotify window and triggers `Ctrl + K` ➡️ query paste ➡️ `Enter`.
   - **Level 2 (Fast-Path UI Synonyms):**
     - Scans active window with `AccessibilityScanner.scan_active_window()`.
     - Matches user query against bilingual synonyms dictionary (`BILINGUAL_UI_SYNONYMS`).
     - Triggers programmatic invoke or coordinate click on the matched control.
   - **Level 3 (Jev System One AI Model):**
     - If not resolved locally, sends the current window title, top visible controls, and goal to TypeSafe AI's `client.system_one()`.
     - Returns strict classified action (`launch_app`, `in_app_search`, `click_ui_element`, `type_text`, `keyboard_shortcut`, etc.) with sub-second response time.

5. **Safe Unicode Execution & TTS Feedback:**
   - Text is injected using clipboard pasting (`Ctrl + V`) to preserve Arabic Unicode characters without corrupting text buffers.
   - Execution status is updated in the Dynamic Island UI and spoken via Edge-TTS (`ar-EG-ShakirNeural`).

---

---

## 🛡️ Reliability Architecture (Phase 1)

Phase 1 incorporates an execution-verification-retry architecture based on the core axiom:

> **Execution != Goal Achievement** (A tool call completing without an exception is not proof of success).

```mermaid
flowchart TD
    UserGoal["User Goal"] --> Decompose["Step Decomposition"]
    Decompose --> Step["Current Sub-step"]
    Step --> Decision["Jev Decision"]
    Decision --> Tool["Tool Execution"]
    Tool --> ExecCheck{"Tool Successful?"}

    ExecCheck -->|No| FailReason["Classify FailureReason"]
    FailReason --> Retryable{"Retryable & Attempts Left?"}
    Retryable -->|Yes| WaitReObserve["Wait & Re-observe UI Tree"]
    WaitReObserve --> Tool
    Retryable -->|No| StepFail["Step Failed -> Abort Goal"]

    ExecCheck -->|Yes| Observe["Capture Observation"]
    Observe --> Verify["Run Verifier"]
    Verify --> VerCheck{"Verification Passed?"}
    
    VerCheck -->|No| Retryable
    VerCheck -->|Yes| NextStep["ToolResult(success=True) -> Next Step"]

    StepFail --> GoalFail["GoalResult(success=False)"]
    NextStep --> AllDone{"All Steps Done?"}
    AllDone -->|Yes| GoalPass["GoalResult(success=True)"]
```

### Core Reliability Components:
1. **`ToolResult` (`src/core/tool_result.py`)**: Structured outcome for every tool call with `success`, `failure_reason`, `retryable`, and `evidence`.
2. **`Observation` (`src/core/observation.py`)**: Environmental state captured after execution from UIA trees, window titles, or clipboard buffers.
3. **`Verifier` (`src/verification/verifier.py`)**: Domain validators including `AppLaunchVerifier`, `TextVerifier`, `UIElementVerifier`, and `SearchVerifier`.
4. **`AgentRuntime` (`src/runtime/agent_runtime.py`)**: Bounded retry loop (`MAX_RETRIES = 2`, `RETRY_DELAY = 0.5s`) with live reliability metrics (`goal_success_rate`, `retries_attempted`, `verification_failures`).
5. **`GoalResult` (`src/core/goal_result.py`)**: Aggregated multi-step outcome enforcing strict failure propagation across sequential sub-steps.

---

## 🧵 Threading & COM Apartment Model

```
+-----------------------------------------------------------------------+
| Main UI Thread (Tkinter Event Loop)                                   |
| - Manages Glassmorphism window, drag events, and Sine visualizer      |
+-----------------------------------------------------------------------+
                                  |
                                  | Launches worker thread on voice input
                                  v
+-----------------------------------------------------------------------+
| Background Worker Thread (threading.Thread, daemon=True)              |
| - with auto.UIAutomationInitializerInThread():                         |
|   * Initializes COM Apartment (MTA/STA) for UIAutomationCore.dll      |
|   * Executes JevDecisionEngine.execute_goal()                         |
|   * Dispatches Win32 and PyAutoGUI events                             |
|   * Sends status callbacks back to Tkinter UI                         |
+-----------------------------------------------------------------------+
```

Without `auto.UIAutomationInitializerInThread()`, calling `uiautomation` inside a non-main Python thread triggers `[WinError -2147221008] CoInitialize has not been called`. The `@ensure_com_initialized` decorator guarantees safe execution across all entrypoints.

