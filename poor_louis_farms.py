"""Low-load Poor Louis Farms fall sign for a HUB75 RGB matrix."""
from __future__ import annotations

import signal
import time
from math import sin
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


GHOST_FRAMES = (
    ("..#####..", ".#######.", "#########", "##.###.##", "#########", "#########", "#.#.#.#.#"),
    ("..#####..", ".#######.", "#########", "##.###.##", "#########", "#########", "##.#.#.##"),
)
STAR_POSITIONS = (
    (35, 4), (46, 16), (58, 7), (72, 25), (83, 5), (91, 30), (41, 29),
    (8, 38), (119, 38), (20, 38), (107, 38), (8, 55), (119, 55),
    (20, 60), (108, 60), (8, 72), (119, 72), (8, 89), (119, 89),
    (20, 92), (108, 92), (6, 97), (96, 97), (18, 104), (47, 101),
    (80, 99), (124, 105), (36, 124), (72, 100), (93, 125), (4, 121),
    (30, 113), (63, 96), (115, 116), (54, 30), (99, 20), (25, 26),
)
CAT_TAIL_SWAY = (-3, -2, 0, 2, 3, 2, 1, 0, -1, -2, -3, -1, 1)
GHOST_BOB = (0, -1, -2, -1, 0, 1, 2, 1, 0, -1, -1, 0, 1)


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


