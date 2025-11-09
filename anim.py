from __future__ import annotations
from typing import List, Tuple
from PIL import Image, ImageSequence

def gif_frames(fp) -> List[Tuple[Image.Image, int]]:
    im = Image.open(fp)
    frames = []
    for frame in ImageSequence.Iterator(im):
        delay = frame.info.get('duration', 100)  # ms
        frames.append((frame.convert('RGBA'), delay))
    return frames

def strip_frames(img: Image.Image, cols: int, rows: int, order='row') -> List[Image.Image]:
    w, h = img.size
    fw, fh = w // cols, h // rows
    out = []
    for r in range(rows):
        for c in range(cols):
            x = c * fw
            y = r * fh
            out.append(img.crop((x, y, x+fw, y+fh)))
    return out
