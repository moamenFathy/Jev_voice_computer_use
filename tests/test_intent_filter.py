"""
Unit Tests for Intent & False-Trigger Filter.
Validates ambient noise rejection, conversational filler filtering, and wake word validation.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.voice.intent_filter import is_valid_voice_command, is_incomplete_utterance


class TestIntentFilter(unittest.TestCase):
    def test_rejects_empty_and_noise_tokens(self):
        self.assertFalse(is_valid_voice_command("")[0])
        self.assertFalse(is_valid_voice_command("   ")[0])
        self.assertFalse(is_valid_voice_command("a")[0])
        self.assertFalse(is_valid_voice_command("اه")[0])
        self.assertFalse(is_valid_voice_command("امم")[0])
        self.assertFalse(is_valid_voice_command("uh")[0])
        self.assertFalse(is_valid_voice_command("okay")[0])

    def test_incomplete_utterance_detection(self):
        # Dangling connectives and verbs
        self.assertTrue(is_incomplete_utterance("افتح المفكرة واكتب"))
        self.assertTrue(is_incomplete_utterance("افتح المفكرة و"))
        self.assertTrue(is_incomplete_utterance("افتح المفكرة وبعدين"))
        self.assertTrue(is_incomplete_utterance("ابحث في جوجل عن"))
        self.assertTrue(is_incomplete_utterance("شغل اغنية في"))
        self.assertTrue(is_incomplete_utterance("open notepad and"))
        self.assertTrue(is_incomplete_utterance("type"))

        # Complete thoughts
        self.assertFalse(is_incomplete_utterance("افتح المفكرة واكتب تقرير الاجتماع"))
        self.assertFalse(is_incomplete_utterance("افتح المفكرة"))
        self.assertFalse(is_incomplete_utterance("شغل عمرو دياب في سبوتيفاي"))
        self.assertFalse(is_incomplete_utterance("احفظ الملف"))
        self.assertFalse(is_incomplete_utterance("open notepad and write hello world"))

    def test_accepts_valid_single_word_commands(self):
        valid_words = ["وقف", "شغل", "كمل", "التالي", "السابق", "احفظ", "انسخ", "الصق", "ميوت", "اقفل", "pause", "resume", "next", "save"]
        for word in valid_words:
            is_valid, clean = is_valid_voice_command(word, streaming_mode=True)
            self.assertTrue(is_valid, f"Expected '{word}' to be valid in streaming mode")
            self.assertEqual(clean, word)

    def test_accepts_direct_app_names_in_streaming(self):
        self.assertTrue(is_valid_voice_command("المفكرة", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("رايدر", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("notepad", streaming_mode=True)[0])

    def test_rejects_unprompted_conversational_chatter_in_streaming(self):
        # Conversational chatter without actionable verbs should be rejected in streaming
        self.assertFalse(is_valid_voice_command("الجو حر النهاردة في الشارع", streaming_mode=True)[0])
        self.assertFalse(is_valid_voice_command("ازيك عامل ايه يا صاحبي", streaming_mode=True)[0])
        self.assertFalse(is_valid_voice_command("good morning everyone", streaming_mode=True)[0])

    def test_accepts_actionable_commands_in_streaming(self):
        self.assertTrue(is_valid_voice_command("افتح المفكرة", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("شغل اغنية عمرو دياب في يوتيوب ميوزك", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("اكتب تقرير اليوم", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("دوس على زرار حفظ", streaming_mode=True)[0])
        self.assertTrue(is_valid_voice_command("خش على موقع github.com", streaming_mode=True)[0])

    def test_wake_word_parsing(self):
        # With wake word "جيف"
        is_val, clean = is_valid_voice_command("يا جيف افتح المفكرة", streaming_mode=True, wake_word="جيف")
        self.assertTrue(is_val)
        self.assertEqual(clean, "افتح المفكرة")

        is_val, clean = is_valid_voice_command("Jev open notepad", streaming_mode=True, wake_word="jev")
        self.assertTrue(is_val)
        self.assertEqual(clean, "open notepad")

        # Without wake word when wake word is mandatory -> Reject
        is_val, _ = is_valid_voice_command("افتح المفكرة", streaming_mode=True, wake_word="جيف")
        self.assertFalse(is_val)


if __name__ == "__main__":
    unittest.main()
