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
CROP_SWAY = (-2, -1, 0, 1, 2, 3, 2, 1, 0, -1, -2, -3, -2)
STAR_POSITIONS = (
    (6, 6), (17, 14), (29, 4), (39, 22), (51, 8), (64, 27), (74, 5),
    (85, 23), (89, 4), (8, 28), (23, 30), (45, 31), (63, 30), (83, 32),
    (8, 38), (119, 38), (20, 38), (107, 38), (8, 56), (119, 56),
    (20, 59), (108, 59), (8, 72), (119, 72), (8, 88), (119, 88),
    (20, 91), (108, 91), (6, 97), (96, 97), (13, 116), (20, 124),
    (43, 119), (70, 123), (94, 120), (8, 126),
)
CAT_TAIL_SWAY = (-3, -2, 0, 2, 3, 2, 1, 0, -1, -2, -3, -1, 1)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
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


def _draw_bat(
    image: Image.Image,
    x: int,
    y: int,
    wing_frame: int,
    scale: float,
    color: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    step = max(1, round(scale))
    for row, pattern in enumerate(BAT_WINGS[wing_frame]):
        for column, pixel in enumerate(pattern):
            if pixel == "#":
                left = x + column * step
                top = y + row * step
                draw.rectangle((left, top, left + step - 1, top + step - 1), fill=color)


def _draw_twinkling_stars(draw: ImageDraw.ImageDraw, scale: float, frame_index: int) -> None:
    """Twinkle stars around the layout while keeping the lettering clear."""
    px = lambda value: round(value * scale)
    for star_index, (star_x, star_y) in enumerate(STAR_POSITIONS):
        phase = (frame_index + star_index * 7) % 26
        if phase >= 20:
            continue
        x, y = px(star_x), px(star_y)
        dim = (130, 137, 173) if star_index % 3 else (139, 111, 158)
        bright = (255, 239, 190) if star_index % 3 else (219, 193, 255)
        draw.point((x, y), fill=bright if phase < 7 else dim)
        if phase < 5 and star_index % 2 == 0:
            sparkle = bright
            draw.point((x - 1, y), fill=sparkle)
            draw.point((x + 1, y), fill=sparkle)
            draw.point((x, y - 1), fill=sparkle)
            draw.point((x, y + 1), fill=sparkle)


def _draw_swaying_crops(
    draw: ImageDraw.ImageDraw, width: int, height: int, scale: float, frame_index: int
) -> None:
    px = lambda value: max(1, round(value * scale))
    for crop_index, crop_x in enumerate(range(px(8), width, px(18))):
        sway = round(CROP_SWAY[(frame_index // 2 + crop_index * 3) % len(CROP_SWAY)] * scale)
        x = crop_x + sway
        crop_y = px(119 + (crop_x % px(7)))
        draw.line((x, height - 1, x, crop_y), fill=(112, 145, 69), width=px(1))
        draw.line((x, px(124), x - px(3), px(121)), fill=(137, 163, 77), width=px(1))
        draw.line((x, px(126), x + px(3), px(123)), fill=(137, 163, 77), width=px(1))


def _draw_moving_border(
    draw: ImageDraw.ImageDraw, scale: float, frame_index: int, frame_count: int
) -> None:
    px = lambda value: round(value * scale)
    left, top, right, bottom = px(3), px(35), px(124), px(94)
    path = (
        [(x, top) for x in range(left, right + 1)]
        + [(right, y) for y in range(top + 1, bottom + 1)]
        + [(x, bottom) for x in range(right - 1, left - 1, -1)]
        + [(left, y) for y in range(bottom - 1, top, -1)]
    )
    if not path:
        return
    colors = ((255, 176, 83), (197, 160, 221), (235, 220, 180), (135, 173, 127))
    movement = round(frame_index * len(path) / frame_count)
    for dash_index, start in enumerate(range(0, len(path), px(16))):
        color = colors[dash_index % len(colors)]
        for length in range(px(4)):
            x, y = path[(start + movement + length) % len(path)]
            draw.point((x, y), fill=color)


def _draw_black_cat(image: Image.Image, x: int, y: int, scale: float, frame_index: int) -> None:
    draw = ImageDraw.Draw(image)
    px = lambda value: round(value * scale)
    black = (5, 6, 13)
    edge = (77, 64, 100)
    tail = px(CAT_TAIL_SWAY[(frame_index // 2) % len(CAT_TAIL_SWAY)])
    draw.line(
        ((x + px(8), y + px(17)), (x + px(4) + tail, y + px(15)),
         (x + px(2) + tail, y + px(11)), (x + px(5) + tail, y + px(8))),
        fill=edge, width=px(4), joint="curve",
    )
    draw.line(
        ((x + px(8), y + px(17)), (x + px(4) + tail, y + px(15)),
         (x + px(2) + tail, y + px(11)), (x + px(5) + tail, y + px(8))),
        fill=black, width=px(2), joint="curve",
    )
    draw.ellipse((x + px(3), y + px(12), x + px(19), y + px(23)), fill=black, outline=edge)
    draw.ellipse((x + px(12), y + px(5), x + px(24), y + px(17)), fill=black, outline=edge)
    draw.polygon(((x + px(13), y + px(10)), (x + px(12), y + px(2)), (x + px(18), y + px(7))), fill=black)
    draw.polygon(((x + px(18), y + px(7)), (x + px(23), y + px(1)), (x + px(23), y + px(11))), fill=black)
    if (frame_index // 2) % 13 not in (5, 6):
        eye = (255, 207, 111)
        draw.point((x + px(17), y + px(11)), fill=eye)
        draw.point((x + px(21), y + px(11)), fill=eye)
    else:
        draw.line(((x + px(16), y + px(11)), (x + px(18), y + px(11))), fill=edge)
        draw.line(((x + px(20), y + px(11)), (x + px(22), y + px(11))), fill=edge)


def _draw_static_sign(width: int, height: int) -> tuple[Image.Image, float]:
    sky = (8, 10, 28)
    image = Image.new("RGB", (width, height), sky)
    draw = ImageDraw.Draw(image)
    scale = min(width / 128, height / 128)
    px = lambda value: max(1, round(value * scale))

    # A bright crescent moon sits over the farm at night.
    draw.ellipse((px(92), px(1), px(124), px(33)), outline=(49, 45, 70), width=px(2))
    draw.ellipse((px(96), px(4), px(121), px(29)), fill=(255, 225, 164))
    draw.ellipse((px(105), px(0), px(130), px(24)), fill=sky)

    # Orchard silhouettes and a low field frame the central name.
    draw.polygon(
        ((0, px(33)), (px(16), px(28)), (px(36), px(34)), (px(55), px(27)),
         (px(78), px(34)), (px(101), px(27)), (width, px(34)), (width, px(42)),
         (0, px(42))), fill=(35, 48, 65),
    )
    draw.rectangle((0, px(96), width, height), fill=(22, 36, 42))
    draw.polygon(((0, px(113)), (width, px(106)), (width, height), (0, height)), fill=(30, 54, 43))

    # Deep forest-green panel makes the farm name the visual anchor.
    left, top, right, bottom = px(3), px(35), px(124), px(94)
    draw.rounded_rectangle(
        (left, top, right, bottom), radius=px(4), fill=(17, 34, 39),
        outline=(90, 67, 112), width=px(2),
    )
    draw.rounded_rectangle(
        (left + px(3), top + px(3), right - px(3), bottom - px(3)),
        radius=px(2), fill=(22, 52, 43), outline=(89, 111, 72), width=px(1),
    )

    title_font = _font(px(17))
    farm_font = _font(px(28))
    tagline_font = _font(px(12))
    _centered_text(draw, "POOR LOUIS", title_font, width, px(40) + px(1), (5, 16, 20))
    _centered_text(draw, "POOR LOUIS", title_font, width, px(40), (255, 243, 216))
    draw.line((px(23), px(63), width - px(23), px(63)), fill=(136, 107, 136), width=px(1))
    _centered_text(draw, "FARMS", farm_font, width, px(65) + px(1), (69, 37, 29))
    _centered_text(draw, "FARMS", farm_font, width, px(65), (255, 171, 77))
    _centered_text(draw, "THANK YOU!", tagline_font, width - px(27), px(99), (255, 232, 190))

    return image, scale


def build_animation_frames(width: int, height: int) -> tuple[bytes, ...]:
    """Pre-render the farm sign and Halloween animation frames at startup."""
    background, scale = _draw_static_sign(width, height)
    bat_width = len(BAT_WINGS[0][0]) * max(1, round(scale))
    step = max(1, round(2 * scale))
    first_x = max(0, round(8 * scale))
    last_x = max(first_x, width - bat_width - round(8 * scale))
    positions = list(range(first_x, last_x + 1, step)) or [first_x]
    if len(positions) > 1:
        positions.extend(positions[-2:0:-1])

    frames = []
    for index, x in enumerate(positions):
        frame = background.copy()
        _draw_bat(frame, x, round(9 * scale), (index // 2) % 2, scale, (177, 152, 207))
        _draw_bat(
            frame, first_x + last_x - x, round(25 * scale), (index // 2 + 1) % 2,
            scale, (111, 104, 142),
        )
        draw = ImageDraw.Draw(frame)
        _draw_swaying_crops(draw, width, height, scale, index)
        _draw_twinkling_stars(draw, scale, index)
        _draw_moving_border(draw, scale, index, len(positions))
        _draw_black_cat(frame, width - round(27 * scale), height - round(27 * scale), scale, index)
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
