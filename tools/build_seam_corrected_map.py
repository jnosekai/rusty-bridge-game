"""Reversible per-seam low-frequency correction; never resample terrain pixels."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'kanogawa-8x-map/kanogawa-map-no-bridge-8x.png'
OUT = ROOT / 'kanogawa-8x-map/seam-corrected'
SEAM_SETTINGS = {
    '01-02': (150, 1.00), '02-03': (100, 0.85),
    '04-05': (120, 0.95), '05-06': (150, 1.00),
    '07-08': (100, 0.85), '08-09': (100, 0.85),
    '10-11': (90, 0.80), '11-12': (100, 0.85),
    '01-04': (150, 1.00), '02-05': (150, 1.00), '03-06': (100, 0.85),
    '04-07': (100, 0.85), '05-08': (120, 0.95), '06-09': (100, 0.85),
    '07-10': (100, 0.85), '08-11': (150, 1.00), '09-12': (100, 0.85),
}

def soften_profile(profile):
    kernel = np.exp(-np.arange(-30, 31, dtype=np.float32)**2 / (2 * 10**2))
    kernel /= kernel.sum()
    return np.stack([np.convolve(np.pad(profile[:, c], 30, mode='edge'), kernel, mode='valid') for c in range(3)], axis=1)

def correct_seam(corrected, axis, position, start, end, label, pass_strength):
    half_band, strength = SEAM_SETTINGS[label]
    pixels = np.swapaxes(corrected, 0, 1) if axis == 0 else corrected
    left = soften_profile(pixels[start:end, position-40:position].mean(axis=1))
    right = soften_profile(pixels[start:end, position:position+40].mean(axis=1))
    delta = right-left
    for offset in range(half_band):
        weight = (1+np.cos(np.pi*offset/(half_band-1)))/4
        weight *= strength*pass_strength
        pixels[start:end, position-1-offset] += delta*weight
        pixels[start:end, position+offset] -= delta*weight

def match_edge_pixels(corrected, axis, position, start, end, strength):
    pixels = np.swapaxes(corrected, 0, 1) if axis == 0 else corrected
    left = soften_profile(pixels[start:end, position-2:position].mean(axis=1))
    right = soften_profile(pixels[start:end, position:position+2].mean(axis=1))
    delta = right-left
    for offset in range(40):
        weight = (1+np.cos(np.pi*offset/39))/4*strength
        pixels[start:end, position-1-offset] += delta*weight
        pixels[start:end, position+offset] -= delta*weight

def main():
    OUT.mkdir(exist_ok=True)
    for name in ('tiles', 'bleed', 'qa'):
        (OUT / name).mkdir(exist_ok=True)
    original = np.asarray(Image.open(SOURCE).convert('RGB'))
    corrected = original.astype(np.float32)
    seams = []
    passes = ((1, 1.0), (0, 1.0), (1, 0.65), (0, 0.65))
    layouts = {1: (2, 1496, 4, 1402), 0: (3, 1402, 3, 1496)}
    for pass_index, (axis, pass_strength) in enumerate(passes):
        count, step, segments, length = layouts[axis]
        for boundary in range(1, count+1):
            position = boundary * step
            for segment in range(segments):
                start, end = segment*length, (segment+1)*length
                first = segment*3+boundary if axis == 1 else (boundary-1)*3+segment+1
                second = first+1 if axis == 1 else first+3
                label = f'{first:02}-{second:02}'
                correct_seam(corrected, axis, position, start, end, label, pass_strength)
                if pass_index < 2:
                    box = (position-150,start,position+150,end) if axis == 1 else (start,position-150,end,position+150)
                    seams.append((label, box, axis))
    for axis, strength in ((1, 1.0), (0, 1.0), (1, 0.65), (0, 0.65)):
        count, step, segments, length = layouts[axis]
        for boundary in range(1, count+1):
            for segment in range(segments):
                match_edge_pixels(
                    corrected, axis, boundary*step,
                    segment*length, (segment+1)*length, strength
                )
    result = Image.fromarray(np.clip(np.rint(corrected),0,255).astype(np.uint8))
    result.save(OUT/'master.png', optimize=True)
    source_image = Image.fromarray(original)
    for label, box, axis in seams:
        before, after = source_image.crop(box), result.crop(box)
        if axis == 0:
            before, after = before.transpose(Image.Transpose.ROTATE_90), after.transpose(Image.Transpose.ROTATE_90)
        sheet = Image.new('RGB',(600,before.height+24),'#222')
        sheet.paste(before,(0,24)); sheet.paste(after,(300,24))
        ImageDraw.Draw(sheet).text((2,3),f'{label} old (300px) | new (300px)',fill='white')
        sheet.save(OUT/'qa'/f'{label}-100pct.png')
    thumbs = []
    for label, _, _ in seams:
        seam = Image.open(OUT/'qa'/f'{label}-100pct.png').convert('RGB')
        preview = seam.resize((200, 224), Image.Resampling.LANCZOS)
        thumbs.append((label, preview))
    contact = Image.new('RGB', (200 * 5, 250 * 4), '#151515')
    draw = ImageDraw.Draw(contact)
    for index, (label, preview) in enumerate(thumbs):
        x = index % 5 * 200
        y = index // 5 * 250
        draw.text((x + 4, y + 4), f'{label}  BEFORE | AFTER', fill='white')
        contact.paste(preview, (x, y + 24))
    contact.save(OUT/'qa'/'all-seams-before-after.png', optimize=True)
    for i in range(12):
        x,y=i%3*1496,i//3*1402
        for folder,bleed in (('tiles',False),('bleed',True)):
            w=1496+int(bleed and i%3<2); h=1402+int(bleed and i//3<3)
            result.crop((x,y,x+w,y+h)).save(OUT/folder/f'kanogawa-final-{i+1:02}.png',optimize=True)
    report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'size':list(result.size),'per_seam_settings':{key:{'half_band_px':value[0],'strength':value[1]} for key,value in SEAM_SETTINGS.items()},'passes':[{'axis':'vertical' if axis else 'horizontal','strength':strength} for axis,strength in passes],'profile_sample_width_px':40,'edge_match_half_band_px':40,'seams':[s[0] for s in seams]}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
