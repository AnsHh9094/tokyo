"""
Tokyo AI — LLM Engine (OpenRouter)
Uses OpenRouter API with free models for intelligent conversation,
code generation, problem solving, and natural interaction.
"""
import os
import json
import requests
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ASSISTANT_NAME, CONFIG_DIR, OPENROUTER_API_KEY

# ── OpenRouter Configuration ─────────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "arcee-ai/trinity-large-preview:free"

# ── Paths ─────────────────────────────────────────────────────
CORE_DIR = Path(__file__).parent
PROMPT_PATH = CORE_DIR / "prompt.txt"


# ── API Keys ──────────────────────────────────────────────────

# ── API Keys ──────────────────────────────────────────────────

def get_openrouter_key() -> str | None:
    """Get OpenRouter API key."""
    return OPENROUTER_API_KEY


# ── System Prompt ─────────────────────────────────────────────

def load_system_prompt() -> str:
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ prompt.txt couldn't be loaded: {e}")
        return f"You are {ASSISTANT_NAME}, a helpful AI assistant. Respond in JSON format."


SYSTEM_PROMPT = load_system_prompt()


# ── JSON Parser ───────────────────────────────────────────────

def safe_json_parse(text: str) -> dict | None:
    """Robustly parse JSON from LLM response, handling markdown wrapping."""
    if not text:
        return None

    text = text.strip()

    # Strip markdown code blocks
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        except Exception:
            pass
    elif "```" in text:
        try:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()
        except Exception:
            pass

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except Exception as e:
        print(f"⚠️ JSON parse error: {e}")
        print(f"⚠️ Raw text preview: {text[:200]}")
        return None


# ── Main LLM Interface ───────────────────────────────────────

def get_llm_output(user_text: str, memory_block: dict | None = None) -> dict:
    """
    Send user text to OpenRouter and get structured JSON response.
    Uses free model — no payment required.
    """
    default = {
        "intent": "chat",
        "parameters": {},
        "needs_clarification": False,
        "text": "Sir, I didn't catch that.",
        "memory_update": None
    }

    if not user_text or not user_text.strip():
        return default

    api_key = get_openrouter_key()
    if not api_key:
        print("❌ OPENROUTER API KEY NOT FOUND")
        return {
            "intent": "chat",
            "parameters": {},
            "needs_clarification": False,
            "text": "Sir, the OpenRouter API key is missing. Please set it up.",
            "memory_update": None
        }

    # Build memory context
    memory_str = ""
    if memory_block:
        memory_str = "\n".join(f"{k}: {v}" for k, v in memory_block.items())

    # Add time context
    now = datetime.now()
    time_str = now.strftime('%A, %B %d, %Y at %I:%M %p')

    user_prompt = f"""Current time: {time_str}

User message: "{user_text}"

Known user memory:
{memory_str if memory_str else "No memory available"}"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Tokyo-Assistant"
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ OpenRouter API Error: {response.text}")
            return {
                "intent": "chat",
                "parameters": {},
                "needs_clarification": False,
                "text": f"Sir, API error ({response.status_code}).",
                "memory_update": None
            }

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = safe_json_parse(content)

        if parsed:
            return {
                "intent": parsed.get("intent", "chat"),
                "parameters": parsed.get("parameters", {}),
                "needs_clarification": parsed.get("needs_clarification", False),
                "text": parsed.get("text", "I'm here, Sir."),
                "memory_update": parsed.get("memory_update")
            }
        else:
            return {
                "intent": "chat",
                "parameters": {},
                "needs_clarification": False,
                "text": content if content else "Sir, I had trouble processing that.",
                "memory_update": None
            }

    except requests.exceptions.Timeout:
        print("❌ OpenRouter timeout")
        return {
            "intent": "chat",
            "parameters": {},
            "needs_clarification": False,
            "text": "Sir, the request timed out.",
            "memory_update": None
        }

    except Exception as e:
        print(f"❌ LLM ERROR: {e}")
        return {
            "intent": "chat",
            "parameters": {},
            "needs_clarification": False,
            "text": "Sir, a system error occurred.",
            "memory_update": None
        }


# ── Content Generation ────────────────────────────────────────

def generate_text(prompt: str, system_prompt: str = None) -> str | None:
    """
    Generate raw text from LLM (no JSON parsing).
    Useful for writing posts, essays, etc.
    """
    api_key = get_openrouter_key()
    if not api_key:
        print("❌ OPENROUTER API KEY NOT FOUND")
        return None

    if not system_prompt:
        system_prompt = "You are a professional content creator. Write high-quality, engaging content."

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Tokyo-Assistant"
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=40
        )

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"❌ API Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Text Generation Error: {e}")
        return None


# ── Connection Test ───────────────────────────────────────────

def test_connection() -> tuple[bool, str]:
    """Test the OpenRouter API connection."""
    api_key = get_openrouter_key()
    if not api_key:
        return False, "❌ OpenRouter API key not found. Enter it in the setup screen."

    try:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Say 'Connection successful' in exactly 2 words."}
            ],
            "max_tokens": 10
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Tokyo-Assistant"
        }

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return True, f"✅ Connected to OpenRouter ({MODEL})"
        else:
            return False, f"❌ Connection failed (HTTP {response.status_code}): {response.text[:200]}"

    except Exception as e:
        return False, f"❌ Connection failed: {e}"
