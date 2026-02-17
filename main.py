"""
Tokyo AI Assistant — Main Entry Point
Orchestrates voice + text input, AI processing, and action execution.
Powered by Google Gemini AI + 21 intents.
"""
import asyncio
import threading
import queue
import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from core.speech_to_text import record_voice, stop_listening, check_microphone
from core.llm import get_llm_output, test_connection
from core.tts import edge_speak, stop_speaking
from core.server import start_server, push_response, push_status, push_log
from core.clap import ClapListener
from core.voice_pack import play_mic_sound, play_process_sound
import socket
import ctypes

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
from ui import JarvisUI
from config import ASSISTANT_NAME, FACE_IMAGE_PATH, VOSK_MODEL_PATH

from actions.open_app import open_app
from actions.web_search import web_search
from actions.weather_report import weather_action
from actions.send_message import send_message
from actions.make_call import make_call
from actions.system_control import (
    system_info, file_operation, clipboard_action, take_screenshot,
    volume_control, set_timer, calculate, take_note_action,
    read_notes_action, shutdown_action
)
from actions.media_control import media_control, spotify_play, youtube_play
from actions.content import create_content_action

from memory.memory_manager import load_memory, update_memory, minimal_memory_for_prompt
from memory.temporary_memory import TemporaryMemory

# ── Constants ─────────────────────────────────────────────────
INTERRUPT_WORDS = {"stop", "mute", "quit", "exit", "shut up", "silence"}

# ── Session memory ────────────────────────────────────────────
temp_memory = TemporaryMemory()

# ── Shared input queue (voice + text) ─────────────────────────
input_queue = queue.Queue()

# ── Intent → Action mapping ──────────────────────────────────
ACTION_MAP = {
    "open_app": open_app,
    "search": web_search,
    "weather_report": weather_action,
    "send_message": send_message,
    "make_call": make_call,
    "system_info": system_info,
    "file_operation": file_operation,
    "clipboard": clipboard_action,
    "screenshot": take_screenshot,
    "volume_control": volume_control,
    "timer": set_timer,
    "calculate": calculate,
    "take_note": take_note_action,
    "read_notes": read_notes_action,
    "shutdown": shutdown_action,
    "media_control": media_control,
    "spotify_play": spotify_play,
    "youtube_play": youtube_play,
    "create_content": create_content_action,
}


# ══════════════════════════════════════════════════════════════
#  VOICE LISTENER THREAD
# ══════════════════════════════════════════════════════════════

voice_active = threading.Event()
voice_thread_started = False
_ui_ref = [None]  # Mutable reference for mic_toggle_handler


def voice_listener():
    """Runs in background thread — pushes voice text into input_queue."""
    while True:
        voice_active.wait()  # Block until mic is ON
        try:
            text = record_voice()
            if text and text.strip() and voice_active.is_set():
                input_queue.put(text.strip())
        except Exception as e:
            print(f"❌ Voice error: {e}")
            time.sleep(2)


def start_voice_thread():
    """Start the voice listener thread (only once)."""
    global voice_thread_started
    if not voice_thread_started:
        voice_thread_started = True
        threading.Thread(target=voice_listener, daemon=True).start()


def mic_toggle_handler(active: bool):
    """Called when user clicks the mic button."""
    if active:
        voice_active.set()
        start_voice_thread()
        print("🎙 Microphone ON")
        try: play_mic_sound()
        except: pass
    else:
        voice_active.clear()
        stop_listening()
        print("🔇 Microphone OFF")
    # Update the UI button state
    if _ui_ref[0]:
        _ui_ref[0].set_mic_active(active)


# ══════════════════════════════════════════════════════════════
#  TEXT INPUT HANDLER (called from UI thread)
# ══════════════════════════════════════════════════════════════

def handle_text_input(text: str):
    """Called when user types and presses Enter/Send."""
    if text and text.strip():
        input_queue.put(text.strip())


# ══════════════════════════════════════════════════════════════
#  PROCESS A SINGLE INPUT
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  PROCESS A SINGLE INPUT
# ══════════════════════════════════════════════════════════════

