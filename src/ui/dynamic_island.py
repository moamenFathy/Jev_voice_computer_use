import tkinter as tk
from tkinter import ttk
import threading
import time
import math
from src.core.os_controller import OSController
from src.voice.voice_engine import VoiceEngine
from src.decision.jev_engine import JevDecisionEngine


class DynamicIslandUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jev Voice Assistant - Dynamic Island")
        
        screen_w = self.root.winfo_screenwidth()
        pill_w = 620
        pill_h = 135
        pos_x = int((screen_w - pill_w) / 2)
        pos_y = 35

        self.root.geometry(f"{pill_w}x{pill_h}+{pos_x}+{pos_y}")
        self.root.attributes('-topmost', True)
        self.root.configure(bg="#0c0d11")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.95)

        # Engine Initializations
        self.controller = OSController()
        self.voice = VoiceEngine()
        self.agent = JevDecisionEngine(self.controller)
        
        self.is_streaming = False
        self.is_busy = False
        self.wave_phase = 0
        self.current_state = "idle"

        # Drag & Move bindings
        self.root.bind("<ButtonPress-1>", self._start_move)
        self.root.bind("<ButtonRelease-1>", self._stop_move)
        self.root.bind("<B1-Motion>", self._do_move)
        self.root.bind("<Escape>", lambda e: self.on_emergency_stop())

        self._build_ui()
        self._animate_visualizer()

    def _start_move(self, event):
        self.x = event.x
        self.y = event.y

    def _stop_move(self, event):
        self.x = None
        self.y = None

    def _do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg="#12131a", highlightthickness=2, highlightbackground="#00f0ff")
        self.main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        top_bar = tk.Frame(self.main_frame, bg="#12131a")
        top_bar.pack(fill="x", padx=15, pady=(6, 2))

        brand_lbl = tk.Label(
            top_bar,
            text="⚡ JEV SYSTEM ONE | DYNAMIC ISLAND",
            font=("Segoe UI", 9, "bold"),
            fg="#00f0ff",
            bg="#12131a"
        )
        brand_lbl.pack(side="left")

        close_btn = tk.Button(
            top_bar,
            text="✕",
            font=("Segoe UI", 9, "bold"),
            fg="#777788",
            bg="#12131a",
            activeforeground="#ff4d6d",
            activebackground="#12131a",
            relief="flat",
            cursor="hand2",
            command=self.root.destroy
        )
        close_btn.pack(side="right", padx=(5, 0))

        self.mode_btn = tk.Button(
            top_bar,
            text="🔴 Enable Streaming (Hands-free)",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg="#242735",
            activebackground="#33384a",
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.toggle_streaming
        )
        self.mode_btn.pack(side="right", padx=5)

        mid_frame = tk.Frame(self.main_frame, bg="#12131a")
        mid_frame.pack(fill="x", padx=15, pady=2)

        self.canvas = tk.Canvas(mid_frame, width=60, height=45, bg="#12131a", highlightthickness=0)
        self.canvas.pack(side="left", padx=(0, 10))

        text_frame = tk.Frame(mid_frame, bg="#12131a")
        text_frame.pack(side="left", fill="both", expand=True)

        self.status_lbl = tk.Label(
            text_frame,
            text="Ready... Speak in Arabic or English",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#12131a",
            anchor="w",
            justify="left"
        )
        self.status_lbl.pack(fill="x")

        self.sub_lbl = tk.Label(
            text_frame,
            text="⚡ Jev Decision Engine (Sub-second Latency)",
            font=("Segoe UI", 9),
            fg="#8888aa",
            bg="#12131a",
            anchor="w",
            justify="left"
        )
        self.sub_lbl.pack(fill="x")

        self.mic_btn = tk.Button(
            mid_frame,
            text="🎙️",
            font=("Segoe UI", 14),
            fg="#ffffff",
            bg="#007acc",
            activebackground="#005999",
            relief="flat",
            width=3,
            height=1,
            cursor="hand2",
            command=self.on_mic_click
        )
        self.mic_btn.pack(side="right", padx=(5, 0))

    def _animate_visualizer(self):
        self.canvas.delete("all")
        self.wave_phase += 0.25

        bars = 5
        bar_w = 4
        spacing = 4
        canvas_h = 35
        mid_y = canvas_h / 2

        color_map = {
            "idle": "#00f0ff",
            "listening": "#ff0055",
            "deciding": "#ffb703",
            "executing": "#00ff88",
            "error": "#ff4d6d",
            "stopped": "#ff4d6d"
        }
        bar_color = color_map.get(self.current_state, "#00f0ff")

        for i in range(bars):
            x = 10 + i * (bar_w + spacing)
            if self.current_state in ["listening", "executing"]:
                amplitude = 12 * abs(math.sin(self.wave_phase + i * 0.8)) + 3
            else:
                amplitude = 4 * abs(math.sin(self.wave_phase * 0.5 + i * 0.5)) + 2

            y1 = mid_y - amplitude
            y2 = mid_y + amplitude
            self.canvas.create_line(x, y1, x, y2, fill=bar_color, width=bar_w, capstyle=tk.ROUND)

        self.root.after(50, self._animate_visualizer)

    def set_state(self, state: str, main_text: str, sub_text: str = ""):
        """Thread-safe UI state updater using root.after."""
        def _update():
            self.current_state = state
            self.status_lbl.config(text=main_text)
            if sub_text:
                self.sub_lbl.config(text=sub_text)

            glow_colors = {
                "idle": "#00f0ff",
                "listening": "#ff0055",
                "deciding": "#ffb703",
                "executing": "#00ff88",
                "error": "#ff4d6d",
                "stopped": "#ff4d6d"
            }
            glow = glow_colors.get(state, "#00f0ff")
            self.main_frame.config(highlightbackground=glow)

            if state == "listening":
                self.mic_btn.config(bg="#ff0055", text="🔴")
            elif state == "executing":
                self.mic_btn.config(bg="#00ff88", text="⚡")
            else:
                self.mic_btn.config(bg="#007acc", text="🎙️")

        self.root.after(0, _update)

    def toggle_streaming(self):
        if not self.is_streaming:
            self.is_streaming = True
            self.mode_btn.config(text="🟢 Streaming Active (Speak freely)", bg="#00805a")
            self.set_state("listening", "🎙️ Listening... Speak your command", "Continuous hands-free listening active")
            self.voice.start_streaming_listen(on_partial_callback=self._on_live_speech_chunk)
        else:
            self.is_streaming = False
            self.voice.stop_streaming_listen()
            self.mode_btn.config(text="🔴 Enable Streaming (Hands-free)", bg="#242735")
            self.set_state("idle", "Ready... Click mic or enable streaming", "⚡ Jev Decision Engine (Ready)")

    def _on_live_speech_chunk(self, recognized_text: str):
        if not recognized_text or self.is_busy:
            return
        threading.Thread(target=lambda: self._run_jev_action(recognized_text), daemon=True).start()

    def on_mic_click(self):
        if self.is_busy:
            return

        def _worker():
            self.is_busy = True
            try:
                self.set_state("listening", "🎙️ Listening... Speak freely", "Listening for voice command...")
                text = self.voice.listen_command(timeout=8, phrase_time_limit=15)
                if text:
                    self._run_jev_action(text)
                else:
                    self.set_state("idle", "No speech detected. Click 🎙️ to try again.", "Ready")
            except Exception as e:
                print(f"[DynamicIsland] Mic listener error: {e}")
                self.set_state("idle", "Ready... Speak in Arabic or English", "Ready")
            finally:
                self.is_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _run_jev_action(self, command: str):
        self.is_busy = True
        try:
            self.set_state("deciding", f"🧠 Processing: '{command}'", "⚡ Jev Decision Engine...")

            def on_callback(event_type, msg):
                if event_type == "action":
                    self.set_state("executing", f"⚡ {msg}", "Executing...")
                elif event_type == "thought":
                    self.root.after(0, lambda: self.sub_lbl.config(text=msg))
                elif event_type == "status":
                    self.set_state("executing", msg, "Executing...")
                elif event_type == "error":
                    self.set_state("error", f"❌ {msg}", "Error encountered")

            import uiautomation as auto
            with auto.UIAutomationInitializerInThread():
                result = self.agent.execute_goal(command, on_step_callback=on_callback)

            result_str = str(result)
            is_success = getattr(result, "success", True)

            if is_success:
                self.set_state("executing", f"✅ {result_str}", "Completed successfully!")
            else:
                self.set_state("error", f"❌ {result_str}", "Operation failed")

            self.voice.speak(result_str)
            time.sleep(1.5)

        except Exception as e:
            print(f"[DynamicIsland] Error during execution: {e}")
            self.set_state("error", f"❌ Error: {e}", "Execution error")
            time.sleep(1.5)
        finally:
            self.is_busy = False
            if self.is_streaming:
                self.set_state("listening", "🎙️ Ready for next command...", "Streaming active")
            else:
                self.set_state("idle", "Ready... Speak in Arabic or English", "⚡ Jev Decision Engine (Ready)")

    def on_emergency_stop(self):
        self.controller.emergency_stop()
        self.set_state("stopped", "🛑 Emergency Stop Activated!", "Stopped by user")
        self.is_busy = False


def launch_dynamic_island():
    root = tk.Tk()
    app = DynamicIslandUI(root)
    root.mainloop()
