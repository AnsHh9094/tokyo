
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from actions.image_generation import generate_image

print("🚀 Testing Image Generation...")
try:
    path = generate_image("test image of a cat")
    if path:
        print(f"✅ Success! Image at: {path}")
    else:
        print("❌ Function returned None")
except Exception as e:
    print(f"❌ Exception: {e}")
