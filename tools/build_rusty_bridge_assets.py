#!/usr/bin/env python3
"""Deterministically build the bridge layers, previews, and minimap."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "kanogawa-8x-map"
BRIDGE_DIR = MAP_DIR / "bridge"
SOURCE_PATH = MAP_DIR / "rusty-bridge-foreground-source.png"
MASTER_PATH = MAP_DIR / "kanogawa-map-no-bridge-8x.png"
FOREGROUND_PATH = BRIDGE_DIR / "rusty-bridge-foreground.png"
SHADOW_PATH = BRIDGE_DIR / "rusty-bridge-shadow.png"
CONTACT_SHADOW_PATH = BRIDGE_DIR / "rusty-bridge-contact-shadow.png"
PLACEMENT_PATH = BRIDGE_DIR / "rusty-bridge-placement.json"

MASTER_WIDTH = 4488
MASTER_HEIGHT = 5608
BRIDGE_X = 2158
BRIDGE_Y = 3787
BRIDGE_WIDTH = 493
BRIDGE_HEIGHT = 255
SHADOW_OFFSET_X = 6
SHADOW_OFFSET_Y = 14
SHADOW_OPACITY = 0.25
SHADOW_BLUR_SOURCE_PIXELS = 3
SHADOW_PADDING_SOURCE_PIXELS = 12
EFFECTIVE_WIDTH = 116
EFFECTIVE_HEIGHT = 60
COLOR_MULTIPLIER = 0.93
CONTRAST_MULTIPLIER = 0.94
MINIMUM_EDGE_ALPHA = 2


def clean_transparent_rgb(image: Image.Image) -> Image.Image:
    """Clear invisible RGB without changing any visible or partially visible pixel."""
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


def build_foreground() -> tuple[Image.Image, tuple[int, int, int, int]]:
    source = Image.open(SOURCE_PATH).convert("RGBA")
    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise ValueError("Bridge source has no visible pixels")
    trimmed = clean_transparent_rgb(source.crop(alpha_bbox))
    foreground = trimmed.resize(
        (EFFECTIVE_WIDTH, EFFECTIVE_HEIGHT),
        Image.Resampling.LANCZOS,
    ).resize(
        (BRIDGE_WIDTH, BRIDGE_HEIGHT),
        Image.Resampling.BICUBIC,
    )
    foreground = ImageEnhance.Color(foreground).enhance(COLOR_MULTIPLIER)
    foreground = ImageEnhance.Contrast(foreground).enhance(CONTRAST_MULTIPLIER)
    foreground.putalpha(
        foreground.getchannel("A").point(
            lambda value: 0 if value < MINIMUM_EDGE_ALPHA else value
        )
    )
    foreground = clean_transparent_rgb(foreground)
    foreground.save(FOREGROUND_PATH, optimize=True)
    return foreground, alpha_bbox


def build_shadow(foreground: Image.Image) -> Image.Image:
    padding = SHADOW_PADDING_SOURCE_PIXELS
    alpha = Image.new(
        "L",
        (foreground.width + padding * 2, foreground.height + padding * 2),
        0,
    )
    alpha.paste(foreground.getchannel("A"), (padding, padding))
    alpha = alpha.filter(ImageFilter.GaussianBlur(SHADOW_BLUR_SOURCE_PIXELS))
    alpha = alpha.point(lambda value: round(value * SHADOW_OPACITY))
    shadow = Image.new("RGBA", alpha.size, (14, 24, 34, 0))
    shadow.putalpha(alpha)
    shadow = clean_transparent_rgb(shadow)
    shadow.save(SHADOW_PATH, optimize=True)
    return shadow


def build_contact_shadow() -> Image.Image:
    padding = SHADOW_PADDING_SOURCE_PIXELS
    contact = Image.new(
        "RGBA",
        (BRIDGE_WIDTH + padding * 2, BRIDGE_HEIGHT + padding * 2),
        (0, 0, 0, 0),
    )
    alpha = Image.new("L", contact.size, 0)
    draw = ImageDraw.Draw(alpha)
    draw.ellipse((padding, padding + 165, padding + 60, padding + 202), fill=50)
    draw.ellipse((padding + 436, padding + 51, padding + 497, padding + 87), fill=50)
    alpha = alpha.filter(ImageFilter.GaussianBlur(5))
    contact = Image.new("RGBA", contact.size, (12, 20, 24, 0))
    contact.putalpha(alpha)
    contact = clean_transparent_rgb(contact)
    contact.save(CONTACT_SHADOW_PATH, optimize=True)
    return contact


def placement_data(
    foreground: Image.Image,
    shadow: Image.Image,
    contact_shadow: Image.Image,
    source_bbox: tuple[int, int, int, int],
) -> dict:
    center_x = BRIDGE_X + BRIDGE_WIDTH / 2
    center_y = BRIDGE_Y + BRIDGE_HEIGHT / 2
    source_scale = BRIDGE_WIDTH / foreground.width
    shadow_padding_display = SHADOW_PADDING_SOURCE_PIXELS * source_scale
    return {
        "master": {"width": MASTER_WIDTH, "height": MASTER_HEIGHT},
        "source": {
            "path": "../rusty-bridge-foreground-source.png",
            "alphaBoundingBox": list(source_bbox),
        },
        "foreground": {
            "path": "rusty-bridge-foreground.png",
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
            "x": BRIDGE_X - shadow_padding_display + SHADOW_OFFSET_X,
            "y": BRIDGE_Y - shadow_padding_display + SHADOW_OFFSET_Y,
            "width": shadow.width * source_scale,
            "height": shadow.height * source_scale,
            "offsetX": SHADOW_OFFSET_X,
            "offsetY": SHADOW_OFFSET_Y,
            "opacity": SHADOW_OPACITY,
            "blurSourcePixels": SHADOW_BLUR_SOURCE_PIXELS,
        },
        "contactShadow": {
            "path": "rusty-bridge-contact-shadow.png",
            "naturalWidth": contact_shadow.width,
            "naturalHeight": contact_shadow.height,
            "x": BRIDGE_X - SHADOW_PADDING_SOURCE_PIXELS,
            "y": BRIDGE_Y - SHADOW_PADDING_SOURCE_PIXELS,
            "width": contact_shadow.width,
            "height": contact_shadow.height,
            "opacity": 50 / 255,
            "blurPixels": 5,
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


def render_layers(master: Image.Image, foreground: Image.Image, data: dict) -> Image.Image:
    composite = master.copy().convert("RGBA")
    fg = foreground
    contact = Image.open(CONTACT_SHADOW_PATH).convert("RGBA")
    composite.alpha_composite(
        contact,
        (
            round(data["contactShadow"]["x"]),
            round(data["contactShadow"]["y"]),
        ),
    )
    shadow_alpha = fg.getchannel("A").filter(ImageFilter.GaussianBlur(3))
    shadow_alpha = shadow_alpha.point(lambda value: round(value * SHADOW_OPACITY))
    shadow = Image.new("RGBA", fg.size, (14, 24, 34, 0))
    shadow.putalpha(shadow_alpha)
    composite.alpha_composite(
        shadow,
        (BRIDGE_X + SHADOW_OFFSET_X, BRIDGE_Y + SHADOW_OFFSET_Y),
    )
    composite.alpha_composite(fg, (BRIDGE_X, BRIDGE_Y))
    return composite


def main() -> None:
    BRIDGE_DIR.mkdir(exist_ok=True)
    foreground, source_bbox = build_foreground()
    shadow = build_shadow(foreground)
    contact_shadow = build_contact_shadow()
    data = placement_data(foreground, shadow, contact_shadow, source_bbox)
    PLACEMENT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    master = Image.open(MASTER_PATH).convert("RGBA")
    if master.size != (MASTER_WIDTH, MASTER_HEIGHT):
        raise ValueError(f"Unexpected master size: {master.size}")
    composite = render_layers(master, foreground, data)
    composite.resize((1122, 1402), Image.Resampling.LANCZOS).convert("RGB").save(
        BRIDGE_DIR / "kanogawa-bridge-composite-preview.jpg",
        quality=93,
        subsampling=0,
    )
    composite.crop((1850, 3450, 2900, 4300)).save(
        BRIDGE_DIR / "kanogawa-bridge-detail-preview.png",
        optimize=True,
    )
    composite.resize((1122, 1402), Image.Resampling.LANCZOS).save(
        MAP_DIR / "kanogawa-minimap.png",
        optimize=True,
    )
    print(f"Built bridge assets at {BRIDGE_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
