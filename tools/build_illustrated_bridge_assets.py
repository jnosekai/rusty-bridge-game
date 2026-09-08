#!/usr/bin/env python3
"""Extract the approved illustrated bridge concept into runtime layers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "kanogawa-8x-map"
BRIDGE_DIR = MAP_DIR / "bridge"
CONCEPT_PATH = BRIDGE_DIR / "kanogawa-final-08-bridge-concept.png"
BASE_TILE_PATH = MAP_DIR / "bleed" / "kanogawa-final-08.png"
MASTER_PATH = MAP_DIR / "kanogawa-map-no-bridge-8x.png"

MASTER_SIZE = (4488, 5608)
TILE_SIZE = (1496, 1402)
TILE_08_ORIGIN = (1496, 2804)
BRIDGE_CROP = (690, 930, 1145, 1210)
SHADOW_OFFSET = (4, 8)


def extract_foreground() -> Image.Image:
    concept = Image.open(CONCEPT_PATH).convert("RGB").crop(BRIDGE_CROP)
    base = (
        Image.open(BASE_TILE_PATH)
        .convert("RGB")
        .crop((0, 0, *TILE_SIZE))
        .crop(BRIDGE_CROP)
    )
    rgb = np.asarray(concept).astype(np.int16)
    original = np.asarray(base).astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    difference = np.max(np.abs(rgb - original), axis=2)

    # The bridge is the only warm, changed object inside this tight diagonal
    # envelope. Water gaps between floorboards remain genuinely transparent.
    warm_bridge = (
        (difference >= 11)
        & (red >= 45)
        & (red - blue >= 18)
        & (red * 100 >= green * 103)
        & (green * 100 >= blue * 104)
    )
    envelope = Image.new("L", concept.size, 0)
    ImageDraw.Draw(envelope).polygon(
        [(31, 147), (384, 15), (432, 82), (72, 238)],
        fill=255,
    )
    mask = Image.fromarray((warm_bridge * 255).astype(np.uint8), mode="L")
    mask = mask.filter(ImageFilter.MaxFilter(3))
    mask = ImageChops.multiply(mask, envelope)
    mask = mask.filter(ImageFilter.GaussianBlur(0.55))

    foreground = concept.convert("RGBA")
    foreground.putalpha(mask)
    return foreground


def create_shadow(alpha: Image.Image) -> Image.Image:
    shadow_alpha = alpha.filter(ImageFilter.MaxFilter(5))
    shadow_alpha = shadow_alpha.filter(ImageFilter.GaussianBlur(3.0))
    shadow_alpha = shadow_alpha.point(lambda value: round(value * 0.22))
    shadow = Image.new("RGBA", alpha.size, (18, 31, 37, 0))
    shadow.putalpha(shadow_alpha)
    return shadow


def build_preview(
    foreground: Image.Image,
    shadow: Image.Image,
    placement: dict,
) -> None:
    master = Image.open(MASTER_PATH).convert("RGBA")
    master.alpha_composite(
        shadow,
        (
            placement["shadow"]["x"],
            placement["shadow"]["y"],
        ),
    )
    master.alpha_composite(
        foreground,
        (
            placement["foreground"]["x"],
            placement["foreground"]["y"],
        ),
    )
    detail = master.crop((2070, 3620, 2760, 4240))
    detail.save(BRIDGE_DIR / "kanogawa-bridge-detail-preview.png", optimize=True)
    master.crop((2110, 3780, 2390, 4070)).save(
        BRIDGE_DIR / "kanogawa-bridge-left-connection-preview.png",
        optimize=True,
    )
    master.crop((2460, 3650, 2740, 3940)).save(
        BRIDGE_DIR / "kanogawa-bridge-right-connection-preview.png",
        optimize=True,
    )
    overview = master.convert("RGB").resize(
        (1122, 1402),
        Image.Resampling.LANCZOS,
    )
    overview.save(MAP_DIR / "kanogawa-minimap.png", optimize=True)
    overview.save(
        BRIDGE_DIR / "kanogawa-bridge-composite-preview.jpg",
        quality=92,
        optimize=True,
    )


def main() -> None:
    foreground = extract_foreground()
    shadow = create_shadow(foreground.getchannel("A"))
    foreground_path = BRIDGE_DIR / "rusty-bridge-illustrated-foreground.png"
    shadow_path = BRIDGE_DIR / "rusty-bridge-illustrated-shadow.png"
    foreground.save(foreground_path, optimize=True)
    shadow.save(shadow_path, optimize=True)

    x = TILE_08_ORIGIN[0] + BRIDGE_CROP[0]
    y = TILE_08_ORIGIN[1] + BRIDGE_CROP[1]
    width, height = foreground.size
    placement = {
        "master": {"width": MASTER_SIZE[0], "height": MASTER_SIZE[1]},
        "source": {
            "path": "kanogawa-final-08-bridge-concept.png",
            "tile": "08",
            "crop": list(BRIDGE_CROP),
        },
        "foreground": {
            "path": foreground_path.name,
            "naturalWidth": width,
            "naturalHeight": height,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "centerX": x + width / 2,
            "centerY": y + height / 2,
            "normalizedX": (x + width / 2) / MASTER_SIZE[0],
            "normalizedY": (y + height / 2) / MASTER_SIZE[1],
        },
        "shadow": {
            "path": shadow_path.name,
            "naturalWidth": width,
            "naturalHeight": height,
            "x": x + SHADOW_OFFSET[0],
            "y": y + SHADOW_OFFSET[1],
            "width": width,
            "height": height,
            "offsetX": SHADOW_OFFSET[0],
            "offsetY": SHADOW_OFFSET[1],
            "opacity": 0.22,
            "blurSourcePixels": 3,
        },
        "passage": {
            "description": "Navigable water under the illustrated bridge",
            "x": 2290,
            "y": 3660,
            "width": 250,
            "height": 510,
        },
        "abutments": [
            {"id": "west", "centerX": 2245, "centerY": 3918, "radius": 44},
            {"id": "east", "centerX": 2582, "centerY": 3805, "radius": 44},
        ],
    }
    (BRIDGE_DIR / "rusty-bridge-placement.json").write_text(
        json.dumps(placement, indent=2) + "\n",
        encoding="utf-8",
    )
    build_preview(foreground, shadow, placement)


if __name__ == "__main__":
    main()
