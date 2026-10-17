"""Adds clearly-labelled demo disease reports around a location, so outbreak alerts can be shown
before real users exist. The assistant tells farmers when counts include demo data.

Usage (from Backend/):  python -m scripts.seed_demo_reports --lat 12.97 --lon 77.59 [--clear]
"""

import argparse
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db import create_tables, init_engine, session_factory
from app.models import DiseaseReport
from app.services.geo import coarsen
from app.services.labels import CLASS_NAMES, get_label

DISEASED = [label for label in CLASS_NAMES if not get_label(label).is_healthy]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--labels", nargs="*", default=["Tomato___Late_blight", "Tomato___Early_blight", "Potato___Late_blight"])
    parser.add_argument("--clear", action="store_true", help="remove all existing demo reports first")
    args = parser.parse_args()

    init_engine()
    await create_tables()
    async with session_factory()() as session:
        if args.clear:
            await session.execute(delete(DiseaseReport).where(DiseaseReport.is_demo.is_(True)))
        now = datetime.now(timezone.utc)
        for _ in range(args.count):
            label = random.choice(args.labels or DISEASED)
            plant = get_label(label)
            session.add(
                DiseaseReport(
                    user_id=None,
                    label=label,
                    crop=plant.crop,
                    disease=plant.disease,
                    lat=coarsen(args.lat + random.uniform(-0.06, 0.06)),
                    lon=coarsen(args.lon + random.uniform(-0.06, 0.06)),
                    confidence=round(random.uniform(0.75, 0.99), 3),
                    is_demo=True,
                    created_at=now - timedelta(days=random.randint(0, 10)),
                )
            )
        await session.commit()
    print(f"Added {args.count} demo reports near ({args.lat}, {args.lon}).")


if __name__ == "__main__":
    asyncio.run(main())
