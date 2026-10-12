"""Low-load Poor Louis Farms fall sign for a HUB75 RGB matrix."""
from __future__ import annotations

import signal
import time
from functools import lru_cache
from math import cos, pi, sin
from pathlib import Path

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
)
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


def _draw_pixel_text(
    image: Image.Image,
    text: str,
    top: int,
    face: tuple[int, int, int],
    frame_index: int,
    font_size: int = 16,
) -> None:
    """Draw high-contrast pixel lettering with a moving, clipped shine."""
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

    # Warm stepped extrusion gives the mint face depth while keeping the edges crisp.
    image.paste((27, 17, 47), (5, 5), mask)
    image.paste((74, 34, 91), (4, 4), mask)
    image.paste((143, 54, 89), (3, 3), mask)
    image.paste((226, 91, 49), (2, 2), mask)
    image.paste((255, 150, 55), (1, 1), mask)

    expanded = mask.filter(ImageFilter.MaxFilter(5))
    inner_rim = mask.filter(ImageFilter.MaxFilter(3))
    outer_stroke = ImageChops.subtract(expanded, inner_rim)
    dark_stroke = ImageChops.subtract(inner_rim, mask)
    image.paste((255, 145, 61), (0, 0), outer_stroke)
    image.paste((4, 12, 20), (0, 0), dark_stroke)

    pulse = (1 + sin(2 * pi * frame_index / 26)) / 2
    animated_face = tuple(round(channel + (255 - channel) * pulse * 0.24) for channel in face)
    image.paste(animated_face, (0, 0), mask)

    # A diagonal glint travels over both lines and is clipped to the letter mask.
    shine = Image.new("L", image.size, 0)
    shine_draw = ImageDraw.Draw(shine)
    center = (frame_index * 5) % (width + 28) - 14
    shine_draw.polygon(
        ((center - 4, 0), (center + 1, 0), (center - 23, height), (center - 28, height)),
        fill=176,
    )
    shine_mask = ImageChops.multiply(mask, shine)
    image.paste((230, 255, 234), (0, 0), shine_mask)


