import os
import re
import difflib
from pathlib import Path
import subprocess

class WindowsAppResolver:
    def __init__(self):
        self.apps = {}
        self._index_installed_apps()
        
        # القاموس الصوتي الشامل لربط الأسماء العربية والإنجليزية بالتطبيقات
        self.arabic_alias_map = {
            # IDEs وبيئات التطوير
            "رايدر": "rider",
            "جيت برينز رايدر": "rider",
            "جت برينز رايدر": "rider",
            "جيتبرينز": "rider",
            "rider": "rider",
            "jetbrains rider": "rider",
            
            "فيجوال ستوديو كوميونيتي": "visual studio",
            "فيجوال ستوديو": "visual studio",
            "فيجوال استوديو": "visual studio",
            "visual studio": "visual studio",
            "visual studio community": "visual studio",
            "vs community": "visual studio",
            
            "في اس كود": "code",
            "فيجوال ستوديو كود": "code",
            "كود": "code",
            "vscode": "code",
            "visual studio code": "code",
            
            "كيرسور": "cursor",
            "كرسور": "cursor",
            "cursor": "cursor",
            
            "زيد": "zed",
            "zed": "zed",
            
            "انتي جرافيتي": "antigravity",
            "انتيجرافيتي": "antigravity",
            "antigravity": "antigravity",
            
            "كلود": "claude",
            "claude": "claude",
            
            "دوكر": "docker desktop",
            "داكر": "docker desktop",
            "docker": "docker desktop",
            
            "وارب": "warp",
            "warp": "warp",
            
            "هيرمس": "hermes",
            "hermes": "hermes",
            
            "أولاما": "ollama",
            "اولاما": "ollama",
            "ollama": "ollama",
            
            "باكيت تريسر": "cisco packet tracer",
            "packet tracer": "cisco packet tracer",
            "excalidraw": "excalidraw",
            "اكسكاليدرو": "excalidraw",
            
            # برامج الميديا والتواصل
            "سبوتيفاي": "spotify",
            "سبوتفاي": "spotify",
            "spotify": "spotify",
            
            "ديسكورد": "discord",
            "دسكورد": "discord",
            "discord": "discord",
            
            "تيليجرام": "telegram",
            "تليجرام": "telegram",
            "telegram": "telegram",
            
            "واتساب": "whatsapp",
            "الواتس": "whatsapp",
            "whatsapp": "whatsapp",
            
            "كروم": "google chrome",
            "جوجل كروم": "google chrome",
            "chrome": "google chrome",
            
            "إيدج": "msedge",
            "ايدج": "msedge",
            "edge": "msedge",
            
            "زين": "zen",
            "zen": "zen",
            
            "ستيم": "steam",
            "steam": "steam",
            
            "اوبسيديان": "obsidian",
            "obsidian": "obsidian",
            
            "في ال سي": "vlc",
            "vlc": "vlc",
            
            "هولو نايت": "hollow knight",
            "hollow knight": "hollow knight",
            "سيلكسونج": "silksong",
            
            # أدوات الويندوز
            "الآلة الحاسبة": "calc",
            "الحاسبة": "calc",
            "حاسبة": "calc",
            "كالكوليتور": "calc",
            "calculator": "calc",
            "المفكرة": "notepad",
            "نوت باد": "notepad",
            "notepad": "notepad",
            "الرسام": "mspaint",
            "بينت": "mspaint",
            "paint": "mspaint",
            "الإعدادات": "ms-settings:",
            "الاعدادات": "ms-settings:",
            "settings": "ms-settings:",
            "الملفات": "explorer",
            "explorer": "explorer",
            "الأوامر": "cmd",
            "تيرمينال": "wt",
            "cmd": "cmd",
            "terminal": "wt",
            
            # أوفيس
            "وورد": "winword",
            "الورد": "winword",
            "word": "winword",
            "إكسيل": "excel",
            "اكسل": "excel",
            "excel": "excel",
            "باوربوينت": "powerpnt",
            "powerpoint": "powerpnt"
        }

        # بروتوكولات ومسارات مباشرة فورية
        self.direct_targets = {
            "spotify": "spotify:",
            "calc": "calc",
            "notepad": "notepad",
            "chrome": "chrome",
            "google chrome": "chrome",
            "msedge": "msedge",
            "mspaint": "mspaint",
            "explorer": "explorer",
            "cmd": "cmd",
            "wt": "wt",
            "winword": "winword",
            "excel": "excel",
            "powerpnt": "powerpnt",
            "ms-settings:": "ms-settings:",
            "discord": "discord:",
            "whatsapp": "whatsapp:",
            "telegram": "tg:",
            "steam": "steam:"
        }

    def _index_installed_apps(self):
        """فهرسة البرامج من قائمة Start وسطح المكتب ومجلدات البرامج المباشرة"""
        search_dirs = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
            Path("C:/Users/Public/Desktop")
        ]
        
        for base in search_dirs:
            if base.exists():
                for lnk in base.rglob("*.lnk"):
                    clean_name = lnk.stem.lower()
                    self.apps[clean_name] = str(lnk)

        # فحص مباشر لـ JetBrains IDEs في Program Files
        jb_path = Path("C:/Program Files/JetBrains")
        if jb_path.exists():
            for rider_exe in jb_path.rglob("rider64.exe"):
                self.apps["rider"] = str(rider_exe)
                self.apps["jetbrains rider"] = str(rider_exe)
            for pycharm_exe in jb_path.rglob("pycharm64.exe"):
                self.apps["pycharm"] = str(pycharm_exe)
            for idea_exe in jb_path.rglob("idea64.exe"):
                self.apps["intellij"] = str(idea_exe)

        # فحص مباشر لـ Visual Studio IDE في Program Files
        vs_path = Path("C:/Program Files/Microsoft Visual Studio")
        if vs_path.exists():
            for vs_exe in vs_path.rglob("devenv.exe"):
                self.apps["visual studio"] = str(vs_exe)
                self.apps["visual studio community"] = str(vs_exe)

    def _arabic_to_latin_phonetic(self, text: str) -> str:
        """تحويل الأصوات العربية إلى لاتينية"""
        mapping = {
            'أ': 'a', 'إ': 'e', 'آ': 'a', 'ا': 'a',
            'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'g',
            'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z',
            'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh',
            'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z',
            'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'k',
            'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
            'ه': 'h', 'و': 'o', 'ي': 'y', 'ى': 'a',
            'ة': 'a', 'ئ': 'e', 'ء': 'a', 'ؤ': 'o',
            'ڤ': 'v', 'پ': 'p'
        }
        res = []
        for c in text.lower():
            if c in mapping:
                res.append(mapping[c])
            elif c.isalnum() or c.isspace():
                res.append(c)
        out = ''.join(res)
        return re.sub(r'\s+', ' ', out).strip()

    def launch(self, query: str) -> tuple[bool, str]:
        """تشغيل التطبيق الذكي بدقة 100%"""
        q = query.lower().strip()
        q = re.sub(r'^(افتح|شغل|ابحث عن|open|launch|run|start)\s+', '', q).strip()

        # 1. فحص القاموس المعرب
        target_name = self.arabic_alias_map.get(q, q)

        # 2. Check direct protocols
        if target_name in self.direct_targets:
            cmd = self.direct_targets[target_name]
            try:
                subprocess.Popen(f'start "" "{cmd}"', shell=True)
                return True, f"Launched {q} instantly."
            except Exception:
                pass

        # 3. Check indexed apps in Windows and Program Files
        for name, path in self.apps.items():
            if target_name == name or target_name in name or name in target_name:
                try:
                    os.startfile(path)
                    return True, f"Opened {name} successfully."
                except Exception:
                    pass

        # 4. Phonetic Latin matching
        phonetic_latin = self._arabic_to_latin_phonetic(q)
        for name, path in self.apps.items():
            if phonetic_latin in name or name in phonetic_latin:
                try:
                    os.startfile(path)
                    return True, f"Opened {name}."
                except Exception:
                    pass

        # 5. Fuzzy Matching
        matches = difflib.get_close_matches(target_name, self.apps.keys(), n=1, cutoff=0.35)
        if not matches:
            matches = difflib.get_close_matches(phonetic_latin, self.apps.keys(), n=1, cutoff=0.35)

        if matches:
            best_match = matches[0]
            try:
                os.startfile(self.apps[best_match])
                return True, f"Opened {best_match}."
            except Exception:
                pass

        # 6. ASCII command fallback
        if target_name.isascii() and not any(ord(c) > 127 for c in target_name):
            try:
                subprocess.Popen(f'start "" "{target_name}"', shell=True)
                return True, f"Executed command '{target_name}'."
            except Exception:
                pass

        return False, f"Could not find application '{query}'."
