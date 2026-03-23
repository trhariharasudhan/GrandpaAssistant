import requests

from brain.memory_engine import load_memory


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snowfall",
    73: "moderate snowfall",
    75: "heavy snowfall",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def _safe_get(data, path, default=None):
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _default_location():
    memory = load_memory()
    city = _safe_get(memory, "personal.location.current_location.city")
    state = _safe_get(memory, "personal.location.current_location.state")
    country = _safe_get(memory, "personal.location.current_location.country")
    parts = [part for part in [city, state, country] if part]
    return ", ".join(parts) if parts else "Salem, India"


def _extract_location(command):
    command = command.lower().strip()

    if "weather in " in command:
        return command.split("weather in ", 1)[1].strip()

    if "forecast in " in command:
        return command.split("forecast in ", 1)[1].strip()

    if command in ["weather", "what is the weather", "today weather", "weather today"]:
        return _default_location()

    if "weather" in command:
        return _default_location()

    return None


def _geocode_location(location_name):
    response = requests.get(
        GEOCODE_URL,
        params={"name": location_name, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        return None
    return results[0]


def _fetch_weather(latitude, longitude):
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _weather_label(code):
    return WEATHER_CODES.get(code, "unknown weather")


def get_weather_report(command):
    location_name = _extract_location(command)
    if not location_name:
        return None

    try:
        place = _geocode_location(location_name)
        if not place:
            return f"I could not find weather information for {location_name}."

        weather = _fetch_weather(place["latitude"], place["longitude"])
        current = weather.get("current", {})
        daily = weather.get("daily", {})

        resolved_name = place.get("name", location_name)
        admin = place.get("admin1")
        country = place.get("country")
        resolved_parts = [part for part in [resolved_name, admin, country] if part]
        resolved_location = ", ".join(resolved_parts)

        temperature = current.get("temperature_2m")
        feels_like = current.get("apparent_temperature")
        weather_code = current.get("weather_code")
        wind_speed = current.get("wind_speed_10m")
        max_temp = (daily.get("temperature_2m_max") or [None])[0]
        min_temp = (daily.get("temperature_2m_min") or [None])[0]

        parts = [f"The current weather in {resolved_location} is {_weather_label(weather_code)}."]

        if temperature is not None:
            parts.append(f"Temperature is {temperature} degree Celsius.")
        if feels_like is not None:
            parts.append(f"It feels like {feels_like} degree Celsius.")
        if max_temp is not None and min_temp is not None:
            parts.append(f"Today's range is {min_temp} to {max_temp} degree Celsius.")
        if wind_speed is not None:
            parts.append(f"Wind speed is {wind_speed} kilometers per hour.")

        return " ".join(parts)
    except requests.RequestException:
        return "I could not fetch weather right now. Please check your internet connection and try again."
