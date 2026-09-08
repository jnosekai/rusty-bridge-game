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
coordinate system and navigation mask; `index.html?map=kanogawa8x` only changes
the background presentation.

Artifacts in this directory:

- `kanogawa-map-no-bridge-8x.png`: pixel-exact assembled master.
- `kanogawa-map-8x-tile-layout.jpg`: labeled placement preview.
- `kanogawa-map-old-new-comparison.jpg`: old and new maps at a common display size.
- `kanogawa-map-8x-seams-100pct.jpg`: unscaled source crops centered on all 17 seams.

Rebuild the deterministic artifacts with:

```sh
python3 tools/build_kanogawa_8x_map.py
```
