"""
Jarvis AI Assistant — Desktop GUI
Sleek, animated UI with face visualization, chat log, text input, and settings.
Based on Mark-X.1 by FatihMakes, enhanced for OpenRouter AI.
"""
import os
import json
import time
import random
import math
import tkinter as tk
from collections import deque
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from tkinter.scrolledtext import ScrolledText
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    CONFIG_DIR, ASSETS_DIR, FACE_IMAGE_PATH,
    UI_WINDOW_SIZE, FACE_IMAGE_SIZE, ASSISTANT_NAME
)

API_FILE = CONFIG_DIR / "api_keys.json"


class JarvisUI:
    """
    Main GUI window for the Jarvis assistant.
    Features: animated face, chat log, text input, setup wizard, speaking indicator.
    """

    def __init__(self, face_path=None, size=None):
        self.root = tk.Tk()
        self.root.title(f"{ASSISTANT_NAME} AI Assistant")
        self.root.resizable(False, False)
        self.root.geometry(f"{UI_WINDOW_SIZE[0]}x{UI_WINDOW_SIZE[1]}")
        self.root.configure(bg="#000000")

        # Try to set icon
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.size = size or FACE_IMAGE_SIZE
        self.center_y = 0.38

        # Track whether API keys have been saved
        self.api_keys_ready = self._api_keys_exist()

        # Callbacks (set by main.py)
        self.on_text_input = None
        self.on_mic_toggle = None

        # Mic state
        self.mic_active = False

        # ── Canvas for face animation ────────────────────────
        self.canvas = tk.Canvas(
            self.root,
            width=self.size[0],
            height=self.size[1],
            bg="#000000",
            highlightthickness=0
        )
        self.canvas.place(relx=0.5, rely=self.center_y, anchor="center")

        # ── Load face image ──────────────────────────────────
        face_file = face_path
        if face_file and Path(face_file).exists():
            self.face_base = (
                Image.open(face_file)
                .convert("RGBA")
                .resize(self.size, Image.LANCZOS)
            )
        else:
            self.face_base = self._create_placeholder_face()

        # ── Halo effect ──────────────────────────────────────
        self.halo_base = self._create_halo(self.size, radius=220, y_offset=-50)

        # ── Animation state ──────────────────────────────────
        self.speaking = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.halo_alpha = 70
        self.target_halo_alpha = 70
        self.last_target_time = time.time()

        # ── Chat log ─────────────────────────────────────────
        self.text_box = ScrolledText(
            self.root,
            fg="#8ffcff",
            bg="#000000",
            insertbackground="#8ffcff",
            height=8,
            borderwidth=0,
            wrap="word",
            font=("Consolas", 10),
            padx=12,
            pady=8
        )
        self.text_box.place(relx=0.5, rely=0.78, anchor="center",
                           relwidth=0.95)
        self.text_box.configure(state="disabled")

        # ── Bottom bar: text input + mic + send ──────────────
        input_frame = tk.Frame(self.root, bg="#000000")
        input_frame.place(relx=0.5, rely=0.95, anchor="center", relwidth=0.95)

        # Mic toggle button
        self.mic_btn = tk.Button(
            input_frame,
            text="🎙 OFF",
            command=self._toggle_mic,
            bg="#1a0000",
            fg="#ff4444",
            activebackground="#330000",
            activeforeground="#ff6666",
            font=("Consolas", 10, "bold"),
            borderwidth=0,
            padx=10,
            pady=4,
            cursor="hand2"
        )
        self.mic_btn.pack(side="left", padx=(0, 6))

        # Text entry
        self.text_input = tk.Entry(
            input_frame,
            fg="#8ffcff",
            bg="#0a0a0a",
            insertbackground="#8ffcff",
            borderwidth=1,
            relief="solid",
            font=("Consolas", 11),
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.text_input.bind("<Return>", self._on_enter)

        # Send button
        send_btn = tk.Button(
            input_frame,
            text="SEND",
            command=self._on_send,
            bg="#001a2e",
            fg="#8ffcff",
            activebackground="#003344",
            activeforeground="#ffffff",
            font=("Consolas", 10, "bold"),
            borderwidth=0,
            padx=12,
            pady=4,
            cursor="hand2"
        )
        send_btn.pack(side="right")

        # Placeholder text
        self.text_input.insert(0, "Type a command or speak...")
        self.text_input.config(fg="#555555")
        self.text_input.bind("<FocusIn>", self._clear_placeholder)
        self.text_input.bind("<FocusOut>", self._add_placeholder)

        # ── Typing animation queue ───────────────────────────
        self.typing_queue = deque()
        self.is_typing = False

        # ── Status label ─────────────────────────────────────
        self.status_label = tk.Label(
            self.root,
            text="● STANDBY",
            fg="#4a9eff",
            bg="#000000",
            font=("Consolas", 9, "bold")
        )
        self.status_label.place(relx=0.5, rely=0.01, anchor="n")

        # ── Show setup if no API keys ────────────────────────
        if not self.api_keys_ready:
            self._show_setup_ui()

        # ── Start animation loop ─────────────────────────────
        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # ══════════════════════════════════════════════════════════
    #  TEXT INPUT HANDLING
    # ══════════════════════════════════════════════════════════

    def _clear_placeholder(self, event):
        if self.text_input.get() == "Type a command or speak...":
            self.text_input.delete(0, tk.END)
            self.text_input.config(fg="#8ffcff")

    def _add_placeholder(self, event):
        if not self.text_input.get():
            self.text_input.insert(0, "Type a command or speak...")
            self.text_input.config(fg="#555555")

    def _toggle_mic(self):
        """Toggle microphone on/off."""
        if self.mic_active:
            self.set_mic_active(False)
        else:
            self.set_mic_active(True)

        if self.on_mic_toggle:
            self.on_mic_toggle(self.mic_active)

    def set_mic_active(self, active: bool):
        """Update mic button appearance."""
        self.mic_active = active
        try:
            if active:
                self.mic_btn.configure(
                    text="🎙 ON",
                    bg="#001a00",
                    fg="#00ff88",
                    activebackground="#003300",
                    activeforeground="#00ff88"
                )
            else:
                self.mic_btn.configure(
                    text="🎙 OFF",
                    bg="#1a0000",
                    fg="#ff4444",
                    activebackground="#330000",
                    activeforeground="#ff6666"
                )
        except Exception:
            pass

    def _on_enter(self, event):
        self._on_send()

    def _on_send(self):
        text = self.text_input.get().strip()
        if not text or text == "Type a command or speak...":
            return

        self.text_input.delete(0, tk.END)

        # Call the handler set by main.py
        if self.on_text_input:
            self.on_text_input(text)

    # ══════════════════════════════════════════════════════════
    #  PLACEHOLDER FACE
    # ══════════════════════════════════════════════════════════

    def _create_placeholder_face(self):
        w, h = self.size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2

        r = min(w, h) // 2 - 60
        for i in range(0, 360, 2):
            angle = math.radians(i)
            alpha = int(100 + 50 * abs(math.sin(angle * 3)))
            x1 = cx + int((r - 2) * math.cos(angle))
            y1 = cy + int((r - 2) * math.sin(angle))
            x2 = cx + int((r + 2) * math.cos(angle))
            y2 = cy + int((r + 2) * math.sin(angle))
            draw.line([(x1, y1), (x2, y2)], fill=(0, 180, 255, alpha), width=2)

        r2 = r - 80
        draw.ellipse(
            [cx - r2, cy - r2, cx + r2, cy + r2],
            outline=(0, 200, 255, 150), width=2
        )

        r3 = 20
        for ring in range(r3, 0, -2):
            a = int(200 * (1 - ring / r3))
            draw.ellipse(
                [cx - ring, cy - ring, cx + ring, cy + ring],
                fill=(0, 220, 255, a)
            )

        for offset in [-60, 60]:
            draw.line(
                [(cx + offset - 35, cy - 30), (cx + offset + 35, cy - 30)],
                fill=(0, 220, 255, 200), width=3
            )
            draw.line(
                [(cx + offset - 25, cy - 20), (cx + offset + 25, cy - 20)],
                fill=(0, 180, 255, 120), width=2
            )

        return img

    # ══════════════════════════════════════════════════════════
    #  HALO EFFECT
    # ══════════════════════════════════════════════════════════

    def _create_halo(self, size, radius=220, y_offset=-50):
        w, h = size
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(halo)

        cx = w // 2
        cy = h // 2 + y_offset

        for r in range(radius, 0, -12):
            alpha = int(70 * (1 - r / radius))
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                fill=(0, 180, 255, alpha)
            )

        return halo.filter(ImageFilter.GaussianBlur(30))

    # ══════════════════════════════════════════════════════════
    #  ANIMATION LOOP
    # ══════════════════════════════════════════════════════════

    def _animate(self):
        now = time.time()

        if now - self.last_target_time > (0.25 if self.speaking else 0.7):
            if self.speaking:
                self.target_scale = random.uniform(1.02, 1.1)
                self.target_halo_alpha = random.randint(120, 150)
            else:
                self.target_scale = random.uniform(1.004, 1.012)
                self.target_halo_alpha = random.randint(60, 80)

            self.last_target_time = now

        scale_speed = 0.45 if self.speaking else 0.25
        halo_speed = 0.40 if self.speaking else 0.25

        self.scale += (self.target_scale - self.scale) * scale_speed
        self.halo_alpha += (self.target_halo_alpha - self.halo_alpha) * halo_speed

        w, h = self.size
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 255))

        halo = self.halo_base.copy()
        halo.putalpha(int(max(0, min(255, self.halo_alpha))))
        frame.alpha_composite(halo)

        face = self.face_base.resize(
            (int(w * self.scale), int(h * self.scale)),
            Image.LANCZOS
        )
        fx = (w - face.size[0]) // 2
        fy = (h - face.size[1]) // 2
        frame.alpha_composite(face, (fx, fy))

        img = ImageTk.PhotoImage(frame)
        self.canvas.delete("all")
        self.canvas.create_image(w // 2, h // 2, image=img)
        self.canvas.image = img

        self.root.after(16, self._animate)

    # ══════════════════════════════════════════════════════════
    #  SPEAKING STATE
    # ══════════════════════════════════════════════════════════

    def start_speaking(self):
        self.speaking = True
        self._update_status("● SPEAKING", "#00ff88")

    def stop_speaking(self):
        self.speaking = False
        self._update_status("● LISTENING", "#ffa500")

    def set_standby(self):
        self._update_status("● STANDBY", "#4a9eff")

    def set_listening(self):
        self._update_status("● LISTENING", "#ffa500")

    def set_processing(self):
        self._update_status("● PROCESSING", "#ff4488")

    def _update_status(self, text, color):
        try:
            self.status_label.configure(text=text, fg=color)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    #  CHAT LOG — char-by-char typing
    # ══════════════════════════════════════════════════════════

    def write_log(self, text: str):
        self.typing_queue.append(text)
        if not self.is_typing:
            self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing = False
            return

        self.is_typing = True
        text = self.typing_queue.popleft()
        self.text_box.configure(state="normal")
        self._type_char(text, 0)

    def _type_char(self, text, i):
        if i < len(text):
            self.text_box.insert(tk.END, text[i])
            self.text_box.see(tk.END)
            self.root.after(12, self._type_char, text, i + 1)
        else:
            self.text_box.insert(tk.END, "\n")
            self.text_box.configure(state="disabled")
            self.root.after(40, self._start_typing)

    def clear_log(self):
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.configure(state="disabled")

    # ══════════════════════════════════════════════════════════
    #  API KEY SETUP
    # ══════════════════════════════════════════════════════════

    def _api_keys_exist(self):
        return API_FILE.exists()

    def _show_setup_ui(self):
        self.setup_frame = tk.Frame(
            self.root,
            bg="#050505",
            highlightbackground="#00cfff",
            highlightthickness=1
        )
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            self.setup_frame,
            text=f"⚡ {ASSISTANT_NAME.upper()} SETUP",
            fg="#8ffcff",
            bg="#050505",
            font=("Consolas", 14, "bold")
        ).pack(pady=(15, 5))

        tk.Label(
            self.setup_frame,
            text="Get your free API key from: openrouter.ai/keys",
            fg="#555555",
            bg="#050505",
            font=("Consolas", 8)
        ).pack(pady=(0, 10))

        self.openrouter_entry = self._setup_entry("OpenRouter API Key")
        self.serpapi_entry = self._setup_entry("SerpAPI Key (optional)")

        tk.Button(
            self.setup_frame,
            text="INITIALIZE SYSTEM",
            command=self._save_api_keys,
            bg="#001a2e",
            fg="#8ffcff",
            activebackground="#003344",
            activeforeground="#ffffff",
            font=("Consolas", 11, "bold"),
            borderwidth=0,
            padx=20,
            pady=8,
            cursor="hand2"
        ).pack(pady=15)

    def _setup_entry(self, label_text):
        tk.Label(
            self.setup_frame,
            text=label_text,
            fg="#8ffcff",
            bg="#050505",
            font=("Consolas", 10)
        ).pack(pady=(8, 2))

        entry = tk.Entry(
            self.setup_frame,
            width=50,
            fg="#8ffcff",
            bg="#0a0a0a",
            insertbackground="#8ffcff",
            borderwidth=1,
            relief="solid",
            font=("Consolas", 10),
            show="•"
        )
        entry.pack(pady=(0, 6), padx=15)
        return entry

    def _save_api_keys(self):
        openrouter_key = self.openrouter_entry.get().strip()
        serpapi_key = self.serpapi_entry.get().strip()

        if not openrouter_key:
            return

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "openrouter_api_key": openrouter_key,
                "serpapi_key": serpapi_key
            }, f, indent=4)

        self.setup_frame.destroy()
        self.api_keys_ready = True
        self.write_log(f"✅ API keys saved successfully.")
        self.write_log(f"⚡ {ASSISTANT_NAME} systems initializing...")

    # ══════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ══════════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()
