from __future__ import annotations
from typing import Tuple, Optional
from PIL import Image
import re, io, base64

# PICO-8 palette (index 0..15)
PICO8_PALETTE = [
    (0,0,0), (29,43,83), (126,37,83), (0,135,81),
    (171,82,54), (95,87,79), (194,195,199), (255,241,232),
    (255,0,77), (255,163,0), (255,236,39), (0,228,54),
    (41,173,255), (131,118,156), (255,119,168), (255,204,170)
]

def load_p8_gfx(fp) -> Image.Image:
    """Load a .p8 (text) cart and return the 128x128 sprite sheet as a PIL image."""
    text = fp.read().decode('utf-8', errors='ignore')
    # Find __gfx__ section: 128 lines of 128/2=64 bytes hex (two pixels per byte)
    m = re.search(r"__gfx__\s*\n([0-9a-fA-F\n]+)", text)
    if not m:
        raise ValueError("__gfx__ section not found")
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
    # Some carts have fewer lines; pad to 128
    lines = (lines + ['']*128)[:128]
    img = Image.new('RGB', (128,128))
    px = img.load()
    for y, ln in enumerate(lines[:128]):
        # Each byte encodes two pixels: hi-nibble then lo-nibble
        x = 0
        for i in range(0, min(len(ln), 256), 2):
            byte = int(ln[i:i+2], 16)
            c1 = PICO8_PALETTE[(byte >> 4) & 0xF]
            c2 = PICO8_PALETTE[byte & 0xF]
            if x < 128: px[x, y] = c1; x += 1
            if x < 128: px[x, y] = c2; x += 1
    return img
