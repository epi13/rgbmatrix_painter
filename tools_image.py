
from __future__ import annotations
from typing import Tuple
from PIL import Image, ImageOps
import numpy as np

def apply_gamma(img: Image.Image, gamma: float) -> Image.Image:
    if gamma <= 0:
        return img
    lut = [int(255 * ((i / 255.0) ** (1.0 / gamma))) for i in range(256)]
    table = lut * 3  # same for R,G,B
    return img.convert("RGB").point(table)

# Simple 4x4 Bayer matrix for ordered dithering
_BAYER_4x4 = (np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5],
]) + 0.5) / 16.0

def ordered_dither(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    tiled = np.tile(_BAYER_4x4, (h // 4 + 1, w // 4 + 1))
    tiled = tiled[:h, :w][..., None]
    # Add threshold and quantize to 8-bit
    arr = np.clip(arr + (tiled - 0.5) / 255.0, 0, 1.0)
    arr = (arr * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")

def fit_letterbox(img: Image.Image, target_wh: Tuple[int, int], bg=(0,0,0)) -> Image.Image:
    tw, th = target_wh
    im = ImageOps.contain(img, (tw, th), method=Image.Resampling.LANCZOS)
    out = Image.new("RGB", (tw, th), bg)
    x = (tw - im.width) // 2
    y = (th - im.height) // 2
    out.paste(im, (x, y))
    return out

def to_panel_image(img: Image.Image, w: int, h: int, gamma: float = 2.2, dither: bool = False) -> Image.Image:
    im = fit_letterbox(img, (w, h))
    im = apply_gamma(im, gamma)
    if dither:
        im = ordered_dither(im)
    return im.convert("RGB")
