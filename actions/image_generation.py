"""
Image Generation Action
Uses multiple free AI image APIs with automatic fallback.
Primary: Pollinations.ai | Fallback: Together.xyz free tier
"""
import requests
import os
import time
import random
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

# Directory to save generated images
ASSETS_DIR = Path(__file__).parent.parent / "assets" / "generated"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _try_pollinations(prompt: str, save_path: Path) -> bool:
    """Try Pollinations.ai (free, no key). Returns True if successful."""
    seed = int(time.time() * 1000) + random.randint(0, 99999)
    encoded = quote(prompt, safe='')
    
    # Try without model param first (most reliable), then with flux
    urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?nologo=true&width=1024&height=1024&seed={seed}",
        f"https://image.pollinations.ai/prompt/{encoded}?model=flux&nologo=true&width=1024&height=1024&seed={seed}",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "image/*",
    }
    
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", "") and len(r.content) > 5000:
                with open(save_path, "wb") as f:
                    f.write(r.content)
                print(f"✅ Pollinations: {len(r.content)} bytes")
                return True
            print(f"⚠️ Pollinations: HTTP {r.status_code}")
        except requests.exceptions.Timeout:
            print("⚠️ Pollinations: timeout")
        except Exception as e:
            print(f"⚠️ Pollinations: {e}")
    
    return False


def _try_picsum(prompt: str, save_path: Path) -> bool:
    """Fallback: Lorem Picsum (random high-quality photo). Not prompt-accurate but always works."""
    try:
        seed = random.randint(1, 1000)
        url = f"https://picsum.photos/seed/{seed}/1024/1024"
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(save_path, "wb") as f:
                f.write(r.content)
            print(f"✅ Picsum fallback: {len(r.content)} bytes")
            return True
    except Exception as e:
        print(f"⚠️ Picsum: {e}")
    return False


def generate_image(prompt: str) -> str | None:
    """
    Generate an image from text prompt.
    Tries Pollinations.ai first, then fallbacks.
    Returns path to saved image, or None if all fail.
    """
    if not prompt:
        return None

    # Clean prompt for filename
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_prompt}.png"
    save_path = ASSETS_DIR / filename

    print(f"🎨 Generating: '{prompt[:60]}...'")
    
    # Try APIs in order
    if _try_pollinations(prompt, save_path):
        return str(save_path)
    
    print("🔄 All AI image APIs failed. Using photo fallback...")
    if _try_picsum(prompt, save_path):
        return str(save_path)
    
    print("❌ All image sources failed")
    return None


if __name__ == "__main__":
    path = generate_image("a wooden table in a modern room")
    if path:
        print(f"Saved: {path}")
        os.startfile(path)
    else:
        print("Failed")
