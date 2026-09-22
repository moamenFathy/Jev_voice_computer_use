"""
Intent & False-Trigger Filter for JEV Voice Engine.
Protects the OS automation engine from ambient background speech, acoustic noise,
and unprompted chatter in hands-free streaming mode.
"""

import re
from typing import Tuple, Optional, Set

# Standalone single-word commands that are strictly valid
VALID_SINGLE_WORD_COMMANDS: Set[str] = {
    # Media controls
    "وقف", "ايقاف", "إيقاف", "شغل", "كمل", "استئناف", "التالي", "التالية", "السابق", "السابقة",
    "نكست", "بريفيوس", "pause", "resume", "play", "stop", "next", "prev", "previous", "back",
    # System & shortcuts
    "احفظ", "سيف", "انسخ", "كوبي", "الصق", "بيست", "حدد", "ميوت", "اكتم", "اقفل", "قفل",
    "save", "copy", "paste", "mute", "close", "minimize",
}

# Conversational fillers and noise words that should be rejected if alone
COMMON_CONVERSATIONAL_FILLERS: Set[str] = {
    "اه", "اها", "امم", "اممم", "اوكي", "اوكيه", "ايوة", "ايوه", "لا", "نعم", "الو", "ألو",
    "تمام", "ماشى", "ماشي", "طيب", "شكرا", "شكراً", "سلام", "مع السلامة", "صباح الخير", "مساء الخير",
    "uh", "um", "umm", "yeah", "yes", "no", "okay", "ok", "hey", "hello", "hi", "thanks", "bye",
}

# Recognized action triggers and prefixes in Arabic & English
ACTION_TRIGGERS: Tuple[str, ...] = (
    # Apps & Launch
    "افتح", "شغل", "launch", "open", "run", "start",
    # Typing & Input
    "اكتب", "type", "write", "input",
    # Clicks & UI
    "دوس", "اضغط", "انقر", "click", "press", "tap",
    # Web & Navigation
    "روح", "خش", "ادخل", "go to", "visit", "browse",
    # Search
    "سيرش", "ابحث", "دور", "search", "find", "lookup",
    # Window & System
    "اقفل", "اغلق", "قفل", "close", "minimize", "احفظ", "save", "علي", "ارفع", "وطي", "اخفض", "اكتم", "ميوت",
    "volume up", "volume down", "mute", "unmute",
    # Math
    "احسب", "calculate", "calc", "compute",
    # Media controls
    "التالي", "السابق", "next", "prev", "pause", "resume",
)

# Known app names that can trigger direct launches even without the verb "افتح"
KNOWN_DIRECT_APPS: Set[str] = {
    "المفكرة", "المفكره", "نوت باد", "نوت باده", "الحاسبة", "الحاسبه", "الآلة الحاسبة", "كالكوليتور",
    "الرسام", "بينت", "رايدر", "جيت برينز رايدر", "في اس كود", "فيجوال ستوديو", "كود",
    "سبوتيفاي", "سبوتفاي", "ديسكورد", "تيليجرام", "تليجرام", "واتساب", "كروم", "جوجل كروم", "ايدج",
    "انتي جرافيتي", "كلود", "دوكر", "وارب", "ستيم", "اوبسيديان", "notepad", "calc", "calculator",
    "rider", "code", "vscode", "visual studio", "spotify", "discord", "telegram", "whatsapp", "chrome",
    "claude", "cursor", "zed", "docker", "warp", "steam", "obsidian",
}


# Trailing connectives and incomplete conjunctions that signal a multi-part thought in progress
INCOMPLETE_TRAILING_TOKENS: Set[str] = {
    # Conjunctions & Connectors
    "و", "وبعدين", "وبعدها", "ثم", "وبعد ذلك", "علشان", "عشان", "and", "then", "and then",
    # Dangling prepositions
    "في", "على", "علي", "عن", "من", "لـ", "مع", "بتاع", "بتاعة", "بتاعت", "in", "on", "at", "for", "to", "with", "about",
    # Dangling imperative action verbs at the end of phrase
    "واكتب", "ودوس", "وانقر", "واضغط", "وافتح", "وشغل", "واحفظ", "واقفل", "وسيرش", "وابحث", "ودور",
    "اكتب", "type", "write", "دوس", "اضغط", "انقر", "click", "ابحث", "سيرش", "search",
}


