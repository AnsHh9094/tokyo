"""
Jarvis AI Assistant — Main Entry Point
Orchestrates voice + text input, AI processing, and action execution.
Based on Mark-X.1 by FatihMakes, enhanced with OpenRouter AI + 15 intents.
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
from ui import JarvisUI
from config import ASSISTANT_NAME, FACE_IMAGE_PATH

from actions.open_app import open_app
from actions.web_search import web_search
from actions.weather_report import weather_action
from actions.send_message import send_message
from actions.system_control import (
    system_info, file_operation, clipboard_action, take_screenshot,
    volume_control, set_timer, calculate, take_note_action,
    read_notes_action, shutdown_action
)

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
}


# ══════════════════════════════════════════════════════════════
#  VOICE LISTENER THREAD
# ══════════════════════════════════════════════════════════════

voice_active = threading.Event()
voice_thread_started = False


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
    else:
        voice_active.clear()
        stop_listening()
        print("🔇 Microphone OFF")


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

def process_input(user_text: str, ui: JarvisUI):
    """Process one user input (from voice or text)."""

    user_lower = user_text.lower().strip()

    # Check for interrupt
    if any(word in user_lower for word in INTERRUPT_WORDS):
        stop_speaking()
        temp_memory.soft_reset()
        ui.set_standby()
        ui.write_log("🔇 Muted.")
        return

    ui.write_log(f"You: {user_text}")
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

    # Call AI
    try:
        result = get_llm_output(
            user_text=user_text,
            memory_block=memory_block
        )
    except Exception as e:
        ui.write_log(f"❌ AI Error: {e}")
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
    ui.write_log("🔗 Connecting to OpenRouter AI...")
    success, msg = test_connection()
    ui.write_log(msg)

    # Check microphone
    mic_ok, mic_msg = check_microphone()
    ui.write_log(mic_msg)

    if mic_ok:
        ui.write_log("🎙 Click the MIC button to enable voice input.")
    else:
        ui.write_log("⌨️ No mic detected — text-only mode.")

    if success:
        edge_speak(
            f"{ASSISTANT_NAME} systems online. Ready for your command, Sir.",
            ui
        )
    else:
        ui.write_log("⚠️ Running in limited mode. Check your API key.")

    ui.set_listening()

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

    face_path = FACE_IMAGE_PATH
    if not face_path.exists():
        alt = BASE_DIR / "face.png"
        if alt.exists():
            face_path = alt

    ui = JarvisUI(
        face_path=str(face_path) if face_path.exists() else None,
        size=(760, 760)
    )

    # Wire callbacks
    ui.on_text_input = handle_text_input
    ui.on_mic_toggle = mic_toggle_handler

    # Start AI loop in background
    def runner():
        asyncio.run(ai_loop(ui))

    threading.Thread(target=runner, daemon=True).start()

    ui.root.mainloop()


if __name__ == "__main__":
    main()