COMMON_MISHEARINGS = {
    "is it time": "what is the time",
    "what's the time": "what is the time",
    "tell me the time": "what is the time",
    "open no pad": "open notepad",
    "open know pad": "open notepad",
    "open google chrome": "open chrome",
    "stop lease": "stop list",
}

def process_input(user_text: str, ui: JarvisUI):
    """Process one user input (from voice or text)."""

    user_lower = user_text.lower().strip()

    # Fix common mishearings
    for bad, good in COMMON_MISHEARINGS.items():
        if bad in user_lower:
            user_text = user_text.replace(bad, good)
            user_lower = user_lower.replace(bad, good)

    # Check for interrupt
    if any(word in user_lower for word in INTERRUPT_WORDS):
        stop_speaking()
        temp_memory.soft_reset()
        ui.set_standby()
        ui.write_log("🔇 Muted.")
        return

    # Wake word check removed as per user request
    # Optional stripping if user says it out of habit
    user_text = user_text.replace("Tokyo", "").replace("tokyo", "").strip()
    if not user_text:
        return # Just said nothing

    # Only log user text if it came from voice/web (desktop _send_text already logs it)
    if not hasattr(ui, '_last_logged_text') or ui._last_logged_text != user_text:
        ui.write_log(f"You: {user_text}")
    ui._last_logged_text = None  # Reset after check
    ui.set_processing()

    # Handle follow-ups
    if temp_memory.get_current_question():
        param = temp_memory.get_current_question()
        temp_memory.update_parameters({param: user_text})
        temp_memory.clear_current_question()
        user_text = temp_memory.get_last_user_text() or user_text

    temp_memory.set_last_user_text(user_text)

    # Build memory context
    long_term = load_memory()
    memory_block = minimal_memory_for_prompt(long_term)

    history = temp_memory.get_history_for_prompt()
    if history.strip():
        memory_block["recent_conversation"] = history

    if temp_memory.has_pending_intent():
        memory_block["_pending_intent"] = temp_memory.pending_intent
        memory_block["_collected_params"] = str(temp_memory.get_parameters())
    
    # Context: Last Search (for "play that", "open that")
    if temp_memory.get_last_search():
        memory_block["last_search"] = str(temp_memory.get_last_search())

    # Call AI
    try:
        result = get_llm_output(
            user_text=user_text,
            memory_block=memory_block
        )
    except Exception as e:
        ui.write_log(f"❌ AI Error: {e}")
        push_response(f"❌ AI Error: {e}")
        edge_speak("Sir, I encountered a system error.", ui)
        ui.set_listening()
        return

    intent = result.get("intent", "chat")
    parameters = result.get("parameters", {})
    response = result.get("text", "")
    memory_update = result.get("memory_update")
    needs_clarification = result.get("needs_clarification", False)

    # Update memory
    if memory_update and isinstance(memory_update, dict):
        update_memory(memory_update)

    temp_memory.set_last_ai_response(response)

    # Handle clarification
    if needs_clarification:
        ui.write_log(f"AI: {response}")
        edge_speak(response, ui)
        if parameters:
            for k, v in parameters.items():
                if not v:
                    temp_memory.set_current_question(k)
                    break
        ui.set_listening()
        return

    # Execute action
    if intent in ACTION_MAP:
        action_fn = ACTION_MAP[intent]

        if intent == "send_message":
            temp_memory.set_pending_intent("send_message")
            temp_memory.update_parameters(parameters)

            required = ["receiver", "message_text", "platform"]
            if all(temp_memory.get_parameter(p) for p in required):
                threading.Thread(
                    target=action_fn,
                    kwargs={
                        "parameters": temp_memory.get_parameters(),
                        "response": response,
                        "player": ui,
                        "session_memory": temp_memory
                    },
                    daemon=True
                ).start()
                temp_memory.clear_pending_intent()
            else:
                ui.write_log(f"AI: {response}")
                edge_speak(response, ui)
                for p in required:
                    if not temp_memory.get_parameter(p):
                        temp_memory.set_current_question(p)
                        break
        else:
            # All other action intents
            kwargs = {
                "parameters": parameters,
                "response": response,
                "player": ui,
                "session_memory": temp_memory
            }
            threading.Thread(
                target=action_fn,
                kwargs=kwargs,
                daemon=True
            ).start()
    else:
        # Chat / unknown
        if response:
            ui.write_log(f"AI: {response}")
            push_response(response)
            edge_speak(response, ui)

    ui.set_listening()


