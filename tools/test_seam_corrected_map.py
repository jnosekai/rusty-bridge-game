"""Verify the reversible seam-only display assets."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "kanogawa-8x-map"
OUT = MAP / "seam-corrected"
SOURCE = MAP / "kanogawa-map-no-bridge-8x.png"
TILE_W, TILE_H = 1496, 1402


def low_frequency_jump(image: Image.Image, axis: str, position: int, start: int, end: int) -> float:
    low = np.asarray(image.filter(ImageFilter.GaussianBlur(10))).astype(np.float32)
    if axis == "vertical":
        return float(np.abs(low[start:end, position - 1] - low[start:end, position]).mean())
    return float(np.abs(low[position - 1, start:end] - low[position, start:end]).mean())


def main() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == manifest["source_sha256"]
    source = Image.open(SOURCE).convert("RGB")
    corrected = Image.open(OUT / "master.png").convert("RGB")
    assert source.size == corrected.size == (4488, 5608)

    original = np.asarray(source).astype(np.int16)
    result = np.asarray(corrected).astype(np.int16)
    changed = np.any(original != result, axis=2)
    allowed = np.zeros(changed.shape, dtype=bool)
    for x in (TILE_W, TILE_W * 2):
        allowed[:, x - 20:x + 20] = True
    for y in (TILE_H, TILE_H * 2, TILE_H * 3):
        allowed[y - 20:y + 20, :] = True
    assert not np.any(changed & ~allowed), "pixels outside the 40px seam strips changed"
    assert np.abs(result - original).max() <= 48, "correction exceeded the documented limit"

    improvements = {}
    for x in (TILE_W, TILE_W * 2):
        for row in range(4):
            label = f"{row * 3 + x // TILE_W:02}-{row * 3 + x // TILE_W + 1:02}"
            before = low_frequency_jump(source, "vertical", x, row * TILE_H, (row + 1) * TILE_H)
            after = low_frequency_jump(corrected, "vertical", x, row * TILE_H, (row + 1) * TILE_H)
            improvements[label] = [before, after]
    for y in (TILE_H, TILE_H * 2, TILE_H * 3):
        for column in range(3):
            first = (y // TILE_H - 1) * 3 + column + 1
            label = f"{first:02}-{first + 3:02}"
            before = low_frequency_jump(source, "horizontal", y, column * TILE_W, (column + 1) * TILE_W)
            after = low_frequency_jump(corrected, "horizontal", y, column * TILE_W, (column + 1) * TILE_W)
            improvements[label] = [before, after]

    reconstructed = Image.new("RGB", corrected.size)
    for index in range(12):
        column, row = index % 3, index // 3
        tile = Image.open(OUT / "tiles" / f"kanogawa-final-{index + 1:02}.png").convert("RGB")
        assert tile.size == (TILE_W, TILE_H)
        reconstructed.paste(tile, (column * TILE_W, row * TILE_H))
        bleed = Image.open(OUT / "bleed" / f"kanogawa-final-{index + 1:02}.png").convert("RGB")
        expected = (TILE_W + (column < 2), TILE_H + (row < 3))
        assert bleed.size == expected
        crop = corrected.crop((column * TILE_W, row * TILE_H, column * TILE_W + expected[0], row * TILE_H + expected[1]))
        assert np.array_equal(np.asarray(bleed), np.asarray(crop))
    assert np.array_equal(np.asarray(reconstructed), result)
    assert set(improvements) == set(manifest["seams"])
    improved = sum(after <= before for before, after in improvements.values())
    assert improved >= 16, f"only {improved}/17 low-frequency seam profiles improved"
    assert sum(after for _, after in improvements.values()) < sum(before for before, _ in improvements.values())
    print(json.dumps({key: [round(v, 3) for v in values] for key, values in improvements.items()}, indent=2))


if __name__ == "__main__":
    main()