def _draw_pixel_text(
    image: Image.Image, text: str, top: int, face: tuple[int, int, int], font_size: int = 16
) -> None:
    """Draw crisp 2x2-pixel lettering with a stepped, extruded 3D edge."""
    width, height = image.size
    pixel_block = 2
    small = Image.new("L", (width // pixel_block, height // pixel_block), 0)
    draw = ImageDraw.Draw(small)
    font = _font(max(1, round(font_size / pixel_block)))
    box = draw.textbbox((0, 0), text, font=font)
    x = (small.width - (box[2] - box[0])) // 2 - box[0]
    y = round(top / pixel_block) - box[1]
    draw.text((x, y), text, font=font, fill=255)
    mask = small.point(lambda value: 255 if value >= 128 else 0)
    mask = mask.resize(image.size, Image.Resampling.NEAREST)

    # Offset copies form a blocky extrusion; both title lines share the same face color and size.
    image.paste((67, 35, 55), (6, 6), mask)
    image.paste((139, 61, 48), (4, 4), mask)
    image.paste((205, 116, 55), (2, 2), mask)
    image.paste((255, 238, 183), (-1, -1), mask)
    image.paste(face, (0, 0), mask)


def _draw_ghost(image: Image.Image, x: int, y: int, frame_index: int, scale: float) -> None:
    draw = ImageDraw.Draw(image)
    pattern = GHOST_FRAMES[(frame_index // 2) % len(GHOST_FRAMES)]
    step = max(1, round(scale * 2))
    color = (212, 208, 238)
    for row, line in enumerate(pattern):
        for column, pixel in enumerate(line):
            if pixel == "#":
                left, top = x + column * step, y + row * step
                draw.rectangle((left, top, left + step - 1, top + step - 1), fill=color)
    draw.point((x + step * 2, y + step * 3), fill=(37, 30, 56))
    draw.point((x + step * 6, y + step * 3), fill=(37, 30, 56))


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


def _draw_pumpkin_vines(
    draw: ImageDraw.ImageDraw, width: int, height: int, scale: float, frame_index: int
) -> None:
    """Draw a lively pixel-art pumpkin patch along the bottom of the sign."""
    px = lambda value: max(1, round(value * scale))
    vine_points = []
    for x in range(0, width + px(2), px(2)):
        wave = sin((x / max(scale, 0.01) * 0.16) + frame_index * 0.22)
        vine_points.append((x, px(103) + round(wave * px(2))))
    draw.line(vine_points, fill=(58, 105, 57), width=px(2))
    draw.line([(x, y - px(1)) for x, y in vine_points], fill=(117, 157, 70), width=px(1))

    # Curled tendrils and leaves wave independently along the vine.
    for leaf_index, leaf_x in enumerate((17, 39, 70, 89, 117)):
        phase = frame_index * 0.13 + leaf_index * 1.7
        sway = round(sin(phase) * px(2))
        anchor_y = px(103) + round(sin(leaf_x * 0.16 + frame_index * 0.22) * px(2))
        leaf_y = anchor_y - px(3) + sway
        draw.polygon(
            ((px(leaf_x) - px(4), leaf_y), (px(leaf_x) - px(1), leaf_y - px(3)),
             (px(leaf_x) + px(4), leaf_y - px(2)), (px(leaf_x) + px(2), leaf_y + px(1))),
            fill=(76, 130, 59), outline=(146, 170, 75),
        )
        curl = round(sin(phase + 1.1) * px(2))
        draw.line(
            ((px(leaf_x), anchor_y), (px(leaf_x) + px(2) + curl, anchor_y - px(3)),
             (px(leaf_x) + px(5) + curl, anchor_y - px(3))),
            fill=(150, 174, 83), width=px(1),
        )

    pumpkin_xs = (px(4), px(50), px(96))
    for pumpkin_index, x in enumerate(pumpkin_xs):
        bob = round(sin(frame_index * 0.20 + pumpkin_index * 1.9) * px(1.5))
        y = px(109) + bob
        # Chunky stepped silhouette and three lobes make each pumpkin read at a glance.
        silhouette = (
            (x + px(7), y), (x + px(19), y), (x + px(22), y + px(3)),
            (x + px(25), y + px(3)), (x + px(27), y + px(6)),
            (x + px(27), y + px(12)), (x + px(24), y + px(15)),
            (x + px(20), y + px(17)), (x + px(6), y + px(17)),
            (x + px(2), y + px(15)), (x, y + px(12)), (x, y + px(6)),
            (x + px(3), y + px(3)), (x + px(6), y + px(3)),
        )
        draw.polygon(silhouette, fill=(231, 105, 30), outline=(255, 174, 69))
        draw.rectangle((x + px(9), y + px(1), x + px(17), y + px(15)), fill=(255, 143, 38))
        draw.line((x + px(5), y + px(5), x + px(5), y + px(13)), fill=(188, 72, 28), width=px(1))
        draw.line((x + px(21), y + px(5), x + px(21), y + px(13)), fill=(188, 72, 28), width=px(1))
        stem_sway = round(sin(frame_index * 0.16 + pumpkin_index) * px(1))
        draw.polygon(
            ((x + px(11), y + px(1)), (x + px(12) + stem_sway, y - px(3)),
             (x + px(16) + stem_sway, y - px(3)), (x + px(17), y + px(1))),
            fill=(99, 133, 59), outline=(163, 177, 83),
        )
        flicker = (frame_index // 2 + pumpkin_index * 5) % 12
        eye = (255, 238, 123) if flicker < 8 else (255, 187, 76)
        if flicker not in (10, 11):
            draw.polygon(
                ((x + px(6), y + px(7)), (x + px(9), y + px(5)), (x + px(10), y + px(9))),
                fill=eye,
            )
            draw.polygon(
                ((x + px(17), y + px(9)), (x + px(18), y + px(5)), (x + px(21), y + px(7))),
                fill=eye,
            )
            draw.polygon(
                ((x + px(7), y + px(11)), (x + px(20), y + px(11)),
                 (x + px(17), y + px(14)), (x + px(10), y + px(14))),
                fill=(255, 210, 102),
            )
        else:
            draw.line((x + px(6), y + px(7), x + px(10), y + px(7)), fill=eye, width=px(1))
            draw.line((x + px(17), y + px(7), x + px(21), y + px(7)), fill=eye, width=px(1))


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

    # Jagged farm silhouettes frame a clear night sky above the sign.
    draw.polygon(
        ((0, px(33)), (px(16), px(28)), (px(36), px(34)), (px(55), px(27)),
         (px(78), px(34)), (px(101), px(27)), (width, px(34)), (width, px(42)),
         (0, px(42))), fill=(35, 48, 65),
    )
    draw.rectangle((0, px(96), width, height), fill=(16, 30, 37))
    draw.polygon(((0, px(112)), (px(42), px(107)), (px(88), px(112)),
                  (width, px(106)), (width, height), (0, height)), fill=(23, 45, 39))

    # A carved, beveled farm sign makes the matched wordmark the visual anchor.
    left, top, right, bottom = px(3), px(35), px(124), px(94)
    draw.rectangle((left + px(3), top + px(3), right, bottom), fill=(8, 14, 20))
    draw.rectangle((left, top, right - px(3), bottom - px(3)), fill=(101, 60, 70))
    draw.rectangle((left + px(2), top + px(2), right - px(5), bottom - px(5)), fill=(35, 29, 48))
    draw.rectangle((left + px(5), top + px(5), right - px(8), bottom - px(8)), fill=(22, 48, 45))
    draw.line((left + px(7), top + px(7), right - px(10), top + px(7)), fill=(93, 135, 87))
    draw.line((left + px(7), bottom - px(10), right - px(10), bottom - px(10)), fill=(13, 29, 33))

    wordmark_face = (255, 204, 112)
    _draw_pixel_text(image, "POOR LOUIS", px(43), wordmark_face, font_size=16)
    _draw_pixel_text(image, "FARMS", px(66), wordmark_face, font_size=16)

    return image, scale


def build_animation_frames(width: int, height: int) -> tuple[bytes, ...]:
    """Pre-render the farm sign and Halloween animation frames at startup."""
    background, scale = _draw_static_sign(width, height)
    frame_count = 104
    frames = []
    for index in range(frame_count):
        frame = background.copy()
        ghost_phase = (index % 52) / 51
        ghost_x = round((35 + 96 * ghost_phase if ghost_phase <= 0.5
                         else 83 - 96 * (ghost_phase - 0.5)) * scale)
        ghost_y = round((11 + GHOST_BOB[(index // 2) % len(GHOST_BOB)]) * scale)
        _draw_ghost(frame, ghost_x, ghost_y, index, scale)
        draw = ImageDraw.Draw(frame)
        _draw_pumpkin_vines(draw, width, height, scale, index)
        _draw_twinkling_stars(draw, scale, index)
        _draw_moving_border(draw, scale, index, frame_count)
        _draw_black_cat(frame, round(4 * scale), round(7 * scale), scale, index)
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