# ══════════════════════════════════════════════════════════════
#  MAIN AI LOOP (polls shared queue)
# ══════════════════════════════════════════════════════════════

async def ai_loop(ui: JarvisUI):
    ui.write_log(f"⚡ {ASSISTANT_NAME} Mark XVIII")
    ui.write_log("─" * 45)

    # Wait for API keys
    if not ui.api_keys_ready:
        ui.write_log("⏳ Waiting for API key setup...")
        while not ui.api_keys_ready:
            await asyncio.sleep(0.5)

    # Test connection
    # ui.write_log("🔗 Connecting to OpenRouter AI...")
    success, msg = test_connection()
    # ui.write_log(msg)

    # Check microphone
    mic_ok, mic_msg = check_microphone()
    # ui.write_log(mic_msg)

    if mic_ok:
        # ui.write_log("🎙 Microphone AUTO-ON.")
        # Auto-enable mic on startup
        mic_toggle_handler(True)
        ui.set_mic_active(True)
    else:
        # ui.write_log("⌨️ No mic detected — text-only mode.")
        pass

    # Start Mobile Remote Server
    try:
        start_server(input_queue)
        local_ip = get_local_ip()
        mobile_url = f"http://{local_ip}:5000"
        # ui.write_log(f"🌐 Web UI: {mobile_url}")
        # ui.write_log(f"📱 Mobile: {mobile_url} (install as PWA)")
    except Exception as e:
        ui.write_log(f"Server Error: {e}")

    if success:
        edge_speak(
            f"{ASSISTANT_NAME} systems online. Ready for your command, Sir.",
            ui
        )
    else:
        ui.write_log("⚠️ Running in limited mode. Check your API key.")

    ui.set_listening()

    # Check for startup command
    startup_cmd_path = BASE_DIR / "startup_command.txt"
    if startup_cmd_path.exists():
        try:
            cmd_text = startup_cmd_path.read_text("utf-8").strip()
            if cmd_text:
                ui.write_log(f"🚀 Auto-Executing: {cmd_text[:50]}...")
                # Delay slightly to ensure UI is ready
                await asyncio.sleep(2.0)
                input_queue.put(cmd_text)
            startup_cmd_path.unlink()  # Delete after reading
        except Exception as e:
            print(f"Startup Command Error: {e}")

    # Main loop — poll shared queue
    while True:
        try:
            user_text = input_queue.get(timeout=0.1)
        except queue.Empty:
            await asyncio.sleep(0.01)
            continue

        process_input(user_text, ui)


# ══════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════

