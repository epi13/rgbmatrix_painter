"""Low-load Poor Louis Farms fall sign for a HUB75 RGB matrix."""
from __future__ import annotations

import signal
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    ANIMATION_FPS,
    CHAIN_LENGTH,
    DISABLE_BUSY_WAITING,
    GPIO_SLOWDOWN,
    MATRIX_REFRESH_LIMIT_HZ,
    MATRIX_HEIGHT,
    MATRIX_WIDTH,
    PANEL_BRIGHTNESS,
    PARALLEL,
    PIXEL_MAPPER_CONFIG,
    PWM_BITS,
    PWM_DITHER_BITS,
)


BAT_WINGS = (
    ("#..##..#", "##.##.##", ".######.", "..####..", "...##..."),
    ("...##...", "..####..", ".######.", "##.##.##", "#..##..#"),
)
CROP_SWAY = (-2, -1, 0, 1, 2, 1, 0, -1)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    draw.text(((width - text_width) // 2 - box[0], y - box[1]), text, font=font, fill=color)


def _draw_pumpkin(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    px = lambda value: round(value * scale)
    orange = (228, 111, 37)
    light = (255, 164, 66)
    dark = (133, 61, 32)
    green = (108, 143, 67)
    draw.ellipse((x, y + px(3), x + px(14), y + px(14)), fill=orange, outline=dark)
    draw.ellipse((x + px(4), y + px(2), x + px(10), y + px(13)), fill=light)
    draw.line((x + px(3), y + px(5), x + px(4), y + px(11)), fill=dark)
    draw.line((x + px(11), y + px(5), x + px(10), y + px(11)), fill=dark)
    draw.line((x + px(7), y + px(2), x + px(8), y), fill=green, width=max(1, px(2)))
    # Tiny warm eyes add a Halloween cue without competing with the farm name.
    draw.ellipse((x + px(4), y + px(7), x + px(5), y + px(8)), fill=(70, 40, 31))
    draw.ellipse((x + px(9), y + px(7), x + px(10), y + px(8)), fill=(70, 40, 31))


def _draw_bat(image: Image.Image, x: int, y: int, wing_frame: int, scale: float) -> None:
    draw = ImageDraw.Draw(image)
    color = (166, 137, 176)
    step = max(1, round(scale))
    for row, pattern in enumerate(BAT_WINGS[wing_frame]):
        for column, pixel in enumerate(pattern):
            if pixel == "#":
                left = x + column * step
                top = y + row * step
                draw.rectangle((left, top, left + step - 1, top + step - 1), fill=color)


def _draw_fireflies(draw: ImageDraw.ImageDraw, frame_index: int) -> None:
    """Add a few dim, drifting fireflies in the open dusk sky."""
    glow = (112, 100, 68)
    light = (250, 213, 137)
    for fly_index, (base_x, base_y) in enumerate(((22, 14), (69, 9), (88, 20))):
        phase = frame_index + fly_index * 7
        x = base_x + ((phase // 4) % 7) - 3
        y = base_y + ((phase // 6 + fly_index) % 3) - 1
        if (phase // 3) % 4 == 0:
            continue
        draw.point((x - 1, y), fill=glow)
        draw.point((x + 1, y), fill=glow)
        draw.point((x, y), fill=light)


def _draw_swaying_crops(
    draw: ImageDraw.ImageDraw, width: int, height: int, scale: float, frame_index: int
) -> None:
    px = lambda value: max(1, round(value * scale))
    for crop_index, crop_x in enumerate(range(px(8), width, px(18))):
        sway = round(CROP_SWAY[(frame_index // 2 + crop_index * 2) % len(CROP_SWAY)] * scale)
        x = crop_x + sway
        crop_y = px(119 + (crop_x % px(7)))
        draw.line((x, height - 1, x, crop_y), fill=(112, 145, 69), width=px(1))
        draw.line((x, px(124), x - px(3), px(121)), fill=(137, 163, 77), width=px(1))
        draw.line((x, px(126), x + px(3), px(123)), fill=(137, 163, 77), width=px(1))


def _draw_static_sign(width: int, height: int) -> tuple[Image.Image, float]:
    image = Image.new("RGB", (width, height), (16, 31, 42))
    draw = ImageDraw.Draw(image)
    scale = min(width / 128, height / 128)
    px = lambda value: max(1, round(value * scale))

    # Quiet dusk sky with a harvest moon and a few fixed stars.
    draw.ellipse((px(94), px(3), px(116), px(25)), fill=(247, 193, 105))
    draw.ellipse((px(101), px(0), px(120), px(19)), fill=(16, 31, 42))
    for star_x, star_y in ((12, 9), (38, 17), (57, 7), (82, 20), (120, 10)):
        x, y = px(star_x), px(star_y)
        draw.point((x, y), fill=(220, 203, 155))

    # Distant orchard hills sit behind the sign.
    draw.polygon(
        ((0, px(29)), (px(18), px(23)), (px(37), px(30)), (px(58), px(22)),
         (px(78), px(29)), (px(99), px(21)), (width, px(28)), (width, px(39)),
         (0, px(39))),
        fill=(45, 73, 61),
    )
    draw.rectangle((0, px(108), width, height), fill=(28, 57, 42))
    draw.polygon(((0, px(118)), (width, px(111)), (width, height), (0, height)), fill=(37, 72, 48))

    # Timber frame and deep green sign keep the farm branding as the focus.
    left, top, right, bottom = px(4), px(27), width - px(4), px(108)
    draw.rounded_rectangle((left, top, right, bottom), radius=px(5), fill=(62, 39, 25), outline=(222, 157, 74), width=px(2))
    draw.rounded_rectangle((left + px(3), top + px(3), right - px(3), bottom - px(3)), radius=px(3), fill=(30, 65, 47), outline=(100, 126, 70), width=px(1))

    # Small carved pumpkins decorate the name without touching the center seam.
    _draw_pumpkin(draw, px(10), px(69), scale)
    _draw_pumpkin(draw, width - px(24), px(69), scale)

    title_font = _font(px(16))
    farm_font = _font(px(25))
    tagline_font = _font(px(8))
    _centered_text(draw, "POOR LOUIS", title_font, width, px(35), (255, 240, 205))
    draw.line((px(27), px(57), width - px(27), px(57)), fill=(168, 113, 57), width=px(1))
    _centered_text(draw, "FARMS", farm_font, width, px(65), (247, 171, 82))
    _centered_text(draw, "LOCALLY GROWN", tagline_font, width, px(96), (225, 232, 193))

    # Quiet sign supports finish the scene; crop rows sway per animation frame.
    for post_x in (px(25), width - px(25)):
        draw.rectangle((post_x - px(2), bottom - px(1), post_x + px(2), height), fill=(91, 62, 40))

    return image, scale


def build_animation_frames(width: int, height: int) -> tuple[bytes, ...]:
    """Pre-render the sign and its small animated details once at startup."""
    background, scale = _draw_static_sign(width, height)
    bat_width = len(BAT_WINGS[0][0]) * max(1, round(scale))
    step = max(1, round(4 * scale))
    first_x = max(0, round(8 * scale))
    last_x = max(first_x, width - bat_width - round(8 * scale))
    positions = list(range(first_x, last_x + 1, step)) or [first_x]
    if len(positions) > 1:
        positions.extend(positions[-2:0:-1])

    frames = []
    for index, x in enumerate(positions):
        frame = background.copy()
        _draw_bat(frame, x, round(10 * scale), index % 2, scale)
        draw = ImageDraw.Draw(frame)
        _draw_fireflies(draw, index)
        _draw_swaying_crops(draw, width, height, scale, index)
        frames.append(frame.tobytes())
    return tuple(frames)


def draw_to_canvas(canvas: object, current: bytes, previous: bytes, width: int, height: int) -> None:
    """Write only changed RGB pixels, skipping the untouched static rows."""
    previous_view = memoryview(previous)
    row_bytes = width * 3
    for y in range(height):
        offset = y * row_bytes
        if current[offset:offset + row_bytes] == previous_view[offset:offset + row_bytes]:
            continue
        pixel_offset = offset
        for x in range(width):
            if (
                current[pixel_offset] != previous_view[pixel_offset]
                or current[pixel_offset + 1] != previous_view[pixel_offset + 1]
                or current[pixel_offset + 2] != previous_view[pixel_offset + 2]
            ):
                canvas.SetPixel(
                    x,
                    y,
                    current[pixel_offset],
                    current[pixel_offset + 1],
                    current[pixel_offset + 2],
                )
            pixel_offset += 3


def main() -> None:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    options = RGBMatrixOptions()
    options.rows = MATRIX_HEIGHT
    options.cols = MATRIX_WIDTH
    options.chain_length = CHAIN_LENGTH
    options.parallel = PARALLEL
    options.pixel_mapper_config = PIXEL_MAPPER_CONFIG
    options.gpio_slowdown = GPIO_SLOWDOWN
    options.brightness = PANEL_BRIGHTNESS
    options.pwm_bits = PWM_BITS
    options.pwm_dither_bits = PWM_DITHER_BITS
    options.limit_refresh_rate_hz = MATRIX_REFRESH_LIMIT_HZ
    options.disable_busy_waiting = DISABLE_BUSY_WAITING
    matrix = RGBMatrix(options=options)

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        frames = build_animation_frames(matrix.width, matrix.height)
        print(
            f"RGB matrix canvas: {matrix.width}x{matrix.height} "
            f"(chain={CHAIN_LENGTH}, mapper={PIXEL_MAPPER_CONFIG}, "
            f"pwm_bits={PWM_BITS}, pwm_dither_bits={PWM_DITHER_BITS}, "
            f"max_refresh_hz={MATRIX_REFRESH_LIMIT_HZ}, "
            f"busy_waiting={not DISABLE_BUSY_WAITING}, "
            f"animation_fps={ANIMATION_FPS}, "
            f"pre_rendered_frames={len(frames)})",
            flush=True,
        )
        canvas = matrix.CreateFrameCanvas()
        blank = bytes(matrix.width * matrix.height * 3)
        front_frame = blank
        back_frame = blank
        frame_index = 0
        frame_interval = 1 / ANIMATION_FPS

        while running:
            current = frames[frame_index]
            draw_to_canvas(canvas, current, back_frame, matrix.width, matrix.height)
            canvas = matrix.SwapOnVSync(canvas)
            back_frame, front_frame = front_frame, current
            frame_index = (frame_index + 1) % len(frames)
            time.sleep(frame_interval)
    finally:
        matrix.Clear()


if __name__ == "__main__":
    main()