def is_incomplete_utterance(text: str) -> bool:
    """
    Checks if a transcribed phrase is a partial or incomplete thought that should NOT
    be dispatched immediately, allowing the user to complete their multi-step sentence naturally.
    """
    if not text:
        return True

    norm = re.sub(r'[\u064B-\u0652]', '', text)
    norm = re.sub(r'[.,!؟?؛;]', '', norm).strip().lower()
    tokens = norm.split()
    if not tokens:
        return True

    last_token = tokens[-1]

    # 1. Ends with a dangling connective or hanging verb
    if last_token in INCOMPLETE_TRAILING_TOKENS:
        return True

    # 2. Check 2-word dangling endings (e.g. 'and then', 'ابحث عن', 'سيرش على')
    if len(tokens) >= 2:
        last_two = f"{tokens[-2]} {tokens[-1]}"
        if last_two in ("and then", "ابحث عن", "سيرش على", "سيرش في", "ابحث في", "دور على", "خش على", "ادخل على", "روح لـ", "روح ل"):
            return True

    # 3. Solitary action verbs with missing arguments (e.g. 'اكتب', 'type', 'ابحث')
    if len(tokens) == 1 and tokens[0] in ("اكتب", "type", "write", "ابحث", "سيرش", "search"):
        return True

    return False


def is_valid_voice_command(
    raw_text: str,
    streaming_mode: bool = False,
    wake_word: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validates whether transcribed audio represents a genuine, actionable voice command.
    Filters out background noise, non-actionable chatter, and unsupported single tokens.

    Returns:
        (is_valid: bool, cleaned_text: str)
    """
    if not raw_text:
        return False, ""

    text = raw_text.strip()
    norm = re.sub(r'[\u064B-\u0652]', '', text)  # remove tashkeel
    norm = re.sub(r'[.,!؟?؛;]', '', norm).strip().lower()

    if not norm or len(norm) < 2:
        return False, ""

    # 1. Check Wake Word (if configured and in streaming mode)
    if wake_word and streaming_mode:
        norm_wake = wake_word.strip().lower()
        wake_pattern = rf'^(?:يا\s*)?{re.escape(norm_wake)}\s*(?:،|,)?\s*(.*)$'
        m = re.match(wake_pattern, norm, flags=re.IGNORECASE)
        if m:
            remainder = m.group(1).strip()
            if remainder:
                return is_valid_voice_command(remainder, streaming_mode=False, wake_word=None)
            return False, ""
        # If wake word is mandatory but absent, reject ambient speech
        return False, ""

    tokens = norm.split()

    # 2. Single token checks
    if len(tokens) == 1:
        single = tokens[0]
        # Reject conversational fillers
        if single in COMMON_CONVERSATIONAL_FILLERS:
            return False, ""
        # Accept explicit single-word commands or direct app names
        if single in VALID_SINGLE_WORD_COMMANDS or single in KNOWN_DIRECT_APPS:
            return True, text
        # If in streaming hands-free mode, reject random unprompted single words (< 4 chars)
        if streaming_mode and len(single) < 4:
            return False, ""

    # 3. Check for Conversational Filler Discard
    if norm in COMMON_CONVERSATIONAL_FILLERS:
        return False, ""

    # 4. In Streaming (Hands-free) mode: require actionable intent grammar
    if streaming_mode:
        starts_with_action = any(
            norm.startswith(act + " ") or norm == act
            for act in ACTION_TRIGGERS
        )
        matches_direct_app = any(
            norm.startswith(app) or app in tokens
            for app in KNOWN_DIRECT_APPS
        )
        is_registered_shortcut = norm in VALID_SINGLE_WORD_COMMANDS

        if not (starts_with_action or matches_direct_app or is_registered_shortcut):
            # Text was conversational chatter without actionable intent
            return False, ""

    return True, text