def main():
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║  {ASSISTANT_NAME.upper()} AI ASSISTANT — MARK XVIII          ║
    ║  Powered by OpenRouter AI                    ║
    ║  Voice + Text + Intelligence + Control        ║
    ╚══════════════════════════════════════════════╝
    """)

    # ── Single Instance Check (Bulletproof) ─────────────────────────
    # Method 1: Windows Mutex (kernel-level)
    # CRITICAL: Must use use_last_error=True to prevent GetLastError from being
    # cleared by intervening Python/ctypes internal calls.
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    mutex_name = "Global\\TokyoAI_SingleInstance_Mutex"
    mutex_handle = _kernel32.CreateMutexW(None, True, mutex_name)
    last_error = ctypes.get_last_error()  # Cached immediately, not cleared
    
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        print("⚠️ Tokyo AI is ALREADY RUNNING!")
        print("   Close existing instances from Task Manager first.")
        _kernel32.CloseHandle(mutex_handle)
        sys.exit(1)
    
    if not mutex_handle:
        print("⚠️ Failed to create mutex, continuing anyway...")
    
    # Method 2: Socket lock (backup)
    SINGLE_INSTANCE_PORT = 65000
    try:
        instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        instance_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        instance_socket.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        instance_socket.listen(1)
    except socket.error:
        print("⚠️ Tokyo AI is ALREADY RUNNING! (Port check)")
        sys.exit(1)
    # ──────────────────────────────────────────────────────────────

    # ── Hide Console Window ───────────────────────────────────────
    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        ctypes.windll.user32.ShowWindow(console_hwnd, 0)  # SW_HIDE
    # ──────────────────────────────────────────────────────────────

    face_path = FACE_IMAGE_PATH
    if not face_path.exists():
        alt = BASE_DIR / "face.png"
        if alt.exists():
            face_path = alt

    ui = JarvisUI(
        face_path=str(face_path) if face_path.exists() else None,
        size=(760, 760)
    )
    _ui_ref[0] = ui  # Set global ref for mic_toggle_handler

    # Wire callbacks
    ui.on_text_input = handle_text_input
    ui.on_mic_toggle = mic_toggle_handler

    # ── Start UI Visible with mic active ───
    _is_awake = [True]  # Track awake state
    _greet_lock = threading.Lock()  # Prevent overlapping greets
    mic_toggle_handler(True)  # This now also updates UI via _ui_ref
    ui.write_log("🫡 At your service, Sir.")

    def _on_hide():
        """Called when the window is hidden (X button). Resets state so clap/wake can re-trigger."""
        _is_awake[0] = False
        ui.hide_window()
        # Resume listeners immediately so they can detect claps/wake words
        # (this also cancels any stuck pause from _greet)
        clap_listener.resume()
        wake_listener.resume()
        print("💤 Window hidden — clap & wake word listeners active")

    def _wake_up():
        """Show UI and activate (must run on main thread). INSTANT response."""
        if _is_awake[0]:
            return  # Already awake — silently ignore
        _is_awake[0] = True
        
        # INSTANT: Show window + enable mic immediately
        ui.show_window()
        ui.root.attributes("-topmost", True)
        ui.root.after(500, lambda: ui.root.attributes("-topmost", False))
        mic_toggle_handler(True)
        ui.write_log("🫡 At your service, Sir.")
        
        # Background: TTS greeting + listener management (non-blocking)
        def _greet():
            with _greet_lock:
                # Check if still awake before pausing (window may have been hidden already)
                if not _is_awake[0]:
                    return
                clap_listener.pause()
                wake_listener.pause()
                edge_speak("At your service, Sir.", ui)
                time.sleep(1.0)
                # Only resume if still awake — _on_hide already resumed them if hidden
                if _is_awake[0]:
                    clap_listener.resume()
                    wake_listener.resume()
        threading.Thread(target=_greet, daemon=True).start()

    def on_wake_trigger():
        """Called by either double-clap or wake phrase (from background thread)."""
        try:
            ui.root.after(0, _wake_up)
        except:
            pass

    # Start AudioHub (Shared Microphone Stream)
    from core.audio_hub import audio_hub
    audio_hub.start()

    # Start Double-Clap Listener (optimized spectral + transient detection)
    clap_listener = ClapListener(
        on_clap_callback=on_wake_trigger, 
        threshold=12, 
        double_clap_min=0.12,
        double_clap_max=0.55,
        cooldown=2.0
    )
    clap_listener.start()

    # Start Wake Word Listener ("daddy's home", "jarvis", etc.)
    from core.wake_word import WakeWordListener
    wake_listener = WakeWordListener(
        on_wake_callback=on_wake_trigger,
        model_path=str(VOSK_MODEL_PATH)
    )
    wake_listener.start()

    # Wire the hide callback so _is_awake resets when window is closed
    ui.root.protocol("WM_DELETE_WINDOW", _on_hide)
    # ──────────────────────────────────────────────────────────────

    # Start AI loop in background
    def runner():
        asyncio.run(ai_loop(ui))

    threading.Thread(target=runner, daemon=True).start()

    ui.root.mainloop()


if __name__ == "__main__":
    main()