def _draw_witch_broom(image: Image.Image, x: int, y: int, scale: float, frame_index: int) -> None:
    """Draw a bright, lively witch with a fluttering cape and animated broom."""
    draw = ImageDraw.Draw(image)
    unit = max(1, round(scale))
    point = lambda column, row: (x + column * unit, y + row * unit)
    flutter = (frame_index // 2) % 4
    broom_tilt = (0, 1, 0, -1)[flutter]
    broom_flicker = frame_index % 4

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

    # Boots and legs hang behind a cape whose trailing edge flaps rapidly.
    draw.line((point(17, 11), point(14, 14), point(12, 16)), fill=(255, 178, 99), width=unit * 2)
    draw.line((point(19, 11), point(18, 14), point(16, 16)), fill=(255, 178, 99), width=unit * 2)
    cape_tail = (16, 17, 15, 18)[flutter]
    draw.polygon(
        tuple(point(*p) for p in ((13, 8), (21, 8), (24, 12), (22, 14),
                                   (19, 13), (17, cape_tail - 2), (14, 14),
                                   (10 - flutter % 2, cape_tail), (11, 11))),
        fill=(91, 39, 132), outline=(226, 125, 238),
    )
    draw.line((point(13, 10), point(11 - flutter % 2, 13 + flutter % 3)),
              fill=(255, 133, 220), width=unit)
    draw.line((point(19, 10), point(21, 12)), fill=(255, 206, 111), width=unit * 2)
    draw.line((point(14, 11), point(18, 12)), fill=(160, 97, 222), width=unit)

    # Bright hair frames a clearly lit face beneath a high-contrast witch's hat.
    draw.rectangle((x + 17 * unit, y + 5 * unit, x + 23 * unit, y + 11 * unit), fill=(235, 117, 77))
    draw.rectangle((x + 18 * unit, y + 6 * unit, x + 22 * unit, y + 10 * unit), fill=(255, 211, 151))
    draw.line((point(19, 8), point(21, 8)), fill=(72, 36, 68), width=unit)
    draw.point(point(23, 9), fill=(255, 180, 92))  # pointed nose, facing forward
    draw.polygon(
        tuple(point(*p) for p in ((13, 5), (19, 4), (21, 0), (24, 4),
                                   (29, 6), (24, 7), (15, 7))),
        fill=(55, 29, 99), outline=(222, 157, 255),
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
            trail_y = 9 + ((trail_index * 3 + frame_index // 2) % 7) - trail_phase // 2
            tx, ty = point(trail_x, trail_y)
            color = trail_palette[(frame_index // 2 + trail_index) % len(trail_palette)]
            draw.point((tx, ty), fill=color)
            if trail_phase in (0, 1):
                draw.line((tx - unit, ty, tx + unit, ty), fill=color)
                draw.line((tx, ty - unit, tx, ty + unit), fill=color)


def _draw_twinkling_stars(draw: ImageDraw.ImageDraw, scale: float, frame_index: int) -> None:
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
        if phase >= 24:
            continue
        x, y = px(star_x), px(star_y)
        bright, dim = palettes[star_index % len(palettes)]
        color = bright if phase < 12 else dim
        draw.point((x, y), fill=color)
        if phase < 9:
            radius = 3 if phase < 3 and star_index % 3 == 0 else 2 if phase < 6 else 1
            draw.line((x - radius, y, x + radius, y), fill=bright)
            draw.line((x, y - radius, x, y + radius), fill=bright)
            if phase < 4:
                draw.line((x - 1, y - 1, x + 1, y + 1), fill=bright)
                draw.line((x - 1, y + 1, x + 1, y - 1), fill=bright)
            if star_index % 4 == 0:
                draw.point((x - 2, y - 2), fill=(255, 246, 217))
                draw.point((x + 2, y + 2), fill=(255, 246, 217))


def _draw_pumpkin_vines(
    draw: ImageDraw.ImageDraw, width: int, height: int, scale: float, frame_index: int
) -> None:
    """Draw detailed, animated jack-o'-lanterns among curling, layered vines."""
    px = lambda value: max(1, round(value * scale))
    def p(x: float, y: float) -> tuple[int, int]:
        return px(x), px(y)

    loop_phase = 2 * pi * frame_index / 26
    main_vine = []
    back_vine = []
    for x in range(0, width + px(2), px(2)):
        design_x = x / max(scale, 0.01)
        wave = sin(design_x * 0.15 + loop_phase)
        main_vine.append((x, px(103) + round(wave * px(2))))
        back_vine.append((x, px(100) + round(sin(design_x * 0.11 - loop_phase * 2) * px(1.5))))
    draw.line(back_vine, fill=(48, 74, 71), width=px(2))
    draw.line([(x, y - px(1)) for x, y in back_vine], fill=(87, 117, 90), width=px(1))
    draw.line(main_vine, fill=(54, 91, 49), width=px(3))
    draw.line([(x, y - px(1)) for x, y in main_vine], fill=(122, 159, 69), width=px(1))

    # Leaves, veins, tiny buds and corkscrew tendrils sway at different rates.
    leaf_palette = ((78, 127, 54), (105, 145, 57), (68, 112, 69), (147, 151, 62))
    leaf_positions = (9, 17, 28, 39, 47, 68, 78, 89, 101, 112, 122)
    for leaf_index, leaf_x in enumerate(leaf_positions):
        phase = loop_phase * (2 if leaf_index % 3 == 0 else 1) + leaf_index * 1.8
        sway_x = round(sin(phase) * px(2))
        anchor_y = px(101) + round(sin(leaf_x * 0.15 + loop_phase) * px(2))
        direction = -1 if leaf_index % 2 == 0 else 1
        tip = (px(leaf_x) + sway_x, anchor_y - px(5) * direction)
        mid_left = (px(leaf_x) - px(4) + sway_x, anchor_y - px(4) * direction)
        mid_right = (px(leaf_x) + px(4) + sway_x, anchor_y - px(3) * direction)
        leaf_color = leaf_palette[leaf_index % len(leaf_palette)]
        base = (px(leaf_x), anchor_y)
        draw.polygon((base, mid_left, tip, mid_right), fill=leaf_color, outline=(174, 183, 92))
        draw.line((base, tip), fill=(190, 190, 96), width=px(1))
        draw.line((mid_left, p(leaf_x - 1, (anchor_y / max(scale, 0.01)) - direction * 2)),
                  fill=(136, 166, 75), width=px(1))
        draw.line((mid_right, p(leaf_x + 1, (anchor_y / max(scale, 0.01)) - direction * 2)),
                  fill=(136, 166, 75), width=px(1))

        curl = round(sin(phase + 1.2) * px(2))
        base = (px(leaf_x), anchor_y)
        curl_points = (base, (px(leaf_x + 2) + curl, anchor_y - px(2)),
                       (px(leaf_x + 5) + curl, anchor_y - px(2)),
                       (px(leaf_x + 5) + curl, anchor_y - px(4)),
                       (px(leaf_x + 3) + curl, anchor_y - px(4)))
        draw.line(curl_points, fill=(170, 187, 89), width=px(1))
        if leaf_index % 3 == 0:
            bud_x, bud_y = px(leaf_x + 7) + curl, anchor_y - px(2)
            draw.rectangle((bud_x, bud_y, bud_x + px(1), bud_y + px(1)), fill=(231, 157, 76))

    palettes = (
        ((184, 58, 30), (224, 83, 31), (252, 126, 40), (255, 174, 63)),
        ((171, 65, 28), (228, 102, 28), (255, 151, 42), (255, 195, 81)),
        ((164, 49, 36), (218, 76, 34), (247, 121, 47), (255, 177, 78)),
    )
    pumpkin_xs = (px(4), px(50), px(96))
    for pumpkin_index, x in enumerate(pumpkin_xs):
        phase = loop_phase + pumpkin_index * 1.6
        bob = round(sin(phase) * px(1.8))
        y = px(109) + bob
        outline, body, lit, highlight = palettes[pumpkin_index]
        # Deep silhouette, rounded lobes, bright center, and dark rib grooves.
        silhouette = (
            (x + px(7), y), (x + px(19), y), (x + px(22), y + px(2)),
            (x + px(25), y + px(3)), (x + px(27), y + px(6)),
            (x + px(27), y + px(12)), (x + px(24), y + px(16)),
            (x + px(20), y + px(19)), (x + px(7), y + px(19)),
            (x + px(3), y + px(17)), (x, y + px(13)), (x, y + px(7)),
            (x + px(3), y + px(3)), (x + px(6), y + px(2)),
        )
        draw.polygon(silhouette, fill=body, outline=(255, 177, 91))
        draw.polygon(
            ((x + px(4), y + px(5)), (x + px(9), y + px(2)),
             (x + px(11), y + px(4)), (x + px(9), y + px(15)), (x + px(5), y + px(16))),
            fill=lit,
        )
        draw.polygon(
            ((x + px(11), y + px(3)), (x + px(17), y + px(3)),
             (x + px(19), y + px(16)), (x + px(16), y + px(18)),
             (x + px(12), y + px(16))),
            fill=highlight,
        )
        for groove_x in (px(5), px(10), px(18), px(23)):
            draw.line((x + groove_x, y + px(6), x + groove_x - px(1), y + px(13)),
                      fill=outline, width=px(1))
        draw.point((x + px(7), y + px(4)), fill=(255, 210, 117))
        draw.point((x + px(20), y + px(16)), fill=(194, 70, 29))
        stem_sway = round(sin(loop_phase * 2 + pumpkin_index) * px(1))
        draw.polygon(
            ((x + px(11), y + px(2)), (x + px(12) + stem_sway, y - px(3)),
             (x + px(16) + stem_sway, y - px(3)), (x + px(18), y + px(2))),
            fill=(84, 119, 53), outline=(163, 181, 91),
        )
        draw.line((x + px(14) + stem_sway, y - px(2), x + px(15) + stem_sway, y),
                  fill=(195, 187, 92), width=px(1))

        # Carved faces morph from a straight baseline mouth into a broad smile, then reset.
        smile_phase = ((frame_index + pumpkin_index * 7) % 26) / 25
        smile = (1 - cos(2 * pi * smile_phase)) / 2
        smile_depth = round(smile * 4)
        cutout = (17, 9, 10)
        blink = (frame_index + pumpkin_index * 13) % 26 in (0, 1, 2)
        if blink:
            draw.line((x + px(6), y + px(7), x + px(10), y + px(7)), fill=cutout, width=px(2))
            draw.line((x + px(17), y + px(7), x + px(21), y + px(7)), fill=cutout, width=px(2))
        else:
            draw.polygon(((x + px(5), y + px(8)), (x + px(8), y + px(5)),
                          (x + px(11), y + px(8)), (x + px(10), y + px(10))), fill=cutout)
            draw.polygon(((x + px(16), y + px(8)), (x + px(19), y + px(5)),
                          (x + px(22), y + px(8)), (x + px(17), y + px(10))), fill=cutout)
        draw.polygon(((x + px(12), y + px(10)), (x + px(14), y + px(10)),
                      (x + px(13), y + px(12))), fill=cutout)
        mouth_left, mouth_right = x + px(7), x + px(21)
        mouth_top = y + px(12)
        if smile_depth == 0:
            draw.line((mouth_left, mouth_top, mouth_right, mouth_top), fill=cutout, width=px(2))
        else:
            mouth = (
                (mouth_left, mouth_top), (mouth_right, mouth_top),
                (x + px(19), mouth_top + px(2 + smile_depth // 2)),
                (x + px(15), mouth_top + px(2 + smile_depth)),
                (x + px(11), mouth_top + px(2 + smile_depth)),
                (x + px(8), mouth_top + px(2 + smile_depth // 2)),
            )
            draw.polygon(mouth, fill=cutout)


def _draw_halloween_border(
    draw: ImageDraw.ImageDraw, scale: float, frame_index: int, frame_count: int
) -> None:
    px = lambda value: round(value * scale)
    left, top, right, bottom = px(2), px(34), px(125), px(95)
    # Each side ripples independently; corner gaps are filled by pixel pumpkins.
    path: list[tuple[int, int, int, int, int, int]] = []
    for x in range(left + px(10), right - px(9)):
        design_x = x / max(scale, 0.01)
        ripple = round(sin(design_x * 0.25 + frame_index * 0.61) * px(3.0))
        path.append((x, top + px(1) + ripple, 0, -1, 1, 0))
    for y in range(top + px(10), bottom - px(9)):
        design_y = y / max(scale, 0.01)
        ripple = round(sin(design_y * 0.22 - frame_index * 0.57) * px(2.2))
        path.append((right - px(1) + ripple, y, 1, 0, 0, 1))
    for x in range(right - px(10), left + px(9), -1):
        design_x = x / max(scale, 0.01)
        ripple = round(sin(design_x * 0.24 - frame_index * 0.63 + 1) * px(3.0))
        path.append((x, bottom - px(1) + ripple, 0, 1, -1, 0))
    for y in range(bottom - px(10), top + px(9), -1):
        design_y = y / max(scale, 0.01)
        ripple = round(sin(design_y * 0.2 + frame_index * 0.59 + 2) * px(2.2))
        path.append((left + px(1) + ripple, y, -1, 0, 0, -1))
    if not path:
        return

    # The moving fire edge is organic, with no continuous straight rail beneath it.
    fire_colors = (
        (105, 34, 45), (168, 47, 31), (221, 67, 27),
        (255, 117, 31), (255, 180, 58), (255, 226, 113),
    )
    for position, (x, y, _, _, _, _) in enumerate(path):
        heat = (position * 3 + frame_index * 5) % 29
        color_index = 0 if heat < 3 else 1 if heat < 7 else 2 if heat < 12 else 3 if heat < 17 else 4 if heat < 23 else 5
        draw.point((x, y), fill=fire_colors[color_index])

    # Flame tongues lean, stretch, and retract as embers race around the wavy edge.
    flame_step = max(4, round(6 * scale))
    step = max(1, round(scale))
    stream_shift = round(frame_index * len(path) / max(1, frame_count))
    for flame_index, start in enumerate(range(0, len(path), flame_step)):
        x, y, nx, ny, tx, ty = path[(start + stream_shift) % len(path)]
        flicker = (frame_index + flame_index * 3) % 6
        length = (2 + flicker % 4) * step
        lean = ((frame_index // 2 + flame_index) % 3 - 1) * step
        flame = (
            (x - tx * 2 * step, y - ty * 2 * step),
            (x + tx * 2 * step, y + ty * 2 * step),
            (x + tx * step + nx * step, y + ty * step + ny * step),
            (x + nx * length + tx * lean, y + ny * length + ty * lean),
            (x - tx * step + nx * step, y - ty * step + ny * step),
        )
        draw.polygon(flame, fill=(237, 77, 28))
        if flicker % 3 != 0:
            draw.line((x + nx * step, y + ny * step,
                       x + nx * max(step, length - step) + tx * lean,
                       y + ny * max(step, length - step) + ty * lean),
                      fill=(255, 193, 72), width=step)
        if flicker in (0, 1):
            draw.point((x + nx * (length + step), y + ny * (length + step)),
                       fill=(255, 237, 166))

    # Rounded pixel pumpkins occupy the corners; their carved features stay black.
    corners = ((4, 36), (116, 36), (4, 86), (116, 86))
    pumpkin_shape = ((2, 0), (5, 0), (7, 2), (8, 4), (7, 7), (5, 8),
                     (2, 8), (0, 6), (0, 3), (1, 1))
    for pumpkin_index, (design_x, design_y) in enumerate(corners):
        x = px(design_x)
        y = px(design_y + round(sin(frame_index * 2 * pi / 13 + pumpkin_index) * 0.6))
        points = tuple((x + px(dx), y + px(dy)) for dx, dy in pumpkin_shape)
        draw.polygon(points, fill=(226, 83, 31), outline=(255, 172, 70))
        draw.line((x + px(3), y + px(1), x + px(4), y - px(1)),
                  fill=(116, 153, 67), width=px(1))
        blink = (frame_index // 2 + pumpkin_index * 4) % 13 < 2
        cutout = (18, 8, 9)
        if blink:
            draw.line((x + px(2), y + px(4), x + px(3), y + px(4)), fill=cutout)
            draw.line((x + px(5), y + px(4), x + px(6), y + px(4)), fill=cutout)
        else:
            draw.point((x + px(2), y + px(3)), fill=cutout)
            draw.point((x + px(6), y + px(3)), fill=cutout)
        draw.line((x + px(2), y + px(6), x + px(6), y + px(6)), fill=cutout, width=px(1))


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


def _draw_moon_glint(draw: ImageDraw.ImageDraw, scale: float, frame_index: int) -> None:
    """Send a tiny cool sparkle along the moon's bright inner crescent."""
    px = lambda value: round(value * scale)
    glints = ((97, 8), (95, 12), (94, 17), (95, 22), (98, 27))
    x, y = glints[(frame_index // 2) % len(glints)]
    color = (151, 255, 244) if (frame_index // 2) % 3 else (255, 245, 183)
    draw.point((px(x), px(y)), fill=color)
    if frame_index % 6 in (0, 1):
        draw.line((px(x - 1), px(y), px(x + 1), px(y)), fill=color)
        draw.line((px(x), px(y - 1), px(x), px(y + 1)), fill=color)


def _draw_wavy_panel(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    color: tuple[int, int, int],
    scale: float,
    phase: float,
) -> None:
    """Fill a gently irregular pixel-board layer with no ruler-straight edges."""
    left, top, right, bottom = bounds
    stride = max(1, round(2 * scale))
    points: list[tuple[int, int]] = []

    def wave(position: int, offset: float) -> int:
        design_position = position / max(scale, 0.01)
        movement = sin(design_position * 0.27 + phase + offset)
        movement += 0.35 * sin(design_position * 0.61 - phase * 1.4 + offset)
        return round(movement * 1.8 * scale)

    xs = list(range(left, right + 1, stride))
    ys = list(range(top, bottom + 1, stride))
    if xs[-1] != right:
        xs.append(right)
    if ys[-1] != bottom:
        ys.append(bottom)
    points.extend((x, top + wave(x, 0)) for x in xs)
    points.extend((right + wave(y, 1.7), y) for y in ys[1:])
    points.extend((x, bottom + wave(x, 3.1)) for x in reversed(xs[:-1]))
    points.extend((left + wave(y, 4.8), y) for y in reversed(ys[1:-1]))
    draw.polygon(points, fill=color)


def _draw_static_sign(width: int, height: int) -> tuple[Image.Image, float]:
    sky = (0, 0, 0)
    image = Image.new("RGB", (width, height), sky)
    draw = ImageDraw.Draw(image)
    scale = min(width / 128, height / 128)
    px = lambda value: max(1, round(value * scale))

    _draw_detailed_moon(draw, scale)

    # Jagged farm silhouettes frame a clear night sky above the sign.
    draw.polygon(
        ((0, px(33)), (px(16), px(28)), (px(36), px(34)), (px(55), px(27)),
         (px(78), px(34)), (px(101), px(27)), (width, px(34)), (width, px(42)),
         (0, px(42))), fill=(43, 57, 78),
    )
    # A restrained cool ridge light separates the farm skyline from the sky.
    draw.line(((0, px(33)), (px(16), px(28)), (px(36), px(34)),
               (px(55), px(27)), (px(78), px(34)), (px(101), px(27)),
               (width, px(34))), fill=(75, 93, 126), width=px(1))
    draw.rectangle((0, px(96), width, height), fill=(16, 30, 37))
    draw.polygon(((0, px(112)), (px(42), px(107)), (px(88), px(112)),
                  (width, px(106)), (width, height), (0, height)), fill=(23, 45, 39))

    # A carved, beveled farm sign makes the matched wordmark the visual anchor.
    left, top, right, bottom = px(3), px(35), px(124), px(94)
    _draw_wavy_panel(draw, (left + px(3), top + px(3), right, bottom),
                     (8, 14, 20), scale, 0.4)
    _draw_wavy_panel(draw, (left, top, right - px(3), bottom - px(3)),
                     (101, 60, 70), scale, 1.3)
    _draw_wavy_panel(draw, (left + px(2), top + px(2), right - px(5), bottom - px(5)),
                     (35, 29, 48), scale, 2.1)
    _draw_wavy_panel(draw, (left + px(5), top + px(5), right - px(8), bottom - px(8)),
                     (22, 48, 45), scale, 3.4)
    draw.point((left + px(7), top + px(7)), fill=(115, 161, 100))
    draw.point((right - px(10), bottom - px(10)), fill=(11, 27, 31))

    return image, scale


def build_animation_frames(width: int, height: int) -> tuple[bytes, ...]:
    """Pre-render a brisk, low-memory farm sign loop at startup."""
    background, scale = _draw_static_sign(width, height)
    frame_count = 52
    frames = []
    wordmark_face = (111, 241, 204)
    for index in range(frame_count):
        frame = background.copy()
        title_bob = round(sin(2 * pi * index / 26) * 2.1 * scale)
        _draw_pixel_text(frame, "POOR LOUIS", round(46 * scale) + title_bob,
                         wordmark_face, frame_index=index, font_size=16)
        _draw_pixel_text(frame, "FARMS", round(70 * scale) + title_bob,
                         wordmark_face, frame_index=index, font_size=16)
        draw = ImageDraw.Draw(frame)
        _draw_pumpkin_vines(draw, width, height, scale, index)
        _draw_twinkling_stars(draw, scale, index)
        _draw_moon_glint(draw, scale, index)
        witch_phase = index / (frame_count - 1)
        witch_x = round((-34 + (width / max(scale, 0.01) + 68) * witch_phase) * scale)
        witch_y = round((8 + sin(index * 2 * pi / 13) * 2.8) * scale)
        _draw_witch_broom(frame, witch_x, witch_y, scale, index)
        _draw_halloween_border(draw, scale, index, frame_count)
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
