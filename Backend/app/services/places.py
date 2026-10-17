"""Nearby places a farmer can get help from, via the OpenStreetMap Overpass API."""

import logging
import time

import httpx

from app.config import get_settings
from app.services.geo import haversine_km

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 6 * 60 * 60
_cache: dict[tuple[float, float, str], tuple[float, list[dict]]] = {}

# OSM has no single tag for "agricultural help", so this casts a few nets.
_QUERIES = {
    "agri_supplies": [
        'nwr["shop"~"^(agrarian|farm|garden_centre)$"]',
    ],
    "expert_help": [
        'nwr["name"~"Krishi Vigyan Kendra|KVK|Agricultur|Krishi|Plant Clinic|Extension",i]',
        'nwr["office"="government"]["government"~"agricultur",i]',
        'nwr["office"="research"]["name"~"agricultur",i]',
    ],
}


def _category(tags: dict) -> str:
    if tags.get("shop") in {"agrarian", "farm"}:
        return "Agri-input shop"
    if tags.get("shop") == "garden_centre":
        return "Garden centre"
    if tags.get("office") == "government":
        return "Agriculture office"
    if tags.get("office") == "research":
        return "Research station"
    return "Agricultural service"


def _build_query(lat: float, lon: float, radius_m: int, kind: str) -> str:
    selectors = _QUERIES["agri_supplies"] + _QUERIES["expert_help"] if kind == "all" else _QUERIES[kind]
    body = "".join(f"{s}(around:{radius_m},{lat},{lon});" for s in selectors)
    return f"[out:json][timeout:20];({body});out center tags 60;"


def _parse(elements: list[dict], lat: float, lon: float) -> list[dict]:
    places = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        el_lat = el.get("lat") or el.get("center", {}).get("lat")
        el_lon = el.get("lon") or el.get("center", {}).get("lon")
        if not name or el_lat is None or el_lon is None:
            continue
        places.append(
            {
                "name": name,
                "category": _category(tags),
                "distance_km": round(haversine_km(lat, lon, el_lat, el_lon), 1),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "address": ", ".join(
                    tags[k] for k in ("addr:street", "addr:city") if tags.get(k)
                ) or None,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={el_lat},{el_lon}",
            }
        )
    places.sort(key=lambda p: p["distance_km"])
    return places


async def find_nearby_places(lat: float, lon: float, kind: str = "all", limit: int = 6) -> list[dict]:
    """kind is "all", "agri_supplies" or "expert_help". Returns [] when the lookup fails."""
    settings = get_settings()
    key = (round(lat, 2), round(lon, 2), kind)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1][:limit]

    query = _build_query(lat, lon, int(settings.places_radius_km * 1000), kind)
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(settings.overpass_url, data={"data": query})
            response.raise_for_status()
            elements = response.json().get("elements", [])
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Overpass lookup failed: %s", e)
        return []

    places = _parse(elements, lat, lon)
    _cache[key] = (time.monotonic(), places)
    return places[:limit]
