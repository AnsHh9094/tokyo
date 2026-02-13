"""
Web Search Action
Uses SerpAPI to perform Google searches and return results.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SERPAPI_KEY
from core.tts import edge_speak

try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False


def _get_serpapi_key() -> str:
    """Get SerpAPI key from config."""
    key = SERPAPI_KEY
    if not key:
        config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    keys = json.load(f)
                    key = keys.get("serpapi_key", "")
            except Exception:
                pass
    return key


def web_search(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Perform a web search and summarize results.

    Args:
        parameters: dict with 'query' key
        response: AI response text
        player: JarvisUI instance
        session_memory: TemporaryMemory instance
    """
    query = (parameters or {}).get("query", "").strip()

    if not query:
        msg = "Sir, what would you like me to search for?"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    api_key = _get_serpapi_key()

    if not api_key or not SERPAPI_AVAILABLE:
        # Fallback: open in browser
        import webbrowser
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        msg = response or f"Sir, I've opened a Google search for '{query}' in your browser."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    try:
        search = GoogleSearch({
            "q": query,
            "api_key": api_key,
            "num": 5
        })
        results = search.get_dict()

        # Extract answer box if available
        answer_box = results.get("answer_box", {})
        if answer_box:
            answer = answer_box.get("answer") or answer_box.get("snippet") or answer_box.get("result")
            if answer:
                msg = f"Sir, {answer}"
                if player:
                    player.write_log(f"Jarvis: {msg}")
                edge_speak(msg, player)
                return True

        # Extract organic results
        organic = results.get("organic_results", [])
        if organic:
            top = organic[0]
            title = top.get("title", "")
            snippet = top.get("snippet", "No description available")

            msg = response or f"Sir, here's what I found: {snippet}"
            if player:
                player.write_log(f"Jarvis: {msg}")
                # Show all results in log
                for i, r in enumerate(organic[:3], 1):
                    player.write_log(f"  [{i}] {r.get('title', '')} - {r.get('link', '')}")

            edge_speak(msg, player)
            return True

        msg = f"Sir, I couldn't find specific results for '{query}'."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return False

    except Exception as e:
        print(f"❌ Search error: {e}")
        # Fallback to browser
        import webbrowser
        webbrowser.open(f"https://www.google.com/search?q={query}")
        msg = f"Sir, I've opened the search in your browser instead."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True
