"""
Jarvis AI Assistant — Dramatic Animated GUI (Tkinter Canvas)
Galaxy-inspired: glowing orb, particles, orbital rings, reactive states.
Pure Python (no external dependencies beyond tkinter).
"""
import tkinter as tk
from tkinter import scrolledtext
from pathlib import Path
import time
import random
import math
import sys
import queue

sys.path.insert(0, str(Path(__file__).parent))
from config import CONFIG_DIR, ASSETS_DIR, ASSISTANT_NAME

API_FILE = CONFIG_DIR / "api_keys.json"

# ── Color Palette ────────────────────────────────────────────
COLORS = {
    "bg":           "#050510",
    "orb_core":     "#80e0ff",
    "orb_mid":      "#2090b0",
    "orb_outer":    "#0a3040",
    "particle":     "#40a0c0",
    "ring":         "#1a4060",
    "text":         "#c0e8ff",
    "chat_bg":      "#0a0a1a",
    "input_bg":     "#0c0c20",
    "border":       "#1a3050",
    "accent":       "#00d4ff",
    "status_standby":   "#4a9eff",
    "status_listen":    "#ffaa00",
    "status_speak":     "#00ff88",
    "status_process":   "#ff4488",
}

# ── Compact Window Size ──────────────────────────────────────
WIN_W = 420
WIN_H = 600


class Particle:
    def __init__(self, cx, cy, w, h):
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.reset()

    def reset(self):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(20, 140)
        self.x = self.cx + math.cos(angle) * dist
        self.y = self.cy + math.sin(angle) * dist
        self.vx = random.uniform(-12, 12)
        self.vy = random.uniform(-20, -4)
        self.life = 1.0
        self.decay = random.uniform(0.3, 0.8)
        self.size = random.uniform(1.0, 2.5)

    def update(self, dt, speed_mult=1.0):
        self.x += self.vx * dt * speed_mult
        self.y += self.vy * dt * speed_mult
        self.life -= self.decay * dt
        if self.life <= 0 or self.x < 0 or self.x > self.w or self.y < 0 or self.y > self.h:
            self.reset()
            self.life = 1.0


class OrbitalRing:
    def __init__(self, radius=80, speed=0.3, segments=50, width=1.0):
        self.radius = radius
        self.speed = speed
        self.segments = segments
        self.width = width
        self.angle = random.uniform(0, 2 * math.pi)
        self.tilt = random.uniform(0.15, 0.4)

    def update(self, dt):
        self.angle += self.speed * dt


