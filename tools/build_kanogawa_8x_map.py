#!/usr/bin/env python3
"""Build deterministic QA artifacts for the 3 x 4 Kanogawa tile set."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


Image.MAX_IMAGE_PIXELS = None


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "kanogawa-8x-map"
TILE_COLUMNS = 3
TILE_ROWS = 4
TILE_PATHS = [ROOT / f"kanogawa-final-{number:02}.png" for number in range(1, 13)]
MASTER_PATH = OUTPUT / "kanogawa-map-no-bridge-8x.png"
BLEED_OUTPUT = OUTPUT / "bleed"


def load_tiles() -> list[Image.Image]:
    tiles = [Image.open(path) for path in TILE_PATHS]
    expected_size = tiles[0].size
    expected_mode = tiles[0].mode
    for path, tile in zip(TILE_PATHS, tiles, strict=True):
        if tile.size != expected_size:
            raise ValueError(f"Unexpected tile size: {path.name} {tile.size} != {expected_size}")
        if tile.mode != expected_mode:
            raise ValueError(f"Unexpected color mode: {path.name} {tile.mode} != {expected_mode}")
        if tile.getextrema()[3] != (255, 255):
            raise ValueError(f"Tile contains transparency: {path.name}")
    return tiles


def build_master(tiles: list[Image.Image]) -> Image.Image:
    tile_width, tile_height = tiles[0].size
    master = Image.new("RGBA", (tile_width * TILE_COLUMNS, tile_height * TILE_ROWS))
    for index, tile in enumerate(tiles):
        column = index % TILE_COLUMNS
        row = index // TILE_COLUMNS
        master.paste(tile, (column * tile_width, row * tile_height))
    master.save(MASTER_PATH, optimize=True)
    return master


def build_bleed_tiles(master: Image.Image, tile_size: tuple[int, int]) -> None:
    """Add only the first real neighbor pixel on right/bottom display edges."""
    BLEED_OUTPUT.mkdir(exist_ok=True)
    tile_width, tile_height = tile_size
    for index, path in enumerate(TILE_PATHS):
        column = index % TILE_COLUMNS
        row = index // TILE_COLUMNS
        x = column * tile_width
        y = row * tile_height
        display_width = tile_width + (column < TILE_COLUMNS - 1)
        display_height = tile_height + (row < TILE_ROWS - 1)
        bleed = master.crop((x, y, x + display_width, y + display_height))
        bleed.save(BLEED_OUTPUT / path.name, optimize=True)


def build_layout_preview(master: Image.Image, tile_size: tuple[int, int]) -> None:
    preview = master.copy()
    draw = ImageDraw.Draw(preview)
    tile_width, tile_height = tile_size
    stroke = 8
    for column in range(1, TILE_COLUMNS):
        x = column * tile_width
        draw.line((x, 0, x, preview.height), fill=(255, 40, 40, 255), width=stroke)
    for row in range(1, TILE_ROWS):
        y = row * tile_height
        draw.line((0, y, preview.width, y), fill=(255, 40, 40, 255), width=stroke)
    font = ImageFont.load_default(size=96)
    for index in range(len(TILE_PATHS)):
        column = index % TILE_COLUMNS
        row = index // TILE_COLUMNS
        x = column * tile_width + 40
        y = row * tile_height + 30
        label = f"{index + 1:02}"
        box = draw.textbbox((x, y), label, font=font, stroke_width=4)
        draw.rectangle((box[0] - 20, box[1] - 12, box[2] + 20, box[3] + 12), fill=(0, 0, 0, 190))
        draw.text((x, y), label, font=font, fill="white", stroke_width=4, stroke_fill="black")
    preview.thumbnail((1347, 1683), Image.Resampling.LANCZOS)
    preview.convert("RGB").save(OUTPUT / "kanogawa-map-8x-tile-layout.jpg", quality=92)


def build_comparison(master: Image.Image) -> None:
    old_path = ROOT / "map.jpg"
    with Image.open(old_path) as old:
        old = old.convert("RGB").resize(master.size, Image.Resampling.LANCZOS)
    new = master.convert("RGB")
    comparison = Image.new("RGB", (master.width * 2, master.height), "black")
    comparison.paste(old, (0, 0))
    comparison.paste(new, (master.width, 0))
    comparison.thumbnail((1600, 1000), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(comparison)
    font = ImageFont.load_default(size=32)
    draw.rectangle((0, 0, 320, 52), fill="black")
    draw.text((12, 8), "OLD map.jpg", font=font, fill="white")
    midpoint = comparison.width // 2
    draw.rectangle((midpoint, 0, midpoint + 390, 52), fill="black")
    draw.text((midpoint + 12, 8), "NEW 01-12", font=font, fill="white")
    comparison.save(OUTPUT / "kanogawa-map-old-new-comparison.jpg", quality=92)


def build_seam_sheet(master: Image.Image, tile_size: tuple[int, int]) -> None:
    tile_width, tile_height = tile_size
    crop_width = 512
    crop_height = 256
    seams: list[tuple[str, Image.Image]] = []
    for row in range(TILE_ROWS):
        center_y = row * tile_height + tile_height // 2
        for column in range(1, TILE_COLUMNS):
            boundary_x = column * tile_width
            label = f"{row * TILE_COLUMNS + column:02}/{row * TILE_COLUMNS + column + 1:02}"
            crop = master.crop((boundary_x - crop_width // 2, center_y - crop_height // 2,
                                boundary_x + crop_width // 2, center_y + crop_height // 2))
            seams.append((label, crop))
    for row in range(1, TILE_ROWS):
        boundary_y = row * tile_height
        for column in range(TILE_COLUMNS):
            center_x = column * tile_width + tile_width // 2
            label = f"{(row - 1) * TILE_COLUMNS + column + 1:02}/{row * TILE_COLUMNS + column + 1:02}"
            crop = master.crop((center_x - crop_width // 2, boundary_y - crop_height // 2,
                                center_x + crop_width // 2, boundary_y + crop_height // 2))
            seams.append((label, crop))

    label_height = 34
    columns = 3
    rows = (len(seams) + columns - 1) // columns
    sheet = Image.new("RGB", (crop_width * columns, (crop_height + label_height) * rows), "#111")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for index, (label, crop) in enumerate(seams):
        x = index % columns * crop_width
        y = index // columns * (crop_height + label_height)
        sheet.paste(crop.convert("RGB"), (x, y + label_height))
        draw.text((x + 8, y + 4), label, font=font, fill="white")
    sheet.save(OUTPUT / "kanogawa-map-8x-seams-100pct.jpg", quality=95, subsampling=0)


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    tiles = load_tiles()
    master = build_master(tiles)
    build_bleed_tiles(master, tiles[0].size)
    build_layout_preview(master, tiles[0].size)
    build_comparison(master)
    build_seam_sheet(master, tiles[0].size)
    print(f"Built {MASTER_PATH.relative_to(ROOT)}: {master.width}x{master.height}")


if __name__ == "__main__":
    main()
