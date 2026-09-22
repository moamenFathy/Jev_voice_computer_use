# Jev Decision Engine & Planning

The **Jev Decision Engine** (`src/decision/jev_engine.py`) is the cognitive core of the system. Powered by **TypeSafe AI's System One model**, it delivers deterministic, high-speed computer use decisions without multi-turn chat overhead.

---

## ⚡ Why TypeSafe AI System One?

Standard LLMs (like GPT-4 or Claude) require multi-second generation times, full text responses, and complex JSON parsing that introduce 2-5 seconds of latency per step. 

**TypeSafe AI System One** provides:
- **Sub-300ms Inference Latency:** Evaluates classification questions over structured criteria simultaneously.
- **Deterministic Choices:** Restricts actions to predefined enum criteria (`Choice`), eliminating hallucinated actions.
- **Calibrated Confidence Scoring:** Returns a confidence metric (`0.0` to `1.0`) allowing graceful fallbacks if confidence is low.

---

## 📥 Input Payload (`State Context`)

When an ambiguous or non-fast-path command is received, the engine builds a `State Context` string:

```text
User Step Goal: 'اكتب تقرير الاجتماع'
Active Window: 'Untitled - Notepad | Controls: 1:Edit 'Text Editor', 2:MenuItem 'File', 3:MenuItem 'Edit''
System Environment: Windows 11 Desktop
```

---

## 📋 Decision Schema & Question Definitions

The engine queries three categorical choices in a single API call:

### 1. `primary_action` (Choice)
- **`launch_app`**: Launch a desktop application or IDE.
- **`in_app_search`**: Search for an item, song, contact, or file inside an open or targeted desktop app.
- **`click_ui_element`**: Click a specific button, menu item, tab, or checkbox inside the active window.
- **`web_search`**: Search the web on Google for informational queries.
- **`type_text`**: Type Arabic or English text into the active document or input field.
- **`math_calculate`**: Calculate a math expression or type numbers into calculator.
- **`keyboard_shortcut`**: Execute shortcut like copy, paste, select all, close window, minimize.
- **`volume_control`**: Increase, decrease, or mute system audio volume.
- **`finish`**: Goal is already complete.

### 2. `target_app` (Choice)
Specifies target application: `spotify`, `rider`, `visual_studio`, `code`, `cursor`, `calculator`, `chrome`, `edge`, `notepad`, `paint`, `explorer`, `cmd`, `discord`, `telegram`, `whatsapp`, `none`.

### 3. `shortcut_type` (Choice)
Specifies required keyboard shortcut: `enter`, `escape`, `close_window` (Alt+F4), `minimize_all` (Win+D), `copy` (Ctrl+C), `paste` (Ctrl+V), `select_all` (Ctrl+A), `save` (Ctrl+S), `none`.

---

## 📤 Model Output & Execution Mapping

```json
{
  "answers": {
    "primary_action": {
      "choice": "type_text",
      "confidence": 0.98
    },
    "target_app": {
      "choice": "notepad",
      "confidence": 0.95
    },
    "shortcut_type": {
      "choice": "none",
      "confidence": 1.0
    }
  }
}
```

### Execution Dispatch Table

| Action Choice | Underlying Tool Call | Implementation Detail |
| :--- | :--- | :--- |
| `launch_app` | `WindowsAppResolver.launch(target_app)` | Resolves `.lnk`, `.exe`, or URI protocol handlers. |
| `in_app_search` | `AccessibilityScanner.universal_in_app_search(query)` | Locates search box via UIA or uses `Ctrl+K`/`Ctrl+L`. |
| `click_ui_element` | `AccessibilityScanner.click_element(target_elem)` | Uses `InvokePattern` / `TogglePattern` or mouse click. |
| `type_text` | `OSController.type_arabic(clean_query)` | Unicode-safe clipboard injection via `Ctrl+V`. |
| `keyboard_shortcut` | `OSController.hotkey(keys)` | Dispatches PyAutoGUI key sequences. |
| `volume_control` | `OSController.press_key("volumeup" / "volumedown")` | Win32 hardware virtual key codes. |

---

## 🧩 Compound Multi-Step Goal Decomposer

The `_decompose_into_steps(goal)` method handles true multi-step voice inputs:

1. **Connector Splitting:** Splits on sequential connectors (`وبعدين`, `وبعدها`, `ثم`, `وبعد ذلك`, `and then`, `then`, `after that`).
2. **Action Verb Conjunctions:** Splits on `و` when directly followed by imperative verbs (`وافتح`, `واكتب`, `واضغط`, `ودوس`, `وانقر`, `واحفظ`, `واقفل`, `ودور على`).
3. **Auto-Play Modifier Detection:** Detects suffixes like `وشغلها`, `وشغله`, `and play it` and flags `auto_play = True` on the search step rather than creating a broken orphan sub-step.
