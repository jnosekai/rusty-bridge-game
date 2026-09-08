#!/usr/bin/env python3
"""Deterministically extract the bridge reference and build game previews."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "kanogawa-8x-map"
BRIDGE_DIR = MAP_DIR / "bridge"
REFERENCE_PATH = MAP_DIR / "kanogawa-map-with-bridge-reference.png"
MASTER_PATH = MAP_DIR / "kanogawa-map-no-bridge-8x.png"
FOREGROUND_PATH = BRIDGE_DIR / "rusty-bridge-from-map.png"
SHADOW_PATH = BRIDGE_DIR / "rusty-bridge-shadow.png"
LEFT_BANK_PATH = BRIDGE_DIR / "rusty-bridge-left-bank.png"
RIGHT_BANK_PATH = BRIDGE_DIR / "rusty-bridge-right-bank.png"
PLACEMENT_PATH = BRIDGE_DIR / "rusty-bridge-placement.json"

MASTER_WIDTH, MASTER_HEIGHT = 4488, 5608
REFERENCE_WIDTH, REFERENCE_HEIGHT = 1122, 1402
REFERENCE_SCALE = 4
REFERENCE_CROP = (540, 950, 660, 1012)
BRIDGE_X = REFERENCE_CROP[0] * REFERENCE_SCALE
BRIDGE_Y = REFERENCE_CROP[1] * REFERENCE_SCALE
BRIDGE_WIDTH = (REFERENCE_CROP[2] - REFERENCE_CROP[0]) * REFERENCE_SCALE
BRIDGE_HEIGHT = (REFERENCE_CROP[3] - REFERENCE_CROP[1]) * REFERENCE_SCALE

# Reference-space bridge silhouette. Shore pixels at both ends are excluded.
FOREGROUND_POLYGON = [(10, 31), (99, 7), (110, 10), (110, 27), (102, 34), (18, 58), (10, 52)]
SHADOW_POLYGON = [(4, 50), (107, 26), (114, 30), (109, 36), (17, 59), (4, 56)]
SHADOW_MAX_ALPHA = 30
UNSHARP_RADIUS = 0.8
UNSHARP_PERCENT = 120
UNSHARP_THRESHOLD = 2
LEFT_BANK_CROP = (2140, 3840, 2280, 4060)
LEFT_BANK_POLYGON = [(0, 0), (140, 0), (140, 220), (0, 220)]
RIGHT_BANK_CROP = (2500, 3720, 2680, 3940)
RIGHT_BANK_POLYGON = [(0, 0), (180, 0), (180, 220), (0, 220)]


def clean_transparent_rgb(image: Image.Image) -> Image.Image:
    """Clear fully transparent RGB to prevent coloured edge halos."""
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


def polygon_mask(size: tuple[int, int], points: list[tuple[int, int]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def pad_rgb_into_transparency(
    rgb: Image.Image, alpha: Image.Image, radius: int = 4
) -> Image.Image:
    """Extend nearby bridge colours under transparent edge pixels."""
    output = rgb.copy()
    source = rgb.load()
    target = output.load()
    mask = alpha.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            if mask[x, y]:
                continue
            nearest = None
            nearest_distance = radius * radius + 1
            for sample_y in range(max(0, y - radius), min(rgb.height, y + radius + 1)):
                for sample_x in range(max(0, x - radius), min(rgb.width, x + radius + 1)):
                    if not mask[sample_x, sample_y]:
                        continue
                    distance = (sample_x - x) ** 2 + (sample_y - y) ** 2
                    if distance < nearest_distance:
                        nearest = source[sample_x, sample_y]
                        nearest_distance = distance
            if nearest is not None:
                target[x, y] = nearest
    return output


def build_foreground(reference_crop: Image.Image) -> tuple[Image.Image, Image.Image]:
    rgb = reference_crop.convert("RGB")
    pixels = [
        rgb.getpixel((x, y))
        for y in range(rgb.height)
        for x in range(rgb.width)
    ]
    colour_mask = Image.new("L", reference_crop.size)
    colour_mask.putdata([
        255 if (
            red > 42
            and red * 100 > green * 88
            and red * 100 > blue * 92
            and red - green > -8
        ) else 0
        for red, green, blue in pixels
    ])
    colour_mask = colour_mask.filter(ImageFilter.MaxFilter(3))
    source_alpha = ImageChops.multiply(
        colour_mask,
        polygon_mask(reference_crop.size, FOREGROUND_POLYGON),
    )

    # Upscale RGB once, then sharpen RGB only. Keep alpha independent so the
    # transparent edge is not sharpened or spread across multiple pixels.
    rgb_upscaled = pad_rgb_into_transparency(rgb, source_alpha).resize(
        (BRIDGE_WIDTH, BRIDGE_HEIGHT), Image.Resampling.LANCZOS
    ).filter(ImageFilter.UnsharpMask(
        radius=UNSHARP_RADIUS,
        percent=UNSHARP_PERCENT,
        threshold=UNSHARP_THRESHOLD,
    ))
    alpha = source_alpha.resize(
        (BRIDGE_WIDTH, BRIDGE_HEIGHT), Image.Resampling.LANCZOS
    ).point(
        lambda value: 0
        if value < 96
        else 255
        if value > 160
        else round((value - 96) * 255 / 64)
    )

    foreground = rgb_upscaled.convert("RGBA")
    foreground.putalpha(alpha)
    foreground = clean_transparent_rgb(foreground)
    foreground.save(FOREGROUND_PATH, optimize=True)
    return foreground, source_alpha


def build_shadow(
    reference_crop: Image.Image,
    base_crop: Image.Image,
    foreground_alpha: Image.Image,
) -> Image.Image:
    """Extract the painted contact shadow without copying a rectangular water patch."""
    darker = ImageChops.subtract(
        base_crop.convert("L"), reference_crop.convert("L")
    ).point(lambda value: min(SHADOW_MAX_ALPHA, max(0, (value - 5) * 4)))
    alpha = ImageChops.multiply(
        darker,
        polygon_mask(reference_crop.size, SHADOW_POLYGON),
    )
    alpha = ImageChops.multiply(alpha, ImageChops.invert(foreground_alpha))

    shadow = reference_crop.copy()
    shadow.putalpha(alpha)
    shadow = shadow.resize((BRIDGE_WIDTH, BRIDGE_HEIGHT), Image.Resampling.BICUBIC)
    shadow.putalpha(
        shadow.getchannel("A").point(lambda value: min(SHADOW_MAX_ALPHA, value))
    )
    shadow = clean_transparent_rgb(shadow)
    shadow.save(SHADOW_PATH, optimize=True)
    return shadow


def build_bank_connection(
    master: Image.Image,
    crop: tuple[int, int, int, int],
    points: list[tuple[int, int]],
    output_path: Path,
) -> Image.Image:
    """Cut crisp bank pixels from the active high-resolution master."""
    bank = master.crop(crop).convert("RGBA")
    rgb = bank.convert("RGB")
    land = Image.new("L", bank.size)
    land.putdata([
        255 if red * 115 > blue * 100 else 0
        for red, _green, blue in (
            rgb.getpixel((x, y))
            for y in range(rgb.height)
            for x in range(rgb.width)
        )
    ])
    alpha = ImageChops.multiply(land, polygon_mask(bank.size, points))
    bank.putalpha(alpha)
    bank = clean_transparent_rgb(bank)
    bank.save(output_path, optimize=True)
    return bank


def placement_data(
    foreground: Image.Image,
    shadow: Image.Image,
    left_bank: Image.Image,
    right_bank: Image.Image,
) -> dict:
    center_x = BRIDGE_X + BRIDGE_WIDTH / 2
    center_y = BRIDGE_Y + BRIDGE_HEIGHT / 2
    return {
        "master": {"width": MASTER_WIDTH, "height": MASTER_HEIGHT},
        "reference": {
            "path": "../kanogawa-map-with-bridge-reference.png",
            "width": REFERENCE_WIDTH,
            "height": REFERENCE_HEIGHT,
            "crop": list(REFERENCE_CROP),
            "scale": REFERENCE_SCALE,
        },
        "foreground": {
            "path": "rusty-bridge-from-map.png",
            "naturalWidth": foreground.width,
            "naturalHeight": foreground.height,
            "x": BRIDGE_X,
            "y": BRIDGE_Y,
            "width": BRIDGE_WIDTH,
            "height": BRIDGE_HEIGHT,
            "centerX": center_x,
            "centerY": center_y,
            "normalizedX": center_x / MASTER_WIDTH,
            "normalizedY": center_y / MASTER_HEIGHT,
        },
        "shadow": {
            "path": "rusty-bridge-shadow.png",
            "naturalWidth": shadow.width,
            "naturalHeight": shadow.height,
            "x": BRIDGE_X,
            "y": BRIDGE_Y,
            "width": BRIDGE_WIDTH,
            "height": BRIDGE_HEIGHT,
            "offsetX": 0,
            "offsetY": 0,
            "opacity": SHADOW_MAX_ALPHA / 255,
            "blurSourcePixels": 0,
        },
        "connections": [
            {
                "id": "west",
                "path": "rusty-bridge-left-bank.png",
                "naturalWidth": left_bank.width,
                "naturalHeight": left_bank.height,
                "x": LEFT_BANK_CROP[0],
                "y": LEFT_BANK_CROP[1],
                "width": left_bank.width,
                "height": left_bank.height,
            },
            {
                "id": "east",
                "path": "rusty-bridge-right-bank.png",
                "naturalWidth": right_bank.width,
                "naturalHeight": right_bank.height,
                "x": RIGHT_BANK_CROP[0],
                "y": RIGHT_BANK_CROP[1],
                "width": right_bank.width,
                "height": right_bank.height,
            },
        ],
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


def render_layers(
    master: Image.Image,
    foreground: Image.Image,
    shadow: Image.Image,
    connections: list[tuple[Image.Image, tuple[int, int]]],
) -> Image.Image:
    composite = master.copy().convert("RGBA")
    composite.alpha_composite(shadow, (BRIDGE_X, BRIDGE_Y))
    composite.alpha_composite(foreground, (BRIDGE_X, BRIDGE_Y))
    for connection, position in connections:
        composite.alpha_composite(connection, position)
    return composite


def main() -> None:
    BRIDGE_DIR.mkdir(exist_ok=True)
    reference = Image.open(REFERENCE_PATH).convert("RGBA")
    master = Image.open(MASTER_PATH).convert("RGBA")
    if reference.size != (REFERENCE_WIDTH, REFERENCE_HEIGHT):
        raise ValueError(f"Unexpected reference size: {reference.size}")
    if master.size != (MASTER_WIDTH, MASTER_HEIGHT):
        raise ValueError(f"Unexpected master size: {master.size}")

    reference_crop = reference.crop(REFERENCE_CROP)
    base_reference = master.convert("RGB").resize(reference.size, Image.Resampling.LANCZOS)
    base_crop = base_reference.crop(REFERENCE_CROP)
    foreground, foreground_alpha = build_foreground(reference_crop)
    shadow = build_shadow(reference_crop, base_crop, foreground_alpha)
    left_bank = build_bank_connection(
        master, LEFT_BANK_CROP, LEFT_BANK_POLYGON, LEFT_BANK_PATH
    )
    right_bank = build_bank_connection(
        master, RIGHT_BANK_CROP, RIGHT_BANK_POLYGON, RIGHT_BANK_PATH
    )
    PLACEMENT_PATH.write_text(
        json.dumps(
            placement_data(foreground, shadow, left_bank, right_bank), indent=2
        ) + "\n",
        encoding="utf-8",
    )

    composite = render_layers(master, foreground, shadow, [
        (left_bank, (LEFT_BANK_CROP[0], LEFT_BANK_CROP[1])),
        (right_bank, (RIGHT_BANK_CROP[0], RIGHT_BANK_CROP[1])),
    ])
    composite.resize((1122, 1402), Image.Resampling.LANCZOS).convert("RGB").save(
        BRIDGE_DIR / "kanogawa-bridge-composite-preview.jpg",
        quality=93,
        subsampling=0,
    )
    composite.crop((1950, 3550, 2850, 4300)).save(
        BRIDGE_DIR / "kanogawa-bridge-detail-preview.png", optimize=True
    )
    composite.crop((2050, 3720, 2350, 4150)).save(
        BRIDGE_DIR / "kanogawa-bridge-left-connection-preview.png", optimize=True
    )
    composite.crop((2470, 3650, 2770, 4080)).save(
        BRIDGE_DIR / "kanogawa-bridge-right-connection-preview.png", optimize=True
    )
    composite.resize((1122, 1402), Image.Resampling.LANCZOS).save(
        MAP_DIR / "kanogawa-minimap.png", optimize=True
    )
    print(f"Built reference bridge assets at {BRIDGE_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
