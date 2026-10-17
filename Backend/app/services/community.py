"""Community outbreak signal: confident diagnoses from other users near the farmer."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import DiseaseReport
from app.services.geo import bounding_box, coarsen, haversine_km
from app.services.labels import get_label


async def record_report(
    session: AsyncSession, user_id: int, label: str, confidence: float, lat: float, lon: float
) -> None:
    plant = get_label(label)
    session.add(
        DiseaseReport(
            user_id=user_id,
            label=label,
            crop=plant.crop,
            disease=plant.disease,
            lat=coarsen(lat),
            lon=coarsen(lon),
            confidence=confidence,
        )
    )
    await session.commit()


async def nearby_outbreaks(
    session: AsyncSession, lat: float, lon: float, exclude_user_id: int | None = None
) -> dict:
    """Summarizes disease reports within the outbreak radius and window, excluding healthy plants."""
    settings = get_settings()
    radius = settings.outbreak_radius_km
    since = datetime.now(timezone.utc) - timedelta(days=settings.outbreak_window_days)
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius)

    query = select(DiseaseReport).where(
        DiseaseReport.lat.between(min_lat, max_lat),
        DiseaseReport.lon.between(min_lon, max_lon),
        DiseaseReport.created_at >= since,
        DiseaseReport.disease != "healthy",
    )
    if exclude_user_id is not None:
        query = query.where(
            (DiseaseReport.user_id != exclude_user_id) | DiseaseReport.user_id.is_(None)
        )
    reports = [
        r for r in (await session.scalars(query)).all()
        if haversine_km(lat, lon, r.lat, r.lon) <= radius
    ]

    counts = Counter(r.label for r in reports)
    demo_labels = {r.label for r in reports if r.is_demo}
    return {
        "radius_km": radius,
        "window_days": settings.outbreak_window_days,
        "total_reports": len(reports),
        "by_disease": [
            {
                "label": label,
                "name": get_label(label).display,
                "reports": count,
                "includes_demo_data": label in demo_labels,
            }
            for label, count in counts.most_common()
        ],
    }
