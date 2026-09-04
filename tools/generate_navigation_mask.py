#!/usr/bin/env python3
"""Generate the boat navigation mask from the 20 presentation tiles.

White pixels are navigable water; black pixels are land, shore, dock, or rock.
The tile geometry mirrors mapPresentationSettings in index.html so the mask stays
in the existing world-coordinate system.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
WORLD_SIZE = (3230, 4340)
OUTPUT_SIZE = (1615, 2170)
TILE_X = (0, 15, 39, 62)
TILE_Y = (0, 10, 28, 50, 67)
TILE_DIMENSIONS = (
    (1254, 1254), (1439, 1093), (1439, 1093), (1254, 1254),
    (1093, 1439), (1254, 1254), (1254, 1254), (1093, 1438),
    (1254, 1254), (1094, 1438), (1094, 1438), (1095, 1436),
    (1254, 1254), (1254, 1254), (1254, 1254), (1093, 1439),
    (1254, 1254), (1439, 1093), (1439, 1093), (1254, 1254),
)


def is_water(rgb: np.ndarray) -> np.ndarray:
    """Include deep and shallow cyan water while excluding green land/gray rock."""
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)

    return (
        (blue >= 58)
        & (blue - red >= 16)
        & (blue * 100 >= green * 96)
        & (blue * 100 >= red * 112)
    )


def tile_frame(index: int) -> tuple[int, int, int, int, int, int]:
    column = index % 4
    row = index // 4
    source_width, source_height = TILE_DIMENSIONS[index]
    left = round(WORLD_SIZE[0] * TILE_X[column] / 100)
    top = round(WORLD_SIZE[1] * TILE_Y[row] / 100)
    width = source_width
    height = round(WORLD_SIZE[1] * 0.33) if row == 4 else source_height
    offset_x = round(width * (-0.01 if index == 1 else -0.28 if index == 5 else 0))
    offset_y = round(height * (0.145 if index == 1 else 0.19 if index == 5 else 0))
    return left, top, width, height, offset_x, offset_y


def paste_clipped(canvas: Image.Image, tile: Image.Image, frame: tuple[int, ...]) -> None:
    left, top, width, height, offset_x, offset_y = frame
    tile = tile.resize((width, height), Image.Resampling.LANCZOS)
    destination = (left + offset_x, top + offset_y)

    crop_left = max(0, left - destination[0])
    crop_top = max(0, top - destination[1])
    crop_right = min(width, left + width - destination[0])
    crop_bottom = min(height, top + height - destination[1])
    if crop_right <= crop_left or crop_bottom <= crop_top:
        return

    cropped = tile.crop((crop_left, crop_top, crop_right, crop_bottom))
    canvas.paste(
        cropped,
        (destination[0] + crop_left, destination[1] + crop_top),
    )


def main() -> None:
    visual = Image.new("RGB", WORLD_SIZE, (18, 61, 36))

    # Normal row-major z-order first; tile 02 remains the visual foreground tile.
    order = [index for index in range(20) if index != 1] + [1]
    for index in order:
        tile_root = ROOT / "seamless-map" if index < 18 else ROOT
        path = tile_root / f"kanogawa_map_{index + 1:02d}.png"
        with Image.open(path) as source:
            paste_clipped(visual, source.convert("RGB"), tile_frame(index))

    visual = visual.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    water = is_water(np.asarray(visual))
    mask = Image.fromarray((water * 255).astype(np.uint8), mode="L")

    # Remove isolated colored noise, bridge tiny submerged-rock holes, then allow
    # a two-pixel shore tolerance for forgiving center-point boat movement.
    mask = mask.filter(ImageFilter.MedianFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.point(lambda value: 255 if value >= 128 else 0)
    mask.save(ROOT / "navigation-mask.png", optimize=True)


if __name__ == "__main__":
    main()
