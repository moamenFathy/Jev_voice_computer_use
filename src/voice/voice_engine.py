import os
import time
import threading
import queue
import speech_recognition as sr
from src.config import VOICE_LANGUAGE, TTS_VOICE, TTS_ENABLED, TEMP_DIR

try:
    import edge_tts
    import pygame
    pygame.mixer.init()
    EDGE_TTS_AVAILABLE = True
except Exception as e:
    EDGE_TTS_AVAILABLE = False

class VoiceEngine:
    def __init__(self, language: str = VOICE_LANGUAGE):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.4  # مهلة مريحة لعدم مقاطعة الكلام
        self.recognizer.non_speaking_duration = 0.8
        self.is_listening = False
        self.stop_listening_fn = None
        self.command_queue = queue.Queue()

    def listen_command(self, timeout: int = 8, phrase_time_limit: int = 15) -> str:
        try:
            with sr.Microphone() as source:
                self.is_listening = True
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text.strip()
        except Exception:
            return ""
        finally:
            self.is_listening = False

    def start_streaming_listen(self, on_partial_callback=None):
        try:
            mic = sr.Microphone()
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)

            def _audio_callback(recognizer, audio):
                try:
                    text = recognizer.recognize_google(audio, language=self.language)
                    if text and len(text.strip().split()) >= 1:
                        if on_partial_callback:
                            on_partial_callback(text.strip())
                except sr.UnknownValueError:
                    pass
                except Exception:
                    pass

            self.stop_listening_fn = self.recognizer.listen_in_background(
                mic, 
                _audio_callback, 
                phrase_time_limit=15
            )
            self.is_listening = True
        except Exception as e:
            print(f"❌ خطأ في بدء الاستماع: {e}")

    def stop_streaming_listen(self):
        if self.stop_listening_fn:
            self.stop_listening_fn(wait_for_stop=False)
            self.stop_listening_fn = None
        self.is_listening = False

    def speak(self, text: str, block: bool = False):
        if not TTS_ENABLED or not EDGE_TTS_AVAILABLE or not text.strip():
            return

        def _run_tts():
            try:
                output_file = str(TEMP_DIR / f"tts_{os.getpid()}_{int(time.time())}.mp3")
                import asyncio
                async def _gen():
                    communicate = edge_tts.Communicate(text, TTS_VOICE)
                    await communicate.save(output_file)
                asyncio.run(_gen())

                if os.path.exists(output_file):
                    pygame.mixer.music.load(output_file)
                    pygame.mixer.music.play()
                    if block:
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
            except Exception:
                pass

        threading.Thread(target=_run_tts, daemon=True).start()
