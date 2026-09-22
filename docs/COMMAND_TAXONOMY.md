# Official Command Taxonomy & Voice Grammar

This document defines the official **5-Category Command Taxonomy** and natural Egyptian Arabic / English voice grammar supported by the **Jev Voice Computer Use** system.

---

## 🎵 1. Media & Music (الوسائط والموسيقى)

Direct playback across streaming platforms and hardware Win32 playback controls.

| Intent / Action | Natural Voice Examples (Arabic / English) | Execution Method |
| :--- | :--- | :--- |
| **Search & Auto-Play on YouTube Music** | - *"شغل اغنية اغيب في يوتيوب ميوزك"*<br>- *"سيرش على ويجز في youtube music وشغلها"* | Resolves top `#1` YouTube Video ID and directly opens `music.youtube.com/watch?v={id}` for instant auto-play. |
| **Search & Auto-Play on Spotify** | - *"شغل عمرو دياب في سبوتيفاي"*<br>- *"سيرش على تراك مكانك في سبوتيفاي وشغلها"* | Brings Spotify to foreground ➡️ dispatches `Ctrl + K` (Quick Search) ➡️ types clean query ➡️ hits `Enter`. |
| **Search on Anghami (أنغامي)** | - *"شغل اغنية اغيب في انغامي"*<br>- *"سيرش على عمرو دياب في أنغامي"* | Directly opens `play.anghami.com/search?query={query}` in browser. |
| **Search on SoundCloud** | - *"شغل مروان بابلو في ساوند كلاود"*<br>- *"سيرش على اغاني راپ في soundcloud"* | Directly opens `soundcloud.com/search?q={query}` in browser. |
| **Search on YouTube** | - *"شغل سورة الكهف على يوتيوب"*<br>- *"سيرش على يوتيوب على بودكاست كذا"* | Resolves top Video ID and opens `youtube.com/watch?v={id}`. |
| **Play / Pause Toggle** | - *"وقف الاغنية"* / *"ايقاف"* / *"pause"*<br>- *"شغل الاغنية"* / *"كمل"* / *"resume"* | Dispatches hardware Win32 Virtual Key `VK_MEDIA_PLAY_PAUSE` (`0xB3`). |
| **Next Track (التالي)** | - *"هات اللي بعدها"* / *"التالي"* / *"نكست"* / *"next"* | Dispatches hardware Win32 Virtual Key `VK_MEDIA_NEXT_TRACK` (`0xB0`). |
| **Previous Track (السابق)** | - *"رجع اللي قبلها"* / *"السابق"* / *"بريفيوس"* / *"back"* | Dispatches hardware Win32 Virtual Key `VK_MEDIA_PREV_TRACK` (`0xB1`). |

---

## 🌐 2. Web Navigation & Browsing (التصفح والمواقع)

General-purpose browser navigation without hardcoded URL requirements.

| Intent / Action | Natural Voice Examples (Arabic / English) | Execution Method |
| :--- | :--- | :--- |
| **Open Known Website** | - *"خش على موقع أنغامي"*<br>- *"ادخل على فيسبوك"*<br>- *"روح على كانفا"*<br>- *"افتح موقع chatgpt"*<br>- *"خش على twitter"* | Resolves known domain alias from `KNOWN_SITES` and directly launches URL in default browser. |
| **Open Domain Directly** | - *"خش على github.com"*<br>- *"روح لـ bue.edu.eg"*<br>- *"افتح amazon.eg"* | Automatically detects TLD (`.com`, `.org`, `.edu`, etc.) and launches `https://{domain}`. |
| **Search & Navigate Unknown Site** | - *"روح لموقع البنك الاهلي المصري"*<br>- *"ادخل على موقع مصلحة الضرائب"* | Strips dialect prefixes and queries Google Search for the exact institution/website. |
| **General Web Search (بحث جوجل)** | - *"ابحث في جوجل عن سعر الدولار اليوم"*<br>- *"سيرش في جوجل على اخبار الذكاء الاصطناعي"* | Launches `google.com/search?q={query}` directly in browser. |

---

## 💻 3. Apps & Windows (البرامج والنوافذ)

System application launching and desktop window state management.

