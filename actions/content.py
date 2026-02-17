"""
Content Creation Handler
Routes requests to:
1. LinkedIn Post Generator
2. Image Generator
3. Essay/Text Generator
"""
import sys
from pathlib import Path
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))
from actions.linkedin import create_linkedin_post
from actions.image_generation import generate_image
from core.tts import edge_speak

def create_content_action(parameters: dict, response: str = None, player=None, session_memory=None):
    """
    Dispatcher for content creation.
    """
    platform = parameters.get("platform", "").lower()
    topic = parameters.get("topic", "")
    content = parameters.get("content", "")

    # 1. Image Generation
    if platform in ["image", "picture", "art", "drawing"] or "generate image" in topic.lower():
        prompt = content if content else topic
        if not prompt:
            edge_speak("What should I generate an image of?", player)
            return
        
        # Enhance prompt with quality tags — NO LLM expansion.
        # The image model (Flux) understands prompts much better than LLM text expansion,
        # which was hallucinating wildly (e.g. "table" → "sports car").
        prompt = f"{prompt}, high quality, detailed, photorealistic, 4K, professional"
        if player:
            player.write_log(f"🎨 Prompt: {prompt[:60]}...")

        if player:
            player.write_log(f"🎨 Generating image...")
        edge_speak(f"Generating image...", player)
        
        image_path = generate_image(prompt)
        
        if image_path:
            import os
            try:
                os.startfile(image_path)
                if player:
                    player.write_log(f"✅ Image opened: {Path(image_path).name}")
            except:
                pass
            edge_speak("Here is your image, Sir.", player)
        else:
            edge_speak("Sir, I couldn't generate the image right now.", player)
        return

    # 2. LinkedIn Post
    if platform == "linkedin":
        create_linkedin_post(parameters, response, player, session_memory)
        return

    # 3. Text/Essay (Fallthrough)
    edge_speak("I can best help with LinkedIn posts or Images right now. For essays, I'll just write them in the chat.", player)
