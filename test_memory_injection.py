import sys
from pathlib import Path
import json

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from memory.memory_manager import load_memory, update_memory, minimal_memory_for_prompt

def test_memory():
    print("1. Loading Memory...")
    mem = load_memory()
    print(f"   Current Memory: {json.dumps(mem, indent=2)}")

    print("\n2. Simulating Update (User Name = Ansh, Profession = Developer)...")
    update_data = {
        "identity": {
            "name": "Ansh",
            "profession": "Developer"
        },
        "preferences": {
            "theme": "Dark Mode"
        }
    }
    update_memory(update_data)
    
    print("\n3. Reloading Memory...")
    new_mem = load_memory()
    print(f"   New Memory: {json.dumps(new_mem, indent=2)}")

    print("\n4. Testing Prompt Injection (Minimal Summary)...")
    summary = minimal_memory_for_prompt(new_mem)
    print(f"   Summary for Prompt: {json.dumps(summary, indent=2)}")

    if summary.get("identity", {}).get("name") == "Ansh":
        print("\n✅ TEST PASSED: Memory updated and summarized correctly.")
    else:
        print("\n❌ TEST FAILED: Name not found in summary.")

if __name__ == "__main__":
    test_memory()