| Intent / Action | Natural Voice Examples (Arabic / English) | Execution Method |
| :--- | :--- | :--- |
| **Launch Desktop App** | - *"افتح المفكرة"* / *"افتح نوت باد"*<br>- *"افتح الآلة الحاسبة"* / *"افتح كالكوليتور"*<br>- *"افتح في اس كود"* / *"شغل رايدر"* | Resolves `.lnk`, `.exe`, or Win32 protocol via `WindowsAppResolver` and activates window. |
| **Close Active Window** | - *"اقفل النافذة"* / *"اقفل البرنامج"* / *"اغلق النافذة"* / *"قفل"* | Dispatches `Alt + F4` shortcut. |
| **Show Desktop (Minimize All)** | - *"نزل كل النوافذ"* / *"صغر كل النوافذ"* / *"سطح المكتب"* / *"هات الديسك توب"* | Dispatches `Win + D` shortcut. |

---

## 🖱️ 4. In-App & UI Actions (التفاعل مع الشاشة)

Interacting with controls, text fields, and editing shortcuts in the active window.

| Intent / Action | Natural Voice Examples (Arabic / English) | Execution Method |
| :--- | :--- | :--- |
| **Type Arabic / English Text** | - *"اكتب تقرير الاجتماع اليوم"*<br>- *"اكتب Hello World"* | Injects text using safe Unicode clipboard paste (`Ctrl + V`). |
| **Click Specific UI Control** | - *"دوس على زرار الكلمات"*<br>- *"اضغط على حفظ"*<br>- *"دوس على ملف"* | Scans active window with `AccessibilityScanner` and triggers `InvokePattern` or mouse click. |
| **Save Document (Ctrl + S)** | - *"احفظ الملف"* / *"احفظ"* / *"سيف"* / *"save"* | Dispatches `Ctrl + S`. |
| **Copy Selection (Ctrl + C)** | - *"انسخ"* / *"كوبي"* / *"copy"* | Dispatches `Ctrl + C`. |
| **Paste Selection (Ctrl + V)** | - *"الصق"* / *"بيست"* / *"paste"* | Dispatches `Ctrl + V`. |
| **Select All (Ctrl + A)** | - *"حدد الكل"* / *"سلكت اول"* / *"select all"* | Dispatches `Ctrl + A`. |

---

## ⚙️ 5. System & Productivity (أوامر النظام والإنتاجية)

System audio volume adjustments and mathematical calculation.

| Intent / Action | Natural Voice Examples (Arabic / English) | Execution Method |
| :--- | :--- | :--- |
| **Increase Volume** | - *"علي الصوت"* / *"ارفع الصوت"* / *"زي الصوت"* | Sends 5 pulses of `VK_VOLUME_UP`. |
| **Decrease Volume** | - *"وطي الصوت"* / *"اخفض الصوت"* / *"نزل الصوت"* | Sends 5 pulses of `VK_VOLUME_DOWN`. |
| **Mute / Unmute** | - *"اكتم الصوت"* / *"ميوت"* / *"mute"* | Sends `VK_VOLUME_MUTE`. |
| **Evaluate Math Expression** | - *"احسب 50 في 12 زائد 100"*<br>- *"احسب 1500 مقسوم على 3"* | Opens Windows Calculator and evaluates expression. |

---

## ⛓️ Compound Multi-Step Commands (الأوامر المتتالية)

Connect multiple atomic tasks in a single breath using:
- **`وبعدين`**, **`ثم`**, **`وبعدها`**, **`and then`**
- Secondary **`و` + فعل أمر** (`وافتح`, `واكتب`, `واضغط`, `ودوس`, `وانقر`, `واحفظ`, `واقفل`, `وخش على`, `وادخل على`)

**Examples:**
- *"افتح المفكرة واكتب تقرير اليوم وبعدين احفظ الملف"* ➡️ Executes 3 atomic sub-tasks sequentially.
- *"خش على موقع أنغامي وشغل عمرو دياب"* ➡️ Opens Anghami then triggers Amr Diab search.
- *"سيرش على اغيب في يوتيوب ميوزك وشغلها"* ➡️ Searches YouTube Music with direct auto-play enabled.
