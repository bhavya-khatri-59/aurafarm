"""Inspect or clear the persistent caches (stored in data/aurafarm.db).

Usage (from Backend/):
  python -m scripts.cache list
  python -m scripts.cache clear [--responses | --remedies]
"""

import argparse
import asyncio

from sqlalchemy import delete, select

from app.db import create_tables, init_engine, session_factory
from app.models import RemedyCache, ResponseCache


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["list", "clear"])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--responses", action="store_true", help="only the photo reply cache")
    group.add_argument("--remedies", action="store_true", help="only the per-disease research cache")
    args = parser.parse_args()

    init_engine()
    await create_tables()
    async with session_factory()() as session:
        if args.action == "list":
            responses = (await session.scalars(select(ResponseCache).order_by(ResponseCache.created_at))).all()
            print(f"{len(responses)} cached photo replies:")
            for r in responses:
                name = (r.diagnosis or {}).get("name", "no diagnosis")
                print(f"  {r.image_hash}  {r.created_at:%Y-%m-%d %H:%M}  {name:32}  text={r.text!r}")
            remedies = (await session.scalars(select(RemedyCache).order_by(RemedyCache.label))).all()
            print(f"\n{len(remedies)} cached remedy research entries:")
            for r in remedies:
                print(f"  {r.label:50} {r.created_at:%Y-%m-%d %H:%M}")
            return
        if not args.remedies:
            await session.execute(delete(ResponseCache))
        if not args.responses:
            await session.execute(delete(RemedyCache))
        await session.commit()
        print("Cleared.")


if __name__ == "__main__":
    asyncio.run(main())
