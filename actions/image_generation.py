"""
Image Generation Action
Uses Pollinations.ai (free, no key) to generate images.
"""
import requests
import os
import time
from pathlib import Path
from datetime import datetime

# Directory to save generated images
ASSETS_DIR = Path(__file__).parent.parent / "assets" / "generated"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def generate_image(prompt: str) -> str | None:
    """
    Generate an image from text using Pollinations.ai.
    Returns the path to the saved image file, or None if failed.
    """
    if not prompt:
        return None

    # Clean prompt for filename
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_prompt}.png"
    save_path = ASSETS_DIR / filename

    print(f"🎨 Generating image for: '{prompt}'...")
    
    try:
        # Pollinations.ai API (Direct URL)
        # We replace spaces with %20 just to be safe, though requests handles params usually.
        # But here we are constructing the URL directly as per their docs often suggesting.
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Image saved: {save_path}")
            return str(save_path)
        else:
            print(f"❌ Image generation failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Image generation error: {e}")
        return None

if __name__ == "__main__":
    # Test
    path = generate_image("futuristic city cyberpunk neon")
    if path:
        os.startfile(path)
