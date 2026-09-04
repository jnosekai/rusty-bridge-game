#!/usr/bin/env python3
"""Small regression checks for the generated navigation mask."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
MASK_PATH = ROOT / "navigation-mask.png"


def sample(mask: Image.Image, x_percent: float, y_percent: float) -> bool:
    x = min(mask.width - 1, int(mask.width * x_percent / 100))
    y = min(mask.height - 1, int(mask.height * y_percent / 100))
    return mask.getpixel((x, y)) >= 128


def main() -> None:
    with Image.open(MASK_PATH) as source:
        mask = source.convert("L")

    assert mask.size == (1615, 2170)
    colors = mask.getcolors(maxcolors=256)
    assert colors is not None
    assert {value for _, value in colors} <= {0, 255}

    expected_water = {
        "dock start": (33.3, 24.3),
        "dock left water": (32.5, 24.3),
        "dock right water": (34.0, 24.3),
        "deep water below dock": (33.3, 26.8),
        "shallow water beside shore": (30.4, 26.1),
        "lower narrow channel": (50.0, 80.0),
        "upper inlet": (70.0, 8.0),
    }
    expected_blocked = {
        "dock wood": (33.3, 23.8),
        "shore left of dock basin": (29.5, 26.1),
        "land below dock basin": (33.3, 28.2),
        "central forest": (45.0, 40.0),
        "lower forest": (44.0, 60.0),
    }

    for label, point in expected_water.items():
        assert sample(mask, *point), f"expected water: {label} {point}"
    for label, point in expected_blocked.items():
        assert not sample(mask, *point), f"expected blocked: {label} {point}"

    print("navigation mask checks passed")


if __name__ == "__main__":
    main()
