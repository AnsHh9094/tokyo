"""
Long-Term Memory Manager
Persistent storage for user identity, preferences, relationships.
Based on Mark-X.1 memory_manager.py by FatihMakes, enhanced with notes.
"""
import json
import os
from threading import Lock
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MEMORY_DIR

MEMORY_PATH = MEMORY_DIR / "memory.json"
NOTES_PATH = MEMORY_DIR / "notes.json"
_lock = Lock()


def _empty_memory() -> dict:
    """Return an empty memory structure."""
    return {
        "identity": {},
        "preferences": {},
        "relationships": {},
        "emotional_state": {}
    }


def load_memory() -> dict:
    """Load memory from disk, return empty if not exists or invalid."""
    if not MEMORY_PATH.exists():
        return _empty_memory()

    with _lock:
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return _empty_memory()
        except Exception:
            return _empty_memory()


def save_memory(memory: dict) -> None:
    """Save memory to disk safely."""
    if not isinstance(memory, dict):
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    with _lock:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)


def _recursive_update(target: dict, updates: dict) -> bool:
    """Recursively merge updates into target memory. Returns True if changed."""
    changed = False
    now = datetime.utcnow().isoformat() + "Z"

    for key, value in updates.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            entry = value if isinstance(value, dict) and "value" in value else {"value": value}
            if key not in target or target[key] != entry:
                target[key] = entry
                changed = True

    return changed


def update_memory(memory_update: dict) -> dict:
    """Merge LLM memory update into global memory and save."""
    if not isinstance(memory_update, dict):
        return load_memory()

    memory = load_memory()
    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print("💾 Memory updated")

    return memory


def minimal_memory_for_prompt(memory: dict) -> dict:
    """
    Create a compact memory summary for the LLM prompt.
    Only includes fields that have values.
    """
    summary = {}

    for category in ("identity", "preferences", "relationships", "emotional_state"):
        cat_data = memory.get(category, {})
        if cat_data:
            compact = {}
            for key, val in cat_data.items():
                if isinstance(val, dict) and "value" in val:
                    compact[key] = val["value"]
                elif isinstance(val, dict):
                    compact[key] = {k: v.get("value", v) if isinstance(v, dict) else v
                                    for k, v in val.items() if k != "updated_at"}
                else:
                    compact[key] = val
            if compact:
                summary[category] = compact

    return summary


# ═══════════════════════════════════════════════════════════════
#  NOTES SYSTEM
# ═══════════════════════════════════════════════════════════════

def add_note(title: str, content: str):
    """Add a note to persistent storage."""
    notes = get_notes()
    notes.append({
        "title": title,
        "content": content,
        "created_at": datetime.now().isoformat()
    })

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def get_notes() -> list:
    """Get all saved notes."""
    if not NOTES_PATH.exists():
        return []
    try:
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
