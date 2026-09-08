#!/usr/bin/env python3
"""Validate bridge assets, layering data, and the two-way navigation corridor."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = ROOT / "kanogawa-8x-map" / "bridge"
PLACEMENT = json.loads(
    (BRIDGE_DIR / "rusty-bridge-placement.json").read_text(encoding="utf-8")
)


def assert_asset_properties() -> None:
    foreground = Image.open(BRIDGE_DIR / PLACEMENT["foreground"]["path"]).convert("RGBA")
    shadow = Image.open(BRIDGE_DIR / PLACEMENT["shadow"]["path"]).convert("RGBA")
    assert foreground.size == (
        PLACEMENT["foreground"]["naturalWidth"],
        PLACEMENT["foreground"]["naturalHeight"],
    )
    assert foreground.width * PLACEMENT["foreground"]["height"] == (
        foreground.height * PLACEMENT["foreground"]["width"]
    )
    alpha_bbox = foreground.getchannel("A").getbbox()
    assert alpha_bbox is not None
    assert max(
        alpha_bbox[0],
        alpha_bbox[1],
        foreground.width - alpha_bbox[2],
        foreground.height - alpha_bbox[3],
    ) <= 30
    assert shadow.getchannel("A").getextrema()[1] <= 64


def assert_navigation_corridor() -> None:
    mask = Image.open(ROOT / "navigation-mask.png").convert("L")
    master = PLACEMENT["master"]
    route = [
        (2230, 3650),
        (2300, 3750),
        (2404.5, 3914.5),
        (2400, 4050),
        (2390, 4140),
    ]
    samples = []
    for start, end in zip(route, route[1:]):
        steps = math.ceil(math.dist(start, end))
        samples.extend(
            (
                start[0] + (end[0] - start[0]) * step / steps,
                start[1] + (end[1] - start[1]) * step / steps,
            )
            for step in range(steps + 1)
        )

    for x, y in samples:
        mask_x = min(mask.width - 1, int(x / master["width"] * mask.width))
        mask_y = min(mask.height - 1, int(y / master["height"] * mask.height))
        assert mask.getpixel((mask_x, mask_y)) >= 128, (x, y, "mask blocked")
        assert not any(
            math.hypot(x - abutment["centerX"], y - abutment["centerY"])
            <= abutment["radius"]
            for abutment in PLACEMENT["abutments"]
        ), (x, y, "abutment blocked")
    print(f"bridge navigation corridor passed in both directions: {len(samples)} samples")


if __name__ == "__main__":
    assert_asset_properties()
    assert_navigation_corridor()
    print("bridge asset checks passed")
