from io import BytesIO

import pytest
from PIL import Image

from app.services import classifier
from app.services.labels import CLASS_NAMES


@pytest.mark.skipif(not classifier.get_settings().model_path.exists(), reason="model weights not present")
async def test_real_model_predicts_known_labels():
    buffer = BytesIO()
    Image.new("RGB", (640, 480), (60, 140, 50)).save(buffer, format="JPEG")

    predictions = await classifier.predict(buffer.getvalue(), top_k=3)

    assert len(predictions) == 3
    assert all(label in CLASS_NAMES for label, _ in predictions)
    probabilities = [p for _, p in predictions]
    assert probabilities == sorted(probabilities, reverse=True)
    assert 0 < sum(probabilities) <= 1.0001
