"""Scores photos with the CLIP leaf check, to choose LEAF_CHECK_THRESHOLD before enabling it.

Usage (from Backend/):  python -m scripts.check_leaf photo1.jpg photo2.png ...
The first run downloads the model (~600 MB) to the Hugging Face cache.
"""

import sys
import time
from pathlib import Path

from app.config import get_settings
from app.services.leaf_check import plant_probability_sync


def main(paths: list[str]) -> None:
    if not paths:
        sys.exit(__doc__)
    threshold = get_settings().leaf_check_threshold
    for path in paths:
        started = time.perf_counter()
        probability = plant_probability_sync(Path(path).read_bytes())
        verdict = "plant" if probability >= threshold else "REJECT"
        print(f"{probability:6.3f}  {verdict:6}  {(time.perf_counter() - started) * 1000:5.0f} ms  {path}")
    print(f"\nThreshold: {threshold} (set LEAF_CHECK_THRESHOLD in .env)")


if __name__ == "__main__":
    main(sys.argv[1:])
