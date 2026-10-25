"""External API services.

Every call to a third-party API lives in this module:
- Open-Meteo geocoding  -> turn a place name into coordinates
- Open-Meteo forecast   -> current weather and the 5-day forecast
- Open-Meteo archive    -> historical daily temperatures for a date range
- Wikipedia REST API    -> a short encyclopaedia summary of a place

All Open-Meteo APIs are free and need no API key. Functions raise
``LocationNotFound`` or ``UpstreamError`` so the API layer can turn them
into clean HTTP error responses instead of stack traces.
"""

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

TIMEOUT = httpx.Timeout(10.0)


class LocationNotFound(Exception):
    """Raised when a place name cannot be resolved to coordinates."""


class UpstreamError(Exception):
    """Raised when an external API fails or returns unusable data."""


# WMO weather codes (used by Open-Meteo) mapped to a human label and an
# emoji icon so the frontend can display conditions without its own table.
WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌦️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "🌨️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌦️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


def describe_weather(code):
    """Return (label, icon) for a WMO weather code."""
    return WEATHER_CODES.get(code, ("Unknown conditions", "❓"))


def _get_json(url, params):
    """GET a URL and return parsed JSON, raising UpstreamError on failure."""
    try:
        response = httpx.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"Weather service request failed: {exc}") from exc


def geocode_location(query):
    """Resolve a place name to the best-matching location.

    The geocoding API ranks results by relevance/population, so taking the
    first result gives a sensible "fuzzy" match for partial or misspelled
    input. Returns a dict with name, country, latitude and longitude.
    """
    data = _get_json(
        GEOCODING_URL,
        {"name": query, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results")
    if not results:
        raise LocationNotFound(f"Location '{query}' could not be found")
    place = results[0]
    return {
        "name": place["name"],
        "country": place.get("country"),
        "admin1": place.get("admin1"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


def fetch_current_weather(latitude, longitude):
    """Current weather for a coordinate pair, in a display-ready shape."""
    data = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "weather_code,wind_speed_10m,wind_direction_10m"
            ),
            "timezone": "auto",
        },
    )
    current = data.get("current")
    if not current:
        raise UpstreamError("Weather service returned no current conditions")
    label, icon = describe_weather(current.get("weather_code"))
    return {
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_direction": current.get("wind_direction_10m"),
        "weather_code": current.get("weather_code"),
        "condition": label,
        "icon": icon,
        "observed_at": current.get("time"),
        "timezone": data.get("timezone"),
    }


def fetch_forecast(latitude, longitude, days=5):
    """Daily forecast for the next ``days`` days (starting today)."""
    data = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": days,
        },
    )
    daily = data.get("daily")
    if not daily:
        raise UpstreamError("Weather service returned no forecast")
    forecast = []
    for i, day in enumerate(daily["time"]):
        label, icon = describe_weather(daily["weather_code"][i])
        forecast.append(
            {
                "date": day,
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_probability": (
                    daily["precipitation_probability_max"][i]
                    if daily.get("precipitation_probability_max")
                    else None
                ),
                "weather_code": daily["weather_code"][i],
                "condition": label,
                "icon": icon,
            }
        )
    return forecast


def fetch_archive_temperatures(latitude, longitude, start_date, end_date):
    """Temperature summary for a historical date range.

    Uses the Open-Meteo archive API and condenses the daily series into
    an average (of daily means), minimum (of daily minimums) and maximum
    (of daily maximums). Days the archive has no data for yet (it lags a
    few days behind real time) arrive as nulls and are skipped.
    """
    data = _get_json(
        ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
        },
    )
    daily = data.get("daily") or {}
    means = [v for v in daily.get("temperature_2m_mean", []) if v is not None]
    maxs = [v for v in daily.get("temperature_2m_max", []) if v is not None]
    mins = [v for v in daily.get("temperature_2m_min", []) if v is not None]
    if not means:
        raise UpstreamError(
            "No archived weather data is available for that date range yet"
        )
    return {
        "avg_temp": round(sum(means) / len(means), 2),
        "min_temp": min(mins) if mins else None,
        "max_temp": max(maxs) if maxs else None,
        "days_with_data": len(means),
    }


def fetch_wikipedia_summary(title):
    """Short Wikipedia summary for a place name, or None if there is none.

    Wikipedia is a nice-to-have extra, so failures are swallowed and
    reported as None rather than failing the whole request.
    """
    try:
        response = httpx.get(
            f"{WIKIPEDIA_SUMMARY_URL}/{title.replace(' ', '_')}",
            timeout=TIMEOUT,
            # Wikipedia's API policy requires a descriptive User-Agent;
            # the default library one is rejected with HTTP 403.
            headers={
                "Accept": "application/json",
                "User-Agent": "WeatherApp/1.0 (PM Accelerator assessment project)",
            },
            follow_redirects=True,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        if data.get("type") == "disambiguation":
            return None
        return {
            "title": data.get("title"),
            "extract": data.get("extract"),
            "url": data.get("content_urls", {})
            .get("desktop", {})
            .get("page"),
            "thumbnail": (data.get("thumbnail") or {}).get("source"),
        }
    except httpx.HTTPError:
        return None


def build_location_info(place):
    """Assemble the "location info" payload for a resolved place.

    Combines the Wikipedia summary with an OpenStreetMap embed URL and a
    YouTube search link, so the frontend can show extra context about the
    searched location (the "additional API integration" part of the brief).
    """
    summary = fetch_wikipedia_summary(place["name"])
    lat, lon = place["latitude"], place["longitude"]
    # A small bounding box around the point makes the OSM embed zoom in
    # on the place instead of showing the whole world.
    delta = 0.05
    bbox = f"{lon - delta}%2C{lat - delta}%2C{lon + delta}%2C{lat + delta}"
    return {
        "name": place["name"],
        "country": place.get("country"),
        "latitude": lat,
        "longitude": lon,
        "wikipedia": summary,
        "map_embed_url": (
            f"https://www.openstreetmap.org/export/embed.html"
            f"?bbox={bbox}&layer=mapnik&marker={lat}%2C{lon}"
        ),
        "youtube_search_url": (
            "https://www.youtube.com/results?search_query="
            + f"{place['name']} travel".replace(" ", "+")
        ),
    }
