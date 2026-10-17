"""Deterministic diagnosis node: classifier + weather + community outbreaks + nearby places."""

import asyncio
from collections.abc import Awaitable, Callable

from langgraph.config import get_stream_writer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.state import AgentState
from app.config import get_settings
from app.services import classifier, community, places, weather
from app.services.labels import get_label

ImageLoader = Callable[[str], Awaitable[bytes]]


async def _none() -> None:
    return None


def make_diagnosis_node(sessions: async_sessionmaker[AsyncSession], load_image: ImageLoader):
    async def diagnose(state: AgentState) -> dict:
        settings = get_settings()
        write = get_stream_writer()
        location = state.get("location")
        user_id = state["user_id"]

        write({"type": "status", "text": "Analyzing the leaf image…"})
        predictions = await classifier.predict(await load_image(state["image_id"]), top_k=3)
        top_label, top_confidence = predictions[0]
        plant = get_label(top_label)
        confident = top_confidence >= settings.confidence_threshold

        if location:
            write({"type": "status", "text": "Checking local weather and reports from nearby farmers…"})
        lat, lon = (location["lat"], location["lon"]) if location else (None, None)
        async with sessions() as session:
            weather_data, outbreaks, nearby = await asyncio.gather(
                weather.get_weather(lat, lon) if location else _none(),
                community.nearby_outbreaks(session, lat, lon, exclude_user_id=user_id)
                if location else _none(),
                places.find_nearby_places(lat, lon)
                if location and confident and not plant.is_healthy else _none(),
            )
            if location and confident and not plant.is_healthy:
                await community.record_report(session, user_id, top_label, top_confidence, lat, lon)

        diagnosis = {
            "status": "confident" if confident else "uncertain",
            "label": top_label,
            "name": plant.display,
            "crop": plant.crop,
            "disease": plant.disease,
            "is_healthy": plant.is_healthy,
            "confidence": round(top_confidence, 3),
            "alternatives": [
                {"label": label, "name": get_label(label).display, "confidence": round(p, 3)}
                for label, p in predictions[1:]
            ],
            "weather": weather_data,
            "outbreaks": outbreaks,
            "nearby_places": nearby,
            "location_available": location is not None,
        }
        write({"type": "diagnosis", "diagnosis": diagnosis})
        return {"diagnosis": diagnosis, "new_diagnosis": True, "image_id": None}

    return diagnose