class JarvisUI:
    def __init__(self, face_path=None, size=None):
        self.root = tk.Tk()
        self.root.title(f"{ASSISTANT_NAME} AI")
        self.root.configure(bg=COLORS["bg"])

        # ── Compact centered window ──────────────────────────
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WIN_W) // 2
        y = (sh - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
        self.root.minsize(350, 450)
        self.root.resizable(True, True)

        # ── State ────────────────────────────────────────────
        self.mic_active = False
        self.on_text_input = None
        self.on_mic_toggle = None
        self.state = "standby"
        self._msg_queue = queue.Queue()
        self.api_keys_ready = API_FILE.exists()

        # ══════════════════════════════════════════════════════
        #  LAYOUT: Canvas (top) → Status → Chat → Input bar
        # ══════════════════════════════════════════════════════

        # Animation Canvas — fixed height, fills width
        self.canvas = tk.Canvas(
            self.root, height=200,
            bg=COLORS["bg"], highlightthickness=0
        )
        self.canvas.pack(fill=tk.X, padx=0, pady=0)

        # Status label
        self.status_var = tk.StringVar(value="● STANDBY")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["status_standby"], bg=COLORS["bg"]
        )
        self.status_label.pack(pady=(2, 4))

        # ══════════════════════════════════════════════════════
        # BOTTOM CONTROLS — packed first with side=BOTTOM
        # so they're ALWAYS visible regardless of window size
        # ══════════════════════════════════════════════════════

        # ── Input bar (BOTTOM-most) ──────────────────────────
        input_frame = tk.Frame(self.root, bg=COLORS["bg"])
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))

        self.text_entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 11),
            bg=COLORS["input_bg"], fg="#ffffff",
            insertbackground=COLORS["accent"],
            relief=tk.FLAT, bd=6
        )
        self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text_entry.bind("<Return>", self._on_enter)

        send_btn = tk.Button(
            input_frame, text="▶", width=3,
            font=("Segoe UI", 10, "bold"),
            fg=COLORS["accent"], bg="#0a1a30",
            activebackground="#0f2a40", activeforeground="#00ffff",
            relief=tk.FLAT, bd=0,
            command=self._send_text
        )
        send_btn.pack(side=tk.RIGHT, padx=(6, 0))

        # ── Mic Toggle — LARGE bar above input ───────────────
        self.mic_btn = tk.Button(
            self.root, text="⏻  MIC OFF", height=2,
            font=("Segoe UI", 12, "bold"),
            fg="#ff4444", bg="#1a0000",
            activebackground="#2a0000", activeforeground="#ff6666",
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=self._mic_click
        )
        self.mic_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(4, 4))

        # ══════════════════════════════════════════════════════
        # CHAT LOG — fills remaining space between status & mic
        # ══════════════════════════════════════════════════════
        chat_frame = tk.Frame(self.root, bg=COLORS["border"], bd=1, relief=tk.FLAT)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        self.chat_log = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg=COLORS["chat_bg"], fg=COLORS["text"],
            font=("Consolas", 10),
            insertbackground=COLORS["accent"],
            relief=tk.FLAT, bd=6,
            selectbackground="#1a4060"
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True)

        # ── Animation state ──────────────────────────────────
        self.orb_radius = 35.0
        self.orb_target = 35.0
        self.orb_pulse = 0.0
        self.orb_pulse_speed = 1.5
        self.frame_count = 0
        self.last_time = time.time()
        self.particle_speed = 1.0

        # Dynamic center — updated on resize
        self.cx = WIN_W // 2
        self.cy = 100  # Center of 200px canvas
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Particles
        self.particles = []
        for _ in range(35):
            p = Particle(self.cx, self.cy, WIN_W, 200)
            p.life = random.uniform(0, 1)
            self.particles.append(p)

        # Rings (smaller for compact window)
        self.rings = [
            OrbitalRing(radius=70, speed=0.3, segments=50, width=1.0),
            OrbitalRing(radius=95, speed=-0.2, segments=40, width=0.8),
            OrbitalRing(radius=120, speed=0.15, segments=30, width=0.6),
        ]

        # Start loops
        self._animate()
        self._process_queue()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Force window to front on startup
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(1000, lambda: self.root.attributes("-topmost", False))

    # ══════════════════════════════════════════════════════════
    #  CANVAS RESIZE HANDLER — keeps orb centered
    # ══════════════════════════════════════════════════════════
    def _on_canvas_resize(self, event):
        self.cx = event.width // 2
        self.cy = event.height // 2
        for p in self.particles:
            p.cx = self.cx
            p.cy = self.cy
            p.w = event.width
            p.h = event.height

    # ══════════════════════════════════════════════════════════
    #  WINDOW MANAGEMENT
    # ══════════════════════════════════════════════════════════
    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    # ══════════════════════════════════════════════════════════
    #  ANIMATION LOOP (~30fps)
    # ══════════════════════════════════════════════════════════
    def _animate(self):
        now = time.time()
        dt = min(now - self.last_time, 0.1)
        self.last_time = now
        self.frame_count += 1

        self.canvas.delete("all")

        self._update_orb(dt)
        self._update_particles(dt)
        for ring in self.rings:
            ring.update(dt)

        self._draw_bg_glow()
        self._draw_rings()
        self._draw_particles()
        self._draw_orb()
        self._draw_label()

        self.root.after(33, self._animate)

    def _update_orb(self, dt):
        targets = {"speaking": (45, 3.0), "processing": (30, 5.0),
                    "listening": (38, 2.0), "standby": (35, 1.5)}
        t, s = targets.get(self.state, (35, 1.5))
        self.orb_target = t
        self.orb_pulse_speed = s
        self.orb_radius += (self.orb_target - self.orb_radius) * dt * 3.0
        self.orb_pulse = math.sin(time.time() * self.orb_pulse_speed) * 0.5 + 0.5

        if self.state == "processing":
            self.cx = self.canvas.winfo_width() // 2 + int(math.sin(time.time() * 20) * 2)

    def _update_particles(self, dt):
        speeds = {"speaking": 2.5, "processing": 4.0, "listening": 1.5, "standby": 0.8}
        self.particle_speed = speeds.get(self.state, 0.8)
        for p in self.particles:
            p.update(dt, self.particle_speed)

    def _draw_bg_glow(self):
        for size, color in [(160, "#030810"), (110, "#051020"), (70, "#081830")]:
            s = int(size * (1 + self.orb_pulse * 0.1))
            self.canvas.create_oval(self.cx-s, self.cy-s, self.cx+s, self.cy+s, fill=color, outline="")

    def _draw_rings(self):
        for ring in self.rings:
            pts = []
            for i in range(ring.segments + 1):
                t = (i / ring.segments) * 2 * math.pi
                rx = ring.radius * math.cos(t + ring.angle)
                ry = ring.radius * math.sin(t + ring.angle) * ring.tilt
                pts.append((self.cx + rx, self.cy + ry))
            for i in range(len(pts) - 1):
                a = abs(math.sin((i / ring.segments) * math.pi))
                if a > 0.3:
                    self.canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                                            fill=COLORS["ring"], width=ring.width)

    def _draw_particles(self):
        for p in self.particles:
            if p.life > 0:
                a = max(0, min(1, p.life))
                s = int(p.size * a)
                if s > 0:
                    c = f"#{int(64*a):02x}{int(160*a):02x}{int(192*a):02x}"
                    self.canvas.create_oval(p.x-s, p.y-s, p.x+s, p.y+s, fill=c, outline="")

    def _draw_orb(self):
        r = self.orb_radius
        for gr, gc in [(r*2.2,"#010812"),(r*1.7,"#021424"),(r*1.3,"#032030"),(r*1.1,"#053848")]:
            g = int(gr * (1 + self.orb_pulse * 0.2))
            self.canvas.create_oval(self.cx-g, self.cy-g, self.cx+g, self.cy+g, fill=gc, outline="")
        cr = int(r * (1 + self.orb_pulse * 0.15))
        self.canvas.create_oval(self.cx-cr-2, self.cy-cr-2, self.cx+cr+2, self.cy+cr+2,
                                fill="", outline=COLORS["orb_mid"], width=1.5)
        self.canvas.create_oval(self.cx-cr, self.cy-cr, self.cx+cr, self.cy+cr,
                                fill=COLORS["orb_outer"], outline="")
        ir = int(cr * 0.6)
        self.canvas.create_oval(self.cx-ir, self.cy-ir, self.cx+ir, self.cy+ir,
                                fill=COLORS["orb_mid"], outline="")
        br = int(cr * 0.3)
        self.canvas.create_oval(self.cx-br, self.cy-br, self.cx+br, self.cy+br,
                                fill=COLORS["orb_core"], outline="")

    def _draw_label(self):
        self.canvas.create_text(self.cx, self.cy,
            text=ASSISTANT_NAME[0] if ASSISTANT_NAME else "J",
            font=("Segoe UI", 14, "bold"), fill="#ffffff")

    # ══════════════════════════════════════════════════════════
    #  PUBLIC API (thread-safe via queue)
    # ══════════════════════════════════════════════════════════
    def write_log(self, text):
        self._msg_queue.put(("log", text))

    def start_speaking(self):
        self._msg_queue.put(("state", "speaking"))

    def stop_speaking(self):
        self._msg_queue.put(("state", "listening"))

    def set_listening(self):
        self._msg_queue.put(("state", "listening"))

    def set_processing(self):
        self._msg_queue.put(("state", "processing"))

    def set_standby(self):
        self._msg_queue.put(("state", "standby"))

    def set_mic_active(self, active):
        self._msg_queue.put(("mic", active))

    def _process_queue(self):
        try:
            while True:
                t, d = self._msg_queue.get_nowait()
                if t == "log":
                    self._do_log(d)
                elif t == "state":
                    self._do_state(d)
                elif t == "mic":
                    self._do_mic(d)
        except queue.Empty:
            pass
        self.root.after(50, self._process_queue)

    def _do_log(self, text):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, text + "\n")
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _do_state(self, state):
        self.state = state
        m = {"standby": ("● STANDBY", COLORS["status_standby"]),
             "listening": ("◉ LISTENING", COLORS["status_listen"]),
             "speaking": ("◈ SPEAKING", COLORS["status_speak"]),
             "processing": ("◆ PROCESSING", COLORS["status_process"])}
        txt, col = m.get(state, ("● STANDBY", COLORS["status_standby"]))
        self.status_var.set(txt)
        self.status_label.config(fg=col)

    def _do_mic(self, active):
        self.mic_active = active
        if active:
            self.mic_btn.config(text="◉  MIC LIVE", fg="#00ff88", bg="#001a0a")
        else:
            self.mic_btn.config(text="⏻  MIC OFF", fg="#ff4444", bg="#1a0000")

    # ══════════════════════════════════════════════════════════
    #  INPUT
    # ══════════════════════════════════════════════════════════
    def _mic_click(self):
        if self.on_mic_toggle:
            self.on_mic_toggle(not self.mic_active)

    def _on_enter(self, event):
        self._send_text()

    def _send_text(self):
        text = self.text_entry.get().strip()
        if text and self.on_text_input:
            self.write_log(f"You: {text}")
            self._last_logged_text = text  # Flag to prevent duplicate logging
            self.on_text_input(text)
            self.text_entry.delete(0, tk.END)

    def _show_setup_ui(self):
        self.write_log("⚠️ API Keys Missing!")
