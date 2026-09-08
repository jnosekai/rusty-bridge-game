#!/usr/bin/env python3
"""Build the 12-tile map's deterministic boat-navigation mask.

White is navigable water and black is blocked terrain. The mask is kept at the
1122 x 1402 reference-map scale so it maps directly to the 4488 x 5608 master.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "kanogawa-8x-map" / "kanogawa-map-no-bridge-8x.png"
OUTPUT = ROOT / "kanogawa-8x-map" / "navigation-mask.png"
OUTPUT_SIZE = (1122, 1402)
DOCK_PERCENT = (33.3, 24.3)

# A boat is allowed only when its center is this many mask pixels inside water.
# One mask pixel represents exactly four source-map pixels.
SHORE_CLEARANCE_PIXELS = 4


def classify_water(rgb: np.ndarray) -> np.ndarray:
    """Select blue/cyan water, including bright shallows and submerged detail."""
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)

    blue_water = (
        (blue >= 78)
        & (blue - red >= 14)
        & (blue * 100 >= green * 91)
        & (green - red >= 3)
    )
    bright_shallow_water = (
        (blue >= 145)
        & (green >= 125)
        & (blue - red >= 7)
        & (green - red >= 10)
        & (blue * 100 >= green * 94)
    )
    return blue_water | bright_shallow_water


def keep_dock_connected_water(mask: Image.Image) -> Image.Image:
    """Discard blue-looking terrain that is not connected to the main lake."""
    seed = (
        round(mask.width * DOCK_PERCENT[0] / 100),
        round(mask.height * DOCK_PERCENT[1] / 100),
    )
    connected = mask.copy()
    ImageDraw.floodfill(connected, seed, 128, thresh=0)
    pixels = np.asarray(connected)
    return Image.fromarray(
        np.where(pixels == 128, 255, 0).astype(np.uint8),
        mode="L",
    )


def main() -> None:
    with Image.open(SOURCE) as source:
        visual = source.convert("RGB").resize(
            OUTPUT_SIZE,
            Image.Resampling.LANCZOS,
        )

    water = classify_water(np.asarray(visual))
    mask = Image.fromarray((water * 255).astype(np.uint8), mode="L")

    # Normalize tiny highlights, ripples, and submerged texture before applying
    # one consistent center-point clearance from every true shore/rock boundary.
    mask = mask.filter(ImageFilter.MedianFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.MinFilter(5))
    mask = keep_dock_connected_water(mask)
    mask = mask.filter(
        ImageFilter.MinFilter(SHORE_CLEARANCE_PIXELS * 2 + 1)
    )
    mask = keep_dock_connected_water(mask)
    mask = mask.point(lambda value: 255 if value >= 128 else 0)
    mask.save(OUTPUT, optimize=True)


if __name__ == "__main__":
    main()
