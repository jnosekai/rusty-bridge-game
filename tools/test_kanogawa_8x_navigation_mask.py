#!/usr/bin/env python3
"""Regression checks for the 12-tile high-resolution navigation mask."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
MASK_PATH = ROOT / "kanogawa-8x-map" / "navigation-mask.png"


def sample(mask: Image.Image, x_percent: float, y_percent: float) -> bool:
    x = min(mask.width - 1, int(mask.width * x_percent / 100))
    y = min(mask.height - 1, int(mask.height * y_percent / 100))
    return mask.getpixel((x, y)) >= 128


def main() -> None:
    with Image.open(MASK_PATH) as source:
        mask = source.convert("L")

    assert mask.size == (1122, 1402)
    colors = mask.getcolors(maxcolors=256)
    assert colors is not None
    assert {value for _, value in colors} <= {0, 255}

    connected = mask.copy()
    ImageDraw.floodfill(
        connected,
        (
            round(mask.width * 33.3 / 100),
            round(mask.height * 24.3 / 100),
        ),
        128,
        thresh=0,
    )
    connected_pixels = np.asarray(connected)
    assert not np.any(connected_pixels == 255), (
        "all navigable water must belong to the dock-connected lake"
    )

    expected_water = {
        "dock start": (33.3, 24.3),
        "dock exit": (34.0, 27.0),
        "upper central lake": (45.0, 16.0),
        "middle lake": (52.0, 42.0),
        "lower river": (48.0, 82.0),
    }
    expected_blocked = {
        "upper left forest": (8.0, 8.0),
        "central island": (55.0, 40.0),
        "left forest": (24.0, 50.0),
        "right forest": (78.0, 50.0),
        "lower right forest": (72.0, 82.0),
    }

    for label, point in expected_water.items():
        assert sample(mask, *point), f"expected water: {label} {point}"
    for label, point in expected_blocked.items():
        assert not sample(mask, *point), f"expected blocked: {label} {point}"

    print("12-tile navigation mask checks passed")


if __name__ == "__main__":
    main()
