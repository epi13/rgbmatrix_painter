"""Low-load Poor Louis Farms fall sign for a HUB75 RGB matrix."""
from __future__ import annotations

import resource
import signal
import time
from functools import lru_cache
from math import cos, isclose, isfinite, pi, sin
from pathlib import Path
from typing import Callable, Iterable, Iterator

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

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


ANIMATION_LOOP_SECONDS = 6.5
DESIGN_TICKS_PER_SECOND = 8.0
LOOP_TICKS = ANIMATION_LOOP_SECONDS * DESIGN_TICKS_PER_SECOND


STAR_POSITIONS = (
    (4, 4), (14, 5), (34, 7), (43, 17), (54, 4), (62, 25), (74, 10),
    (82, 29), (90, 5), (127, 3), (39, 27), (55, 30), (76, 28), (89, 32),
    (126, 26), (8, 38), (20, 38), (107, 38), (119, 38), (8, 50), (119, 51),
    (20, 60), (108, 60), (8, 68), (119, 69), (8, 82), (119, 83), (20, 92),
    (108, 92), (6, 97), (28, 96), (43, 98), (63, 96), (79, 98), (96, 97),
    (124, 98), (18, 104), (35, 106), (47, 101), (80, 99), (112, 106),
    (36, 124), (56, 120), (72, 100), (93, 125), (4, 121), (126, 119),
    (24, 30), (69, 3), (99, 20), (25, 26), (115, 32), (2, 29), (127, 58),
    (2, 75), (125, 89), (12, 116), (62, 127), (105, 124), (37, 33),
    (3, 12), (24, 15), (46, 9), (68, 16), (77, 20), (120, 13),
    (3, 46), (125, 45), (3, 56), (125, 62), (4, 88), (123, 77),
    (26, 112), (59, 109), (86, 115), (121, 110),
    (17, 34), (30, 42), (48, 39), (66, 42), (78, 40), (106, 40),
    (17, 47), (35, 52), (56, 50), (79, 54), (99, 52), (113, 47),
    (28, 58), (51, 62), (72, 59), (95, 61), (17, 72), (34, 73),
    (58, 76), (78, 72), (102, 76), (114, 69), (29, 84), (51, 85),
    (76, 87), (101, 85), (116, 95), (15, 98), (52, 104), (68, 106),
    (90, 108), (120, 115),
)


def _mix_color(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))


def _shade_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)


@lru_cache(maxsize=16)
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


