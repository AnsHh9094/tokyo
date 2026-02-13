"""
Weather Report Action
Uses wttr.in (free, no API key required) for weather data.
"""
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak


def weather_action(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Get weather information for a city.

    Args:
        parameters: dict with 'city' and optional 'days' keys
        response: AI response text
        player: JarvisUI instance
        session_memory: TemporaryMemory instance
    """
    city = (parameters or {}).get("city", "").strip()

    if not city:
        msg = "Sir, which city would you like the weather for?"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    try:
        # Use wttr.in for free weather data (JSON format)
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Jarvis-Assistant"})

        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")

        data = resp.json()

        # Current conditions
        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "?")
        temp_f = current.get("temp_F", "?")
        feels_like_c = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        wind_speed = current.get("windspeedKmph", "?")
        wind_dir = current.get("winddir16Point", "")

        # Build response
        weather_text = (
            f"Currently in {city}: {desc}, {temp_c}°C ({temp_f}°F), "
            f"feels like {feels_like_c}°C. "
            f"Humidity: {humidity}%, Wind: {wind_speed} km/h {wind_dir}."
        )

        # Check for forecast
        days = int((parameters or {}).get("days", 1))
        forecast_data = data.get("weather", [])

        if days > 1 and len(forecast_data) > 1:
            weather_text += " Forecast: "
            for i, day in enumerate(forecast_data[1:days], 1):
                date = day.get("date", "")
                max_temp = day.get("maxtempC", "?")
                min_temp = day.get("mintempC", "?")
                day_desc = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
                weather_text += f"Day {i}: {day_desc}, {min_temp}-{max_temp}°C. "

        spoken = response or f"Sir, {weather_text}"
        if player:
            player.write_log(f"Jarvis: {spoken}")
            player.write_log(f"  📊 {weather_text}")
        edge_speak(spoken, player)
        return True

    except Exception as e:
        print(f"❌ Weather error: {e}")
        msg = f"Sir, I couldn't retrieve the weather for {city} at the moment."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return False
