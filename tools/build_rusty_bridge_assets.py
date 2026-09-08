#!/usr/bin/env python3
"""Build the separate bridge layers from the supplied transparent source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "kanogawa-8x-map"
BRIDGE_DIR = MAP_DIR / "bridge"
SOURCE_PATH = MAP_DIR / "rusty-bridge-foreground-source.png"
MASTER_PATH = MAP_DIR / "kanogawa-map-no-bridge-8x.png"
SHADOW_PATH = BRIDGE_DIR / "rusty-bridge-shadow.png"
PLACEMENT_PATH = BRIDGE_DIR / "rusty-bridge-placement.json"

MASTER_WIDTH, MASTER_HEIGHT = 4488, 5608
VISIBLE_BRIDGE_X, VISIBLE_BRIDGE_Y = 2145, 3780
VISIBLE_BRIDGE_WIDTH, VISIBLE_BRIDGE_HEIGHT = 520, 269
FOREGROUND_X, FOREGROUND_Y = 2121, 3773
FOREGROUND_WIDTH, FOREGROUND_HEIGHT = 590, 295
SHADOW_OFFSET_X, SHADOW_OFFSET_Y = 6, 14
SHADOW_OPACITY = 0.25
SHADOW_BLUR_PIXELS = 3
SHADOW_PADDING = 12


def clean_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    visible = alpha.point(lambda value: 255 if value else 0)
    empty = Image.new("L", rgba.size, 0)
    return Image.merge("RGBA", (
        Image.composite(red, empty, visible),
        Image.composite(green, empty, visible),
        Image.composite(blue, empty, visible),
        alpha,
    ))


def build_foreground() -> tuple[Image.Image, tuple[int, int, int, int], tuple[int, int]]:
    source = Image.open(SOURCE_PATH).convert("RGBA")
    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise ValueError("Bridge source has no visible pixels")
    foreground = source.resize(
        (FOREGROUND_WIDTH, FOREGROUND_HEIGHT), Image.Resampling.LANCZOS
    )
    return foreground, alpha_bbox, source.size


def build_shadow(foreground: Image.Image) -> Image.Image:
    alpha = Image.new(
        "L",
        (foreground.width + SHADOW_PADDING * 2, foreground.height + SHADOW_PADDING * 2),
        0,
    )
    alpha.paste(foreground.getchannel("A"), (SHADOW_PADDING, SHADOW_PADDING))
    alpha = alpha.filter(ImageFilter.GaussianBlur(SHADOW_BLUR_PIXELS))
    alpha = alpha.point(lambda value: round(value * SHADOW_OPACITY))
    shadow = Image.new("RGBA", alpha.size, (14, 24, 34, 0))
    shadow.putalpha(alpha)
    shadow = clean_transparent_rgb(shadow)
    shadow.save(SHADOW_PATH, optimize=True)
    return shadow


def placement_data(
    foreground: Image.Image,
    shadow: Image.Image,
    source_bbox: tuple[int, int, int, int],
    source_size: tuple[int, int],
) -> dict:
    center_x = VISIBLE_BRIDGE_X + VISIBLE_BRIDGE_WIDTH / 2
    center_y = VISIBLE_BRIDGE_Y + VISIBLE_BRIDGE_HEIGHT / 2
    return {
        "master": {"width": MASTER_WIDTH, "height": MASTER_HEIGHT},
        "source": {
            "path": "../rusty-bridge-foreground-source.png",
            "alphaBoundingBox": list(source_bbox),
            "width": source_size[0],
            "height": source_size[1],
        },
        "foreground": {
            "path": "../rusty-bridge-foreground-source.png",
            "naturalWidth": source_size[0],
            "naturalHeight": source_size[1],
            "x": FOREGROUND_X,
            "y": FOREGROUND_Y,
            "width": FOREGROUND_WIDTH,
            "height": FOREGROUND_HEIGHT,
            "centerX": center_x,
            "centerY": center_y,
            "normalizedX": center_x / MASTER_WIDTH,
            "normalizedY": center_y / MASTER_HEIGHT,
        },
        "shadow": {
            "path": "rusty-bridge-shadow.png",
            "naturalWidth": shadow.width,
            "naturalHeight": shadow.height,
            "x": FOREGROUND_X - SHADOW_PADDING + SHADOW_OFFSET_X,
            "y": FOREGROUND_Y - SHADOW_PADDING + SHADOW_OFFSET_Y,
            "width": shadow.width,
            "height": shadow.height,
            "offsetX": SHADOW_OFFSET_X,
            "offsetY": SHADOW_OFFSET_Y,
            "opacity": SHADOW_OPACITY,
            "blurSourcePixels": SHADOW_BLUR_PIXELS,
        },
        "passage": {
            "description": "Navigable water under the bridge deck",
            "x": 2250,
            "y": 3650,
            "width": 260,
            "height": 520,
        },
        "abutments": [
            {"id": "west", "centerX": 2188, "centerY": 3958, "radius": 54},
            {"id": "east", "centerX": 2572, "centerY": 3888, "radius": 54},
        ],
    }


def render_composite(
    master: Image.Image, foreground: Image.Image, shadow: Image.Image
) -> Image.Image:
    composite = master.copy().convert("RGBA")
    composite.alpha_composite(
        shadow,
        (FOREGROUND_X - SHADOW_PADDING + SHADOW_OFFSET_X,
         FOREGROUND_Y - SHADOW_PADDING + SHADOW_OFFSET_Y),
    )
    composite.alpha_composite(foreground, (FOREGROUND_X, FOREGROUND_Y))
    return composite


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--update-minimap",
        action="store_true",
        help="Update the game minimap after browser validation succeeds.",
    )
    args = parser.parse_args()

    BRIDGE_DIR.mkdir(exist_ok=True)
    master = Image.open(MASTER_PATH).convert("RGBA")
    if master.size != (MASTER_WIDTH, MASTER_HEIGHT):
        raise ValueError(f"Unexpected master size: {master.size}")
    foreground, source_bbox, source_size = build_foreground()
    shadow = build_shadow(foreground)
    PLACEMENT_PATH.write_text(
        json.dumps(
            placement_data(foreground, shadow, source_bbox, source_size), indent=2
        ) + "\n",
        encoding="utf-8",
    )

    composite = render_composite(master, foreground, shadow)
    composite.resize((1122, 1402), Image.Resampling.LANCZOS).convert("RGB").save(
        BRIDGE_DIR / "kanogawa-bridge-composite-preview.jpg",
        quality=93,
        subsampling=0,
    )
    composite.crop((1900, 3450, 2900, 4300)).save(
        BRIDGE_DIR / "kanogawa-bridge-detail-preview.png", optimize=True
    )
    if args.update_minimap:
        composite.resize((1122, 1402), Image.Resampling.LANCZOS).save(
            MAP_DIR / "kanogawa-minimap.png", optimize=True
        )
    print(f"Built bridge assets at {BRIDGE_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
