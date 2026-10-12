"""Low-load Poor Louis Farms fall sign for a HUB75 RGB matrix."""
from __future__ import annotations

import signal
import time
from functools import lru_cache
from math import cos, pi, sin
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
)
CAT_TAIL_SWAY = (-3, -2, 0, 2, 3, 2, 1, 0, -1, -2, -3, -1, 1)


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

    # Warm stepped bevels add depth without the muddy red cast of a long drop shadow.
    image.paste((49, 39, 58), (5, 5), mask)
    image.paste((92, 68, 65), (4, 4), mask)
    image.paste((139, 91, 67), (3, 3), mask)
    image.paste((190, 123, 59), (2, 2), mask)
    image.paste((239, 164, 67), (1, 1), mask)
    image.paste((255, 239, 188), (-1, -1), mask)
    image.paste(face, (0, 0), mask)


def _draw_witch_broom(image: Image.Image, x: int, y: int, scale: float, frame_index: int) -> None:
    """Draw a tiny witch, fluttering cape, and broom as crisp pixel art."""
    draw = ImageDraw.Draw(image)
    unit = max(1, round(scale))
    point = lambda column, row: (x + column * unit, y + row * unit)
    flutter = (frame_index // 3) % 3

    # Broom bristles and striped bindings.
    draw.polygon(
        tuple(point(*p) for p in ((2, 12), (8, 12), (7, 18), (5, 20), (4, 16), (1, 19), (2, 15), (0, 16))),
        fill=(180, 91, 45), outline=(255, 180, 83),
    )
    draw.line((point(2, 14), point(7, 14)), fill=(246, 151, 58), width=unit)
    draw.line((point(3, 17), point(6, 16)), fill=(116, 56, 41), width=unit)
    draw.line((point(6, 15), point(32, 9)), fill=(105, 57, 47), width=unit * 2)
    draw.line((point(7, 14), point(31, 8)), fill=(226, 152, 76), width=unit)
    draw.line((point(7, 13), point(8, 15)), fill=(255, 210, 111), width=unit)

    # Boots and legs hang behind a fluttering plum cloak.
    draw.line((point(17, 11), point(14, 14), point(12, 16)), fill=(255, 178, 99), width=unit * 2)
    draw.line((point(19, 11), point(18, 14), point(16, 16)), fill=(255, 178, 99), width=unit * 2)
    draw.rectangle((x + 9 * unit, y + (15 - flutter) * unit,
                    x + 14 * unit, y + (17 - flutter) * unit), fill=(68, 31, 91))
    draw.line((point(12, 16 - flutter), point(10, 17 - flutter)), fill=(32, 23, 52), width=unit * 2)
    draw.line((point(16, 16), point(15, 17)), fill=(32, 23, 52), width=unit * 2)
    draw.polygon(
        tuple(point(*p) for p in ((13, 8), (21, 8), (24, 13), (21, 15),
                                   (16, 13), (10, 15), (12, 11))),
        fill=(83, 39, 116), outline=(182, 97, 194),
    )
    draw.line((point(13, 10), point(11, 13 + flutter)), fill=(242, 131, 197), width=unit)
    draw.line((point(19, 10), point(21, 12)), fill=(255, 187, 104), width=unit * 2)

    # Bright hair frames a peach face beneath a tall purple hat.
    draw.rectangle((x + 17 * unit, y + 5 * unit, x + 23 * unit, y + 11 * unit), fill=(235, 117, 77))
    draw.rectangle((x + 18 * unit, y + 6 * unit, x + 22 * unit, y + 10 * unit), fill=(255, 204, 145))
    draw.point(point(22, 8), fill=(58, 37, 72))
    draw.point(point(23, 9), fill=(255, 180, 92))  # pointed nose, facing forward
    draw.polygon(
        tuple(point(*p) for p in ((13, 5), (19, 4), (21, 0), (24, 4),
                                   (29, 6), (24, 7), (15, 7))),
        fill=(47, 32, 83), outline=(151, 94, 191),
    )
    draw.line((point(17, 5), point(25, 5)), fill=(255, 119, 76), width=unit)
    draw.line((point(19, 1), point(22, 2)), fill=(203, 157, 255), width=unit)

    # Three trailing sparks make the flight path feel magical.
    sparkle = (frame_index // 2) % 3
    if sparkle != 0:
        draw.point(point(-2, 9 + sparkle), fill=(118, 239, 227))
        draw.point(point(4, 7 - sparkle), fill=(248, 133, 234))


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
        if phase >= 21:
            continue
        x, y = px(star_x), px(star_y)
        bright, dim = palettes[star_index % len(palettes)]
        color = bright if phase < 9 else dim
        draw.point((x, y), fill=color)
        if phase < 7:
            radius = 2 if phase < 3 and star_index % 3 == 0 else 1
            draw.line((x - radius, y, x + radius, y), fill=bright)
            draw.line((x, y - radius, x, y + radius), fill=bright)
            if star_index % 4 == 0:
                draw.point((x - 1, y - 1), fill=(255, 244, 208))
                draw.point((x + 1, y + 1), fill=(255, 244, 208))


def _draw_pumpkin_vines(
    draw: ImageDraw.ImageDraw, width: int, height: int, scale: float, frame_index: int
) -> None:
    """Draw detailed, animated jack-o'-lanterns among curling, layered vines."""
    px = lambda value: max(1, round(value * scale))
    def p(x: float, y: float) -> tuple[int, int]:
        return px(x), px(y)

    loop_phase = 2 * pi * frame_index / 52
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
        bob = round(sin(phase) * px(1.2))
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
        smile_phase = ((frame_index + pumpkin_index * 11) % 52) / 51
        smile = (1 - cos(2 * pi * smile_phase)) / 2
        smile_depth = round(smile * 4)
        glow = (255, 245, 155) if (frame_index + pumpkin_index * 4) % 13 < 9 else (255, 195, 89)
        blink = (frame_index + pumpkin_index * 19) % 52 in (0, 1)
        if blink:
            draw.line((x + px(6), y + px(7), x + px(10), y + px(7)), fill=glow, width=px(1))
            draw.line((x + px(17), y + px(7), x + px(21), y + px(7)), fill=glow, width=px(1))
        else:
            draw.polygon(((x + px(5), y + px(8)), (x + px(8), y + px(5)),
                          (x + px(11), y + px(8)), (x + px(10), y + px(10))), fill=glow)
            draw.polygon(((x + px(16), y + px(8)), (x + px(19), y + px(5)),
                          (x + px(22), y + px(8)), (x + px(17), y + px(10))), fill=glow)
        draw.point((x + px(13), y + px(9)), fill=(255, 219, 113))
        mouth_left, mouth_right = x + px(7), x + px(21)
        mouth_top = y + px(12)
        if smile_depth == 0:
            draw.line((mouth_left, mouth_top, mouth_right, mouth_top), fill=glow, width=px(1))
        else:
            mouth = (
                (mouth_left, mouth_top), (mouth_right, mouth_top),
                (x + px(19), mouth_top + px(2 + smile_depth // 2)),
                (x + px(15), mouth_top + px(2 + smile_depth)),
                (x + px(11), mouth_top + px(2 + smile_depth)),
                (x + px(8), mouth_top + px(2 + smile_depth // 2)),
            )
            draw.polygon(mouth, fill=(91, 30, 26), outline=glow)
            if smile_depth >= 2:
                draw.rectangle((x + px(10), mouth_top + px(1), x + px(17), mouth_top + px(2)),
                               fill=(255, 229, 164))


def _draw_halloween_border(
    draw: ImageDraw.ImageDraw, scale: float, frame_index: int, frame_count: int
) -> None:
    px = lambda value: round(value * scale)
    left, top, right, bottom = px(2), px(34), px(125), px(95)
    draw.rectangle((left, top, right, bottom), outline=(78, 39, 78), width=px(1))
    draw.rectangle((left + px(1), top + px(1), right - px(1), bottom - px(1)),
                   outline=(159, 62, 37), width=px(1))
    draw.rectangle((left + px(2), top + px(2), right - px(2), bottom - px(2)),
                   outline=(255, 159, 55), width=px(1))

    path = (
        [(x, top) for x in range(left + px(8), right - px(7))]
        + [(right, y) for y in range(top + px(8), bottom - px(7))]
        + [(x, bottom) for x in range(right - px(8), left + px(7), -1)]
        + [(left, y) for y in range(bottom - px(8), top + px(7), -1)]
    )
    if not path:
        return

    # Crawling ember light moves around the frame in a single Halloween fire palette.
    fire_colors = (
        (113, 42, 48), (184, 55, 35), (232, 79, 31),
        (255, 133, 38), (255, 190, 67), (255, 231, 129),
    )
    for position, (x, y) in enumerate(path):
        heat = (position * 3 + frame_index * 3) % 26
        color_index = 0 if heat < 3 else 1 if heat < 7 else 2 if heat < 13 else 3 if heat < 18 else 4 if heat < 23 else 5
        draw.point((x, y), fill=fire_colors[color_index])

    # Short pixel flames lick outward from the rail and travel with the ember stream.
    flame_step = max(1, round(9 * scale))
    path_motion = round(frame_index * len(path) / frame_count)
    corners = ((left, top), (right, top), (right, bottom), (left, bottom))
    for flame_index, start in enumerate(range(0, len(path), flame_step)):
        x, y = path[(start + path_motion) % len(path)]
        if any(abs(x - cx) < px(10) and abs(y - cy) < px(10) for cx, cy in corners):
            continue
        if y == top:
            nx, ny, tx, ty = 0, -1, 1, 0
        elif y == bottom:
            nx, ny, tx, ty = 0, 1, 1, 0
        elif x == left:
            nx, ny, tx, ty = -1, 0, 0, 1
        else:
            nx, ny, tx, ty = 1, 0, 0, 1
        step = max(1, round(scale))
        flicker = (frame_index // 2 + flame_index * 2) % 4
        length = (2 + flicker % 3) * step
        flame = (
            (x - tx * 2 * step, y - ty * 2 * step),
            (x + tx * 2 * step, y + ty * 2 * step),
            (x + tx * step + nx * step, y + ty * step + ny * step),
            (x + nx * length, y + ny * length),
            (x - tx * step + nx * step, y - ty * step + ny * step),
        )
        draw.polygon(flame, fill=(241, 83, 30), outline=(116, 45, 47))
        core_end = max(step, length - step)
        draw.line((x + nx * step, y + ny * step,
                   x + nx * core_end, y + ny * core_end), fill=(255, 204, 83), width=step)
        draw.point((x + nx * length, y + ny * length), fill=(255, 242, 167))

    # Four tiny jack-o'-lantern plaques make the frame unmistakably Halloween themed.
    for pumpkin_index, (x, y) in enumerate(((4, 36), (116, 36), (4, 86), (116, 86))):
        x, y = px(x), px(y)
        glow = (255, 235, 135) if (frame_index // 2 + pumpkin_index * 3) % 13 < 10 else (255, 154, 67)
        draw.rectangle((x + px(1), y + px(2), x + px(7), y + px(6)), fill=(205, 80, 41))
        draw.rectangle((x + px(2), y + px(1), x + px(6), y + px(7)), fill=(240, 119, 45))
        draw.line((x + px(4), y, x + px(5), y + px(1)), fill=(129, 157, 77), width=px(1))
        draw.point((x + px(3), y + px(3)), fill=glow)
        draw.point((x + px(5), y + px(3)), fill=glow)
        draw.line((x + px(3), y + px(5), x + px(5), y + px(5)), fill=(255, 210, 109), width=px(1))


def _draw_detailed_moon(draw: ImageDraw.ImageDraw, scale: float) -> None:
    """Paint a layered crescent with a colored halo, craters, and lit rim."""
    px = lambda value: round(value * scale)
    draw.ellipse((px(87), px(0), px(127), px(40)), outline=(54, 45, 94), width=px(2))
    draw.ellipse((px(90), px(2), px(124), px(36)), outline=(80, 92, 146), width=px(1))
    draw.ellipse((px(93), px(3), px(123), px(33)), fill=(255, 217, 133), outline=(255, 241, 190))
    draw.ellipse((px(103), px(0), px(131), px(27)), fill=(8, 10, 28))
    # Pixel clusters and crater rings are concentrated in the illuminated crescent.
    draw.ellipse((px(96), px(9), px(100), px(13)), fill=(224, 169, 104), outline=(255, 233, 173))
    draw.ellipse((px(98), px(20), px(103), px(24)), fill=(238, 182, 105))
    draw.ellipse((px(101), px(14), px(103), px(16)), fill=(255, 243, 190))
    draw.rectangle((px(95), px(16), px(96), px(18)), fill=(255, 248, 204))
    draw.point((px(99), px(7)), fill=(255, 249, 218))
    draw.point((px(103), px(27)), fill=(250, 199, 116))
    # Cool edge light separates the shadowed rim from the night sky.
    draw.arc((px(96), px(4), px(123), px(33)), 92, 255, fill=(134, 194, 224), width=px(1))


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

    _draw_detailed_moon(draw, scale)

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

    return image, scale


def build_animation_frames(width: int, height: int) -> tuple[bytes, ...]:
    """Pre-render the farm sign and Halloween animation frames at startup."""
    background, scale = _draw_static_sign(width, height)
    frame_count = 104
    frames = []
    wordmark_face = (255, 204, 112)
    for index in range(frame_count):
        frame = background.copy()
        title_bob = round((1 + sin(2 * pi * index / 52)) * scale)
        _draw_pixel_text(frame, "POOR LOUIS", round(46 * scale) + title_bob,
                         wordmark_face, font_size=16)
        _draw_pixel_text(frame, "FARMS", round(70 * scale) + title_bob,
                         wordmark_face, font_size=16)
        draw = ImageDraw.Draw(frame)
        _draw_pumpkin_vines(draw, width, height, scale, index)
        _draw_twinkling_stars(draw, scale, index)
        witch_phase = index / (frame_count - 1)
        witch_x = round((-34 + (width / max(scale, 0.01) + 68) * witch_phase) * scale)
        witch_y = round((8 + sin(index * 2 * pi / 26) * 1.5) * scale)
        _draw_witch_broom(frame, witch_x, witch_y, scale, index)
        _draw_halloween_border(draw, scale, index, frame_count)
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
