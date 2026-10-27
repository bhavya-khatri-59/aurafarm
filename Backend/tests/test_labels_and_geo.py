import json
from pathlib import Path

from app.services.geo import bounding_box, coarsen, haversine_km
from app.services.labels import CLASS_NAMES, LABELS

BACKEND = Path(__file__).resolve().parent.parent


def test_labels_match_model_class_order():
    assert len(CLASS_NAMES) == 38
    seed = json.loads((BACKEND / "kb" / "remedies_seed.json").read_text())
    assert set(seed) == set(CLASS_NAMES)


def test_label_normalization():
    label = LABELS["Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"]
    assert (label.crop, label.disease) == ("corn", "gray_leaf_spot")
    assert LABELS["Tomato___healthy"].is_healthy
    assert LABELS["Pepper,_bell___Bacterial_spot"].display == "Bell pepper bacterial spot"
    assert LABELS["Apple___Apple_scab"].display == "Apple scab"
    assert LABELS["Apple___Cedar_apple_rust"].display == "Cedar apple rust"
    assert LABELS["Tomato___Late_blight"].display == "Tomato late blight"
    assert LABELS["Orange___Haunglongbing_(Citrus_greening)"].display == "Orange citrus greening (HLB)"


def test_geo_helpers():
    # Bengaluru to Mysuru is roughly 128 km as the crow flies.
    assert 120 < haversine_km(12.97, 77.59, 12.30, 76.64) < 135
    min_lat, max_lat, min_lon, max_lon = bounding_box(12.97, 77.59, 10)
    assert min_lat < 12.97 < max_lat and min_lon < 77.59 < max_lon
    assert coarsen(12.345678) == 12.35
