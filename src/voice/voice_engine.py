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
        self.recognizer.energy_threshold = 280
        self.recognizer.dynamic_energy_threshold = True
        # Natural speech boundary thresholds (allows comfortable pauses without cutting off)
        self.recognizer.pause_threshold = 1.1
        self.recognizer.non_speaking_duration = 0.5
        self.is_listening = False
        self.stop_listening_fn = None
        self.command_queue = queue.Queue()

    def listen_command(self, timeout: int = 10, phrase_time_limit: int = 25) -> str:
        try:
            with sr.Microphone() as source:
                self.is_listening = True
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                try:
                    text = self.recognizer.recognize_google(audio, language=self.language)
                except sr.UnknownValueError:
                    # Fallback to English if Arabic recognition didn't capture the phrase
                    text = self.recognizer.recognize_google(audio, language="en-US")
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
                text = ""
                try:
                    text = recognizer.recognize_google(audio, language=self.language)
                except sr.UnknownValueError:
                    try:
                        text = recognizer.recognize_google(audio, language="en-US")
                    except Exception:
                        pass
                except Exception:
                    pass

                if text and len(text.strip().split()) >= 1:
                    if on_partial_callback:
                        on_partial_callback(text.strip())

            self.stop_listening_fn = self.recognizer.listen_in_background(
                mic, 
                _audio_callback, 
                phrase_time_limit=25
            )
            self.is_listening = True
        except Exception as e:
            print(f"❌ Error starting speech listener: {e}")

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
                import asyncio
                import io
                audio_buffer = io.BytesIO()

                async def _gen():
                    communicate = edge_tts.Communicate(text, TTS_VOICE)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])

                asyncio.run(_gen())
                audio_buffer.seek(0)

                if audio_buffer.getbuffer().nbytes > 0:
                    try:
                        pygame.mixer.music.load(audio_buffer)
                        pygame.mixer.music.play()
                        if block:
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                        return
                    except Exception:
                        pass

                # Fallback to temp file if buffer loading fails on older systems
                output_file = str(TEMP_DIR / f"tts_{os.getpid()}_{int(time.time())}.mp3")
                with open(output_file, "wb") as f:
                    f.write(audio_buffer.getvalue())
                if os.path.exists(output_file):
                    pygame.mixer.music.load(output_file)
                    pygame.mixer.music.play()
                    if block:
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
            except Exception:
                pass

        threading.Thread(target=_run_tts, daemon=True).start()