@lru_cache(maxsize=32)
def _text_masks(width: int, height: int, text: str, top: int, font_size: int) -> tuple[Image.Image, ...]:
    """Reuse glyphs and outlines for the few pixel positions in the title bob."""
    pixel_block = 2
    small = Image.new("L", (width // pixel_block, height // pixel_block), 0)
    draw = ImageDraw.Draw(small)
    font = _font(max(1, round(font_size / pixel_block)))
    box = draw.textbbox((0, 0), text, font=font)
    x = (small.width - (box[2] - box[0])) // 2 - box[0]
    y = round(top / pixel_block) - box[1]
    draw.text((x, y), text, font=font, fill=255)
    mask = small.point(lambda value: 255 if value >= 128 else 0)
    mask = mask.resize((width, height), Image.Resampling.NEAREST)
    expanded = mask.filter(ImageFilter.MaxFilter(5))
    inner_rim = mask.filter(ImageFilter.MaxFilter(3))
    return mask, ImageChops.subtract(expanded, inner_rim), ImageChops.subtract(inner_rim, mask)


def _draw_pixel_text(
    image: Image.Image,
    text: str,
    top: int,
    face: tuple[int, int, int],
    frame_index: float,
    font_size: int = 16,
) -> None:
    """Draw mint lettering with changing reflected light and a feathered shine."""
    width, height = image.size
    mask, outer_stroke, dark_stroke = _text_masks(width, height, text, top, font_size)
    reflected_light = (1 + sin(2 * pi * frame_index / 13)) / 2

    # Warm stepped extrusion gives the mint face depth while keeping the edges crisp.
    image.paste((27, 17, 47), (5, 5), mask)
    image.paste(_mix_color((54, 28, 80), (100, 54, 126), reflected_light), (4, 4), mask)
    image.paste(_mix_color((113, 43, 85), (172, 70, 112), reflected_light), (3, 3), mask)
    image.paste(_mix_color((188, 73, 44), (246, 131, 57), reflected_light), (2, 2), mask)
    image.paste((255, 150, 55), (1, 1), mask)

    image.paste(_mix_color((234, 108, 42), (255, 182, 78), reflected_light), (0, 0), outer_stroke)
    image.paste((4, 12, 20), (0, 0), dark_stroke)

    pulse = (1 + sin(2 * pi * frame_index / 26)) / 2
    animated_face = tuple(round(channel + (255 - channel) * pulse * 0.24) for channel in face)
    image.paste(animated_face, (0, 0), mask)

    # A diagonal glint travels over both lines and is clipped to the letter mask.
    shine = Image.new("L", image.size, 0)
    shine_draw = ImageDraw.Draw(shine)
    center = (frame_index / 26 % 1) * (width + 36) - 18
    for radius, opacity in ((8, 35), (5, 90), (2, 215)):
        shine_draw.polygon(
            ((round(center - radius), 0), (round(center + radius), 0),
             (round(center + radius - 24), height), (round(center - radius - 24), height)),
            fill=opacity,
        )
    shine_mask = ImageChops.multiply(mask, shine)
    image.paste((230, 255, 234), (0, 0), shine_mask)


def _draw_witch_broom(image: Image.Image, x: int, y: int, scale: float, frame_index: float) -> None:
    """Draw a bright, lively witch with a fluttering cape and animated broom."""
    draw = ImageDraw.Draw(image)
    unit = max(1, round(scale))
    point = lambda column, row: (x + column * unit, y + row * unit)
    flutter = int(frame_index // 2) % 4
    broom_tilt = (0, 1, 0, -1)[flutter]
    broom_flicker = int(frame_index) % 4
    moonlight = (1 + sin(frame_index * 2 * pi / 13)) / 2
    cape_light = _mix_color((73, 30, 117), (128, 57, 166), moonlight)
    rim_light = _mix_color((190, 102, 226), (245, 180, 255), moonlight)

    # A glowing, rippled broom and bristles make the ride read clearly in motion.
    draw.polygon(
        tuple(point(*p) for p in ((2, 12), (8, 12), (7, 18 + broom_flicker % 2),
                                  (5, 20), (4, 16), (1, 19 - broom_flicker % 2),
                                  (2, 15), (0, 16))),
        fill=(189, 83, 37), outline=(255, 190, 83),
    )
    draw.line((point(2, 14), point(7, 14)), fill=(255, 174, 61), width=unit)
    draw.line((point(3, 17), point(6, 16)), fill=(115, 45, 35), width=unit)
    draw.line((point(6, 15), point(32, 9 + broom_tilt)), fill=(79, 37, 42), width=unit * 3)
    draw.line((point(7, 14), point(31, 8 + broom_tilt)), fill=(255, 164, 70), width=unit)
    draw.line((point(7, 13), point(8, 15)), fill=(255, 226, 130), width=unit)

    # A tiny black cat perches behind the witch on the broom's trailing end.
    cat_outline = (141, 123, 201)
    cat_points = ((1, 10), (2, 8), (4, 7), (5, 4), (7, 6), (9, 6),
                  (11, 4), (12, 7), (14, 8), (15, 10), (13, 12),
                  (5, 12), (3, 11))
    draw.polygon(tuple(point(*p) for p in cat_points), fill=(4, 4, 14), outline=cat_outline)
    tail_lift = int(frame_index // 3) % 2
    draw.line((point(2, 10), point(0, 9), point(0, 7 - tail_lift), point(2, 6 - tail_lift)),
              fill=(181, 153, 231), width=unit)
    draw.point(point(7, 8), fill=(255, 211, 121))
    draw.point(point(10, 8), fill=(136, 250, 228))
    draw.line((point(6, 10), point(11, 10)), fill=(58, 53, 83), width=unit)

    # Boots and legs hang behind a cape whose trailing edge flaps rapidly.
    draw.line((point(17, 11), point(14, 14), point(12, 16)), fill=(255, 178, 99), width=unit * 2)
    draw.line((point(19, 11), point(18, 14), point(16, 16)), fill=(255, 178, 99), width=unit * 2)
    cape_tail = (16, 17, 15, 18)[flutter]
    draw.polygon(
        tuple(point(*p) for p in ((13, 8), (21, 8), (24, 12), (22, 14),
                                   (19, 13), (17, cape_tail - 2), (14, 14),
                                   (10 - flutter % 2, cape_tail), (11, 11))),
        fill=cape_light, outline=rim_light,
    )
    draw.line((point(13, 10), point(11 - flutter % 2, 13 + flutter % 3)),
              fill=(255, 133, 220), width=unit)
    draw.line((point(19, 10), point(21, 12)), fill=(255, 206, 111), width=unit * 2)
    draw.line((point(14, 11), point(18, 12)),
              fill=_mix_color((133, 70, 192), (217, 139, 239), moonlight), width=unit)

    # Bright hair frames a clearly lit face beneath a high-contrast witch's hat.
    draw.rectangle((x + 17 * unit, y + 5 * unit, x + 23 * unit, y + 11 * unit), fill=(235, 117, 77))
    draw.rectangle((x + 18 * unit, y + 6 * unit, x + 22 * unit, y + 10 * unit), fill=(255, 211, 151))
    draw.line((point(19, 8), point(21, 8)), fill=(72, 36, 68), width=unit)
    draw.point(point(23, 9), fill=(255, 180, 92))  # pointed nose, facing forward
    draw.polygon(
        tuple(point(*p) for p in ((13, 5), (19, 4), (21, 0), (24, 4),
                                   (29, 6), (24, 7), (15, 7))),
        fill=_mix_color((40, 22, 84), (79, 39, 123), moonlight), outline=rim_light,
    )
    draw.line((point(17, 5), point(25, 5)), fill=(255, 153, 79), width=unit)
    draw.line((point(19, 1), point(22, 2)), fill=(246, 211, 255), width=unit)
    if frame_index % 8 < 4:
        draw.point(point(18, 6), fill=(255, 228, 164))
    else:
        draw.point(point(18, 6), fill=(89, 41, 103))

    # Moving cross-sparkles and ember motes leave a short, shifting flight trail.
    trail_palette = ((125, 255, 230), (255, 159, 83), (238, 154, 255))
    for trail_index, trail_x in enumerate((-4, -9, -14)):
        trail_phase = (frame_index + trail_index * 3) % 8
        if trail_phase < 5:
            trail_y = round(11 + sin(frame_index * 2 * pi / 13 + trail_index * 2) * 3)
            tx, ty = point(trail_x, trail_y)
            palette_index = int(frame_index // 2 + trail_index) % len(trail_palette)
            glow = sin(pi * trail_phase / 5) ** 0.5
            color = _shade_color(trail_palette[palette_index], 0.3 + glow * 0.7)
            draw.point((tx, ty), fill=color)
            if trail_phase < 2:
                draw.line((tx - unit, ty, tx + unit, ty), fill=color)
                draw.line((tx, ty - unit, tx, ty + unit), fill=color)


def _draw_twinkling_stars(draw: ImageDraw.ImageDraw, scale: float, frame_index: float) -> None:
    """Cycle colorful cross-sparkles around the title and Halloween scene."""
    px = lambda value: round(value * scale)
    palettes = (
        ((255, 231, 142), (166, 126, 71)),
        ((113, 244, 232), (52, 133, 151)),
        ((244, 157, 255), (140, 91, 174)),
        ((255, 151, 111), (166, 86, 76)),
    )
    for star_index, (star_x, star_y) in enumerate(STAR_POSITIONS):
        phase = (frame_index + star_index * 7) % 26
        x, y = px(star_x), px(star_y)
        bright, dim = palettes[star_index % len(palettes)]
        intensity = ((1 + cos(2 * pi * phase / 26)) / 2) ** 2
        color = _mix_color(_shade_color(dim, 0.35), bright, intensity)
        draw.point((x, y), fill=color)
        if intensity > 0.18:
            radius = 3 if intensity > 0.82 and star_index % 3 == 0 else 2 if intensity > 0.45 else 1
            ray_color = _shade_color(bright, intensity ** 0.5)
            draw.line((x - radius, y, x + radius, y), fill=ray_color)
            draw.line((x, y - radius, x, y + radius), fill=ray_color)
            if intensity > 0.6:
                draw.line((x - 1, y - 1, x + 1, y + 1), fill=ray_color)
                draw.line((x - 1, y + 1, x + 1, y - 1), fill=ray_color)
            if star_index % 4 == 0:
                satellite = _shade_color((255, 246, 217), intensity)
                draw.point((x - 2, y - 2), fill=satellite)
                draw.point((x + 2, y + 2), fill=satellite)


def _draw_detailed_moon(draw: ImageDraw.ImageDraw, scale: float) -> None:
    """Paint a layered crescent with a colored halo, craters, and lit rim."""
    px = lambda value: round(value * scale)
    draw.ellipse((px(87), px(0), px(127), px(40)), outline=(54, 45, 94), width=px(2))
    draw.ellipse((px(90), px(2), px(124), px(36)), outline=(80, 92, 146), width=px(1))
    draw.ellipse((px(93), px(3), px(123), px(33)), fill=(255, 217, 133), outline=(255, 241, 190))
    draw.ellipse((px(103), px(0), px(131), px(27)), fill=(0, 0, 0))
    # Pixel clusters and crater rings are concentrated in the illuminated crescent.
    draw.ellipse((px(96), px(9), px(100), px(13)), fill=(224, 169, 104), outline=(255, 233, 173))
    draw.ellipse((px(98), px(20), px(103), px(24)), fill=(238, 182, 105))
    draw.ellipse((px(101), px(14), px(103), px(16)), fill=(255, 243, 190))
    draw.rectangle((px(95), px(16), px(96), px(18)), fill=(255, 248, 204))
    draw.point((px(99), px(7)), fill=(255, 249, 218))
    draw.point((px(103), px(27)), fill=(250, 199, 116))
    # Cool edge light separates the shadowed rim from the night sky.
    draw.arc((px(96), px(4), px(123), px(33)), 92, 255, fill=(134, 194, 224), width=px(1))


def _draw_moon_glint(draw: ImageDraw.ImageDraw, scale: float, frame_index: float) -> None:
    """Send a tiny cool sparkle along the moon's bright inner crescent."""
    px = lambda value: round(value * scale)
    phase = 2 * pi * frame_index / 26
    position = (1 + sin(phase)) / 2
    x, y = round(94 + abs(2 * position - 1) * 3), round(8 + position * 19)
    glow = (1 + cos(phase * 2)) / 2
    color = _mix_color((255, 224, 145), (151, 255, 244), glow)
    draw.point((px(x), px(y)), fill=color)
    if glow > 0.7:
        draw.line((px(x - 1), px(y), px(x + 1), px(y)), fill=color)
        draw.line((px(x), px(y - 1), px(x), px(y + 1)), fill=color)


def _draw_static_sign(width: int, height: int) -> tuple[Image.Image, float]:
    image = Image.new("RGB", (width, height), (0, 0, 0))
    scale = min(width / 128, height / 128)
    return image, scale


def animation_frame_count(fps: float = ANIMATION_FPS) -> int:
    if not isfinite(fps) or fps <= 0:
        raise ValueError("Animation FPS must be finite and positive")
    return max(1, round(ANIMATION_LOOP_SECONDS * fps))


def refresh_fraction(refresh_hz: float, fps: float) -> int:
    """Use a whole number of panel refreshes for each animation frame."""
    animation_frame_count(fps)
    if not isfinite(refresh_hz) or refresh_hz <= 0:
        raise ValueError("Panel refresh limit must be finite and positive")
    fraction = round(refresh_hz / fps)
    if not 1 <= fraction <= 255 or not isclose(refresh_hz / fraction, fps):
        raise ValueError("Animation FPS must evenly divide the panel refresh limit")
    return fraction


def iter_animation_frames(width: int, height: int, fps: float = ANIMATION_FPS) -> Iterator[Image.Image]:
    """Sample the same 6.5-second scene at the requested playback rate."""
    background, scale = _draw_static_sign(width, height)
    frame_count = animation_frame_count(fps)
    wordmark_face = (111, 241, 204)
    for index in range(frame_count):
        tick = index * LOOP_TICKS / frame_count
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        _draw_twinkling_stars(draw, scale, tick)
        _draw_detailed_moon(draw, scale)
        _draw_moon_glint(draw, scale, tick)
        title_bob = round(sin(2 * pi * tick / 26) * 2.1 * scale)
        _draw_pixel_text(frame, "POOR LOUIS", round(46 * scale) + title_bob,
                         wordmark_face, frame_index=tick, font_size=16)
        _draw_pixel_text(frame, "FARMS", round(70 * scale) + title_bob,
                         wordmark_face, frame_index=tick, font_size=16)
        witch_phase = index / frame_count
        witch_x = round((-34 + (width / max(scale, 0.01) + 68) * witch_phase) * scale)
        witch_y = round((8 + sin(tick * 2 * pi / 13) * 2.8) * scale)
        _draw_witch_broom(frame, witch_x, witch_y, scale, tick)
        yield frame


def build_animation_frames(width: int, height: int, fps: float = ANIMATION_FPS) -> tuple[bytes, ...]:
    """Return RGB frames for previews; hardware playback uses the image iterator."""
    return tuple(image.tobytes() for image in iter_animation_frames(width, height, fps))


def cache_animation_canvases(
    matrix: object,
    images: Iterable[Image.Image],
    should_continue: Callable[[], bool],
) -> tuple[object, ...]:
    """Compile one frame at a time, then retain only native panel buffers."""
    canvases = []
    for image in images:
        if not should_continue():
            break
        canvas = matrix.CreateFrameCanvas()
        # One-time safe uploads avoid depending on Pillow's private memory layout.
        canvas.SetImage(image, unsafe=False)
        canvases.append(canvas)
        if len(canvases) == 1:
            matrix.SwapOnVSync(canvas)
    return tuple(canvases)


def play_cached_animation(
    matrix: object,
    canvases: tuple[object, ...],
    fps: float,
    refresh_hz: float,
    should_continue: Callable[[], bool],
) -> None:
    """Playback only swaps immutable buffers, paced entirely by panel VSync."""
    fraction = refresh_fraction(refresh_hz, fps)
    if not canvases:
        raise ValueError("Native animation cache is empty")
    frame_index = 0
    count = 0
    report_frames = max(1, round(fps * 10))
    started, cpu_started = time.monotonic(), time.thread_time()
    while should_continue():
        matrix.SwapOnVSync(canvases[frame_index], fraction)
        frame_index = (frame_index + 1) % len(canvases)
        count += 1
        if count >= report_frames:
            now, cpu_now = time.monotonic(), time.thread_time()
            elapsed = now - started
            print(
                f"Playback: actual_fps={count / elapsed:.2f}, "
                f"animation_thread_cpu_percent={(cpu_now - cpu_started) / elapsed * 100:.2f}",
                flush=True,
            )
            started, cpu_started = now, cpu_now
            count = 0
            report_frames = max(1, round(fps * 60))


def main() -> None:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    fraction = refresh_fraction(MATRIX_REFRESH_LIMIT_HZ, ANIMATION_FPS)
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
        started = time.monotonic()
        print(f"Building native animation cache: fps={ANIMATION_FPS}, frames={animation_frame_count()}", flush=True)
        canvases = cache_animation_canvases(
            matrix, iter_animation_frames(matrix.width, matrix.height), lambda: running
        )
        if not running:
            return
        print(
            f"RGB matrix canvas: {matrix.width}x{matrix.height} "
            f"(chain={CHAIN_LENGTH}, mapper={PIXEL_MAPPER_CONFIG}, "
            f"pwm_bits={PWM_BITS}, pwm_dither_bits={PWM_DITHER_BITS}, "
            f"max_refresh_hz={MATRIX_REFRESH_LIMIT_HZ}, "
            f"busy_waiting={not DISABLE_BUSY_WAITING}, "
            f"animation_fps={ANIMATION_FPS}, "
            f"pre_rendered_frames={len(canvases)}, "
            f"vsync_fraction={fraction}, "
            f"cache_build_seconds={time.monotonic() - started:.2f}, "
            f"peak_rss_mib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f})",
            flush=True,
        )
        play_cached_animation(matrix, canvases, ANIMATION_FPS, MATRIX_REFRESH_LIMIT_HZ, lambda: running)
    finally:
        matrix.Clear()


if __name__ == "__main__":
    main()
