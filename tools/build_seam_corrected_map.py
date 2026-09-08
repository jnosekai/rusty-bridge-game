"""Reversible low-frequency seam correction; never resample terrain pixels."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'kanogawa-8x-map/kanogawa-map-no-bridge-8x.png'
OUT = ROOT / 'kanogawa-8x-map/seam-corrected'
HALF_BAND = 20

def soften_profile(profile):
    kernel = np.exp(-np.arange(-30, 31, dtype=np.float32)**2 / (2 * 10**2))
    kernel /= kernel.sum()
    return np.stack([np.convolve(np.pad(profile[:, c], 30, mode='edge'), kernel, mode='valid') for c in range(3)], axis=1)

def main():
    OUT.mkdir(exist_ok=True)
    for name in ('tiles', 'bleed', 'qa'):
        (OUT / name).mkdir(exist_ok=True)
    original = np.asarray(Image.open(SOURCE).convert('RGB'))
    corrected = original.astype(np.float32)
    seams = []
    for axis, count, step, segments, length in ((1, 2, 1496, 4, 1402), (0, 3, 1402, 3, 1496)):
        for boundary in range(1, count+1):
            position = boundary * step
            for segment in range(segments):
                start, end = segment*length, (segment+1)*length
                a = np.swapaxes(original, 0, 1) if axis == 0 else original
                b = np.swapaxes(corrected, 0, 1) if axis == 0 else corrected
                # Smooth the discontinuity along the edge, never the artwork.
                left = a[start:end, position-2:position].astype(np.float32).mean(axis=1)
                right = a[start:end, position:position+2].astype(np.float32).mean(axis=1)
                delta = np.clip(soften_profile(right-left), -48, 48)
                for offset in range(HALF_BAND):
                    weight = (1 + np.cos(np.pi * offset/(HALF_BAND-1))) / 4
                    b[start:end,position-1-offset] += delta*weight
                    b[start:end,position+offset] -= delta*weight
                first = segment*3+boundary if axis == 1 else (boundary-1)*3+segment+1
                second = first+1 if axis == 1 else first+3
                box = (position-40,start,position+40,end) if axis == 1 else (start,position-40,end,position+40)
                seams.append((f'{first:02}-{second:02}', box, axis))
    result = Image.fromarray(np.clip(np.rint(corrected),0,255).astype(np.uint8))
    result.save(OUT/'master.png', optimize=True)
    source_image = Image.fromarray(original)
    for label, box, axis in seams:
        before, after = source_image.crop(box), result.crop(box)
        if axis == 0:
            before, after = before.transpose(Image.Transpose.ROTATE_90), after.transpose(Image.Transpose.ROTATE_90)
        sheet = Image.new('RGB',(160,before.height+24),'#222')
        sheet.paste(before,(0,24)); sheet.paste(after,(80,24))
        ImageDraw.Draw(sheet).text((2,3),f'{label} old | new',fill='white')
        sheet.save(OUT/'qa'/f'{label}-100pct.png')
    thumbs = []
    for label, _, _ in seams:
        seam = Image.open(OUT/'qa'/f'{label}-100pct.png').convert('RGB')
        preview = seam.resize((160, 224), Image.Resampling.NEAREST)
        thumbs.append((label, preview))
    contact = Image.new('RGB', (160 * 5, 250 * 4), '#151515')
    draw = ImageDraw.Draw(contact)
    for index, (label, preview) in enumerate(thumbs):
        x = index % 5 * 160
        y = index // 5 * 250
        draw.text((x + 4, y + 4), f'{label}  BEFORE | AFTER', fill='white')
        contact.paste(preview, (x, y + 24))
    contact.save(OUT/'qa'/'all-seams-before-after.png', optimize=True)
    for i in range(12):
        x,y=i%3*1496,i//3*1402
        for folder,bleed in (('tiles',False),('bleed',True)):
            w=1496+int(bleed and i%3<2); h=1402+int(bleed and i//3<3)
            result.crop((x,y,x+w,y+h)).save(OUT/folder/f'kanogawa-final-{i+1:02}.png',optimize=True)
    report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'size':list(result.size),'band_total_px':40,'max_channel_correction_per_boundary':24,'seams':[s[0] for s in seams]}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
