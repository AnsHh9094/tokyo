
# Validated WinRT Media Control
import asyncio
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

async def get_media_session():
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    return current_session

async def media_action(action):
    session = await get_media_session()
    if not session:
        return "No active media session found."
    
    info = await session.try_get_media_properties_async()
    title = info.title if info else "Unknown"
    artist = info.artist if info else "Unknown"
    
    if action == "play":
        await session.try_play_async()
        return f"Resumed: {title} by {artist}"
    elif action == "pause":
        await session.try_pause_async()
        return f"Paused: {title} by {artist}"
    elif action == "next":
        await session.try_skip_next_async()
        return f"Skipped: {title}"
    elif action == "previous":
        await session.try_skip_previous_async()
        return f"Previous track: {title}"
    
    return "Unknown action."

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "pause"
    print( asyncio.run(media_action(action)) )
