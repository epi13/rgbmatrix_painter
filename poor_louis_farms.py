"""Animated Poor Louis Farms sign for a HUB75 RGB matrix."""
from __future__ import annotations

import math
import signal
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    CHAIN_LENGTH,
    GPIO_SLOWDOWN,
    MATRIX_HEIGHT,
    MATRIX_WIDTH,
    PANEL_BRIGHTNESS,
    PARALLEL,
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def build_frame(t: float, width: int = MATRIX_WIDTH, height: int = MATRIX_HEIGHT) -> Image.Image:
    """Draw one RGB frame; t is elapsed animation time in seconds."""
    im = Image.new("RGB", (width, height), (21, 83, 116))
    d = ImageDraw.Draw(im)
    scale = min(width / 64, height / 64)
    px = lambda value: round(value * scale)

    # A warm, slow-breathing sun and drifting cloud give the sign a little life.
    pulse = (math.sin(t * 1.2) + 1) / 2
    sun_r = px(4 + pulse)
    sun_x = px(52 + math.sin(t * .22) * 2)
    sun_y = px(11)
    d.ellipse((sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r), fill=(255, 205, 82))
    cloud_x = int((t * px(3)) % (width + px(20))) - px(14)
    cloud_y = px(9)
    for dx, dy, radius in ((0, 2, 3), (4, 0, 4), (9, 2, 3)):
        r = px(radius)
        x, y = cloud_x + px(dx), cloud_y + px(dy)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(184, 221, 223))

    # Farm field and two gently swaying crop rows.
    horizon = px(49)
    d.rectangle((0, horizon, width, height), fill=(53, 111, 59))
    sway = math.sin(t * 2.0) * px(1)
    for x0 in range(px(4), width, px(10)):
        x = x0 + round(sway * math.sin(x0 * .2))
        d.line((x, height, x, height - px(7)), fill=(119, 172, 73), width=max(1, px(1)))
        d.ellipse((x - px(2), height - px(7), x, height - px(4)), fill=(142, 190, 83))
        d.ellipse((x, height - px(9), x + px(2), height - px(6)), fill=(142, 190, 83))

    # Painted wooden roadside sign, sized for the configured panel.
    left, right = px(2), width - px(2)
    top, bottom = px(16), px(48)
    d.rounded_rectangle((left, top, right, bottom), radius=px(3), fill=(53, 38, 27), outline=(239, 187, 103), width=max(1, px(1)))
    d.rounded_rectangle((left + px(2), top + px(2), right - px(2), bottom - px(2)), radius=px(2), fill=(37, 77, 47))

    title_font = _font(px(7))
    farm_font = _font(px(8))
    tagline_font = _font(px(4))
    title = "POOR LOUIS"
    farm = "FARMS"
    title_box = d.textbbox((0, 0), title, font=title_font)
    farm_box = d.textbbox((0, 0), farm, font=farm_font)
    tagline = "LOCAL"
    tag_box = d.textbbox((0, 0), tagline, font=tagline_font)
    def center(text: str, font: ImageFont.ImageFont, box: tuple[int, int, int, int], y: int, color: tuple[int, int, int]) -> None:
        tw = box[2] - box[0]
        d.text(((width - tw) // 2, y), text, font=font, fill=color)

    center(title, title_font, title_box, top + px(2), (255, 245, 213))
    center(farm, farm_font, farm_box, top + px(11), (242, 181, 91))
    center(tagline, tagline_font, tag_box, top + px(23), (222, 240, 187))
    return im


def main() -> None:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    options = RGBMatrixOptions()
    options.rows = MATRIX_HEIGHT
    options.cols = MATRIX_WIDTH
    options.chain_length = CHAIN_LENGTH
    options.parallel = PARALLEL
    options.gpio_slowdown = GPIO_SLOWDOWN
    options.brightness = PANEL_BRIGHTNESS
    matrix = RGBMatrix(options=options)

    running = True
    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    started = time.monotonic()
    next_frame = started
    try:
        while running:
            now = time.monotonic()
            matrix.SetImage(build_frame(now - started), 0, 0)
            next_frame += 1 / 12
            time.sleep(max(0, next_frame - time.monotonic()))
    finally:
        matrix.Clear()


if __name__ == "__main__":
    main()
