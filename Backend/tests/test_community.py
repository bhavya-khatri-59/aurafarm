from app.db import session_factory
from app.services import community


async def test_outbreaks_within_radius_excluding_self(db):
    async with session_factory()() as session:
        await community.record_report(session, 1, "Tomato___Late_blight", 0.9, 12.970, 77.590)
        await community.record_report(session, 2, "Tomato___Late_blight", 0.9, 12.990, 77.600)  # ~2.5 km
        await community.record_report(session, 3, "Tomato___Early_blight", 0.9, 12.975, 77.595)
        await community.record_report(session, 4, "Tomato___Late_blight", 0.9, 13.500, 77.590)  # ~59 km

        summary = await community.nearby_outbreaks(session, 12.97, 77.59, exclude_user_id=1)

    assert summary["total_reports"] == 2
    assert {d["label"]: d["reports"] for d in summary["by_disease"]} == {
        "Tomato___Late_blight": 1,
        "Tomato___Early_blight": 1,
    }
