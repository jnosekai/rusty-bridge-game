# Kanogawa no-bridge high-resolution map

The runtime map is assembled from `kanogawa-final-01.png` through
`kanogawa-final-12.png`. Tiles are placed without resampling, overlap, masks,
filters, or color correction in this order:

```text
01 02 03
04 05 06
07 08 09
10 11 12
```

Every tile is 1496 x 1402 RGBA pixels with a fully opaque alpha channel. The
assembled master is 4488 x 5608 pixels. The game keeps using its existing world
coordinate system; the background and its independent navigation mask are both
mapped proportionally onto those unchanged world coordinates.

Despite the historical `8x` name, the 4488 x 5608 master is physically 4x the
1122 x 1402 reference dimensions. The filename is retained for compatibility.

Runtime images in `bleed/` include the first real pixel from the right and/or
bottom neighbor. That one-pixel overlap prevents transformed image edges from
revealing the layer background at fractional browser coordinates. The bleed
pixels are crops from the assembled master; no pixels are synthesized or scaled.

Artifacts in this directory:

- `kanogawa-map-no-bridge-8x.png`: pixel-exact assembled master.
- `kanogawa-map-8x-tile-layout.jpg`: labeled placement preview.
- `kanogawa-map-old-new-comparison.jpg`: old and new maps at a common display size.
- `kanogawa-map-8x-seams-100pct.jpg`: unscaled source crops centered on all 17 seams.
- `bleed/kanogawa-final-01.png` through `12.png`: runtime-only one-pixel bleed tiles.
- `bridge/`: the approved illustrated tile-08 bridge concept, its extracted
  foreground, deterministic alpha-derived shadow, placement data, and previews.
- `kanogawa-minimap.png`: bridge composite used only by the high-resolution map.
- `navigation-mask.png`: 1122 x 1402 binary mask generated from the 12-tile
  master. Water connected to the dock is white; land and a uniform four-pixel
  shoreline clearance are black.

Rebuild the deterministic artifacts with:

```sh
python3 tools/build_kanogawa_8x_map.py
python3 tools/build_illustrated_bridge_assets.py
python3 tools/generate_kanogawa_8x_navigation_mask.py
```
