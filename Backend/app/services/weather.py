"""Current conditions and a short forecast from WeatherAPI.com."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"


async def get_weather(lat: float, lon: float) -> dict:
    settings = get_settings()
    if not settings.weather_api_key:
        return {"error": "Weather service is not configured"}

    params = {"key": settings.weather_api_key, "q": f"{lat},{lon}", "days": 3}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FORECAST_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.warning("Weather lookup failed: %s", e)
        return {"error": "Weather data is currently unavailable"}

    current = data.get("current", {})
    location = data.get("location", {})
    forecast = [
        {
            "date": day.get("date"),
            "max_temp_c": day["day"].get("maxtemp_c"),
            "min_temp_c": day["day"].get("mintemp_c"),
            "avg_humidity": day["day"].get("avghumidity"),
            "chance_of_rain": day["day"].get("daily_chance_of_rain"),
            "total_precip_mm": day["day"].get("totalprecip_mm"),
            "condition": day["day"].get("condition", {}).get("text"),
        }
        for day in data.get("forecast", {}).get("forecastday", [])
    ]
    return {
        "location": ", ".join(p for p in (location.get("name"), location.get("region")) if p),
        "temp_c": current.get("temp_c"),
        "humidity": current.get("humidity"),
        "condition": current.get("condition", {}).get("text"),
        "wind_kph": current.get("wind_kph"),
        "precip_mm": current.get("precip_mm"),
        "forecast": forecast,
    }
