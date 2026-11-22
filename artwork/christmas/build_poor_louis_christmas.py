#!/usr/bin/env python3
"""Draw the Poor Louis Farms Christmas loop at its native 128×128 pixels."""
import argparse
from math import pi, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageChops, ImageDraw

from santa_flyby import draw_flyby, flight_position
from winter_delivery import draw_delivery, draw_presents_under_tree
from winter_scenery import (
    MOON_X,
    MOON_Y,
    MOON_SIZE,
    draw_cabin,
    draw_cabin_lights,
    draw_chimney_smoke,
    draw_moon,
    draw_moon_shimmer,
    draw_snow_glints,
    draw_stylized_snowflakes,
    draw_tree,
    draw_tree_lights,
)
from woodland_scene import draw_woodland_motion, draw_woodland_props


SIZE = 128
DELAY_MS = 50
FRAME_COUNT = 376
LOOP_SECONDS = FRAME_COUNT * DELAY_MS / 1000
FARM_BEAT_SECONDS = 9.6
WOODLAND_X = 144
PAN_START, PAN_END = 7.75, 11.50
FADE_START, FADE_MID = 17.65, 18.25
SKY_RATE, RIDGE_RATE, TREE_RATE = 0.20, 0.39, 0.68
SKY = "#070c1d"
GLYPHS = {
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "I": ("111", "010", "010", "010", "010", "010", "111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
}


def title_mask(text):
    width = sum((len(GLYPHS[letter][0]) * 2 + 2) if letter != " " else 4 for letter in text) - 2
    mask = Image.new("L", (width, 14))
    draw = ImageDraw.Draw(mask)
    x = 0
    for letter in text:
        if letter == " ":
            x += 4
            continue
        for y, row in enumerate(GLYPHS[letter]):
            for dx, bit in enumerate(row):
                if bit == "1":
                    draw.rectangle((x + 2 * dx, 2 * y, x + 2 * dx + 1, 2 * y + 1), fill=255)
        x += len(GLYPHS[letter][0]) * 2 + 2
    return mask


def title_face(mask):
    face = Image.new("RGB", mask.size)
    colors = ("#fff0c7", "#edfad8", "#c6efd2", "#a7dac4", "#8cbdae")
    tones = (0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 4)
    draw = ImageDraw.Draw(face)
    for row, tone in enumerate(tones):
        draw.line((0, row, mask.width - 1, row), fill=colors[tone])
    return face


TITLE = tuple((mask, title_face(mask), y) for mask, y in
              ((title_mask("POOR LOUIS"), 42), (title_mask("FARMS"), 61)))


def draw_title(image, phase, offset_x):
    for line, (mask, face, y) in enumerate(TITLE):
        x = (SIZE - mask.width) // 2 + offset_x
        image.paste("#332444", (x + 3, y + 3), mask)
        image.paste("#915261", (x + 2, y + 2), mask)
        image.paste("#e4ab75", (x + 1, y + 1), mask)
        image.paste(face, (x, y), mask)

        # A narrow diagonal glint crosses the bevel twice per loop.
        sweep = (phase * 2 - line * 0.09) % 1
        if sweep < 0.32:
            center = round(-10 + sweep / 0.32 * (mask.width + 23))
            shine = Image.new("L", mask.size)
            beam = ImageDraw.Draw(shine)
            beam.polygon(((center, 0), (center + 5, 0), (center - 2, 13), (center - 7, 13)), fill=255)
            image.paste("#fff8dc", (x, y), ImageChops.multiply(mask, shine))

    draw = ImageDraw.Draw(image)
    for x, y, offset in ((26, 65, 0.23), (100, 67, 0.70)):
        x += offset_x
        shimmer = (phase - offset) % 1
        if shimmer < 0.08:
            draw.point((x, y), fill="#e4ab75")
            if 0.02 <= shimmer < 0.056:
                draw.line((x - 2, y, x + 2, y), fill="#d6ae81")
                draw.line((x, y - 2, x, y + 2), fill="#fff8dc")


def spruce(draw, x, y, width, height, palette):
    dark, light, trunk = palette
    draw.rectangle((x - 1, y + height - 7, x + 1, y + height + 1), fill=trunk)
    for tier in range(3):
        top = y + tier * height // 5
        bottom = y + (tier + 3) * height // 5 - 3
        tips = max(2, (tier + 2) * width // 8)
        draw.polygon(((x, top), (x - tips, bottom), (x + tips, bottom)), fill=dark)
        draw.polygon(((x, top), (x - tips, bottom), (x, bottom - 2)), fill=light)


def make_panorama():
    sky = Image.new("RGB", (SIZE + round(WOODLAND_X * SKY_RATE), SIZE), SKY)
    draw_moon(ImageDraw.Draw(sky))

    ridge = Image.new("RGBA", (SIZE + round(WOODLAND_X * RIDGE_RATE), SIZE))
    draw = ImageDraw.Draw(ridge)
    draw.polygon(((106, 98), (117, 93), (128, 82), (140, 65), (152, 52),
                  (165, 68), (170, 62), (177, 55), (185, 67), (185, 109),
                  (106, 109)), fill="#293958")
    draw.polygon(((117, 93), (128, 82), (140, 65), (152, 52),
                  (150, 65), (156, 76), (148, 83), (138, 88)),
                 fill="#426187")
    draw.polygon(((140, 65), (152, 52), (158, 61), (156, 60),
                  (154, 62), (151, 60), (147, 65), (145, 63)),
                 fill="#879fbc")
    draw.polygon(((165, 68), (177, 55), (184, 65), (181, 64), (176, 62),
                  (173, 67), (170, 65)), fill="#677d9d")
    draw.line(((143, 72), (150, 66), (155, 72)), fill="#5b729a")

    trees = Image.new("RGBA", (SIZE + round(WOODLAND_X * TREE_RATE), SIZE))
    draw = ImageDraw.Draw(trees)
    for x, y, w, h in ((1, 81, 17, 24), (17, 86, 15, 21), (62, 84, 18, 23),
                       (72, 88, 14, 21), (121, 86, 14, 20)):
        spruce(draw, x, y, w, h, ("#172546", "#213055", "#172546"))
    for x, y, w, h in ((133, 73, 20, 37), (143, 63, 23, 46), (153, 78, 15, 32),
                      (165, 58, 25, 51), (176, 74, 23, 37), (188, 62, 26, 44),
                      (200, 73, 19, 35), (213, 67, 20, 38), (223, 55, 23, 52)):
        spruce(draw, x, y, w, h, ("#172546", "#293958", "#213055"))

    ground = Image.new("RGBA", (SIZE + WOODLAND_X, SIZE))
    draw = ImageDraw.Draw(ground)
    draw.polygon(((0, 106), (19, 101), (44, 103), (69, 98), (101, 103), (127, 98),
                  (147, 96), (161, 100), (181, 96), (208, 101), (235, 96),
                  (255, 99), (272, 91), (272, 127), (0, 127)), fill="#6e8eb7")
    draw.polygon(((0, 115), (20, 112), (52, 116), (72, 111), (101, 116), (127, 113),
                  (148, 111), (170, 115), (194, 112), (218, 116), (243, 112),
                  (263, 115), (272, 110), (272, 127), (0, 127)), fill="#8ca5b8")
    draw.line(((0, 116), (20, 113), (38, 115)), fill="#d1e3e8")
    draw.line(((84, 121), (101, 118), (127, 116)), fill="#d1e3e8")
    draw.ellipse((8, 114, 62, 121), fill="#7d9bbe")
    draw.ellipse((85, 115, 114, 121), fill="#7d9bbe")

    draw_cabin(draw)
    draw_tree(draw)
    draw_presents_under_tree(draw)
    draw.ellipse((64, 119, 84, 124), fill="#7288a9")
    draw.line(((128, 116), (146, 114), (161, 116)), fill="#d1e3e8")
    draw.line(((147, 122), (153, 121), (169, 123)), fill="#c4d3de")
    draw.line(((236, 124), (249, 122), (264, 123)), fill="#d1e3e8")
    woodland = Image.new("RGBA", (SIZE, SIZE))
    draw_woodland_props(woodland)
    ground.alpha_composite(woodland, (WOODLAND_X, 0))
    return sky, ridge, trees, ground


rng = Random(42)
STARS = tuple((rng.randrange(4, 124), rng.randrange(4, 35), rng.randrange(8)) for _ in range(34))
FLAKES = tuple((rng.randrange(SIZE), rng.randrange(SIZE), rng.randrange(2), rng.randrange(12))
               for _ in range(28))
SKY_STARS = STARS + tuple((rng.randrange(SIZE, SIZE + round(WOODLAND_X * SKY_RATE)),
                           rng.randrange(3, 43), rng.randrange(8)) for _ in range(10))


def follow_camera(seconds):
    if seconds <= PAN_START:
        return 0
    if seconds >= PAN_END:
        return WOODLAND_X
    start, end = flight_position(PAN_START), flight_position(PAN_END)
    progress = (flight_position(seconds) - start) / (end - start)
    return round(WOODLAND_X * progress ** 2 * (3 - 2 * progress))


def draw_sky_motion(draw, phase, camera_x):
    # A dim aurora emerges over the clearing as the camera leaves the farm.
    if camera_x > 46:
        drift = round(sin(phase * 2 * pi) * 2)
        faint, bright = ("#172546", "#213055") if camera_x < 93 else ("#23394b", "#365c60")
        points = ((36, 28 + drift), (44, 31 + drift), (55, 30), (66, 25), (80, 26))
        draw.line(tuple((x, y + 2) for x, y in points), fill=faint, width=3)
        draw.line(points, fill=bright)
        for x, y in ((42, 30 + drift), (48, 31 + drift), (58, 29), (66, 25), (75, 26)):
            draw.line((x, y + 1, x, y + 5), fill=faint)
        draw.line(((42, 39), (52, 37), (60, 35), (71, 36)), fill=faint)
    for x, y, offset in SKY_STARS:
        if MOON_X - 3 <= x <= MOON_X + MOON_SIZE + 3 and MOON_Y - 5 <= y <= MOON_Y + MOON_SIZE + 3:
            continue
        shine = (phase * 3 + offset / 8) % 1
        draw.point((x, y), fill="#f5d49c" if shine < 0.22 else "#7189a8")
        if shine < 0.10 and offset % 3 == 0:
            draw.line((x - 2, y, x + 2, y), fill="#94adcb")
            draw.line((x, y - 2, x, y + 2), fill="#f5d49c")
    draw_moon_shimmer(draw, phase)


def draw_flurries(draw, phase):
    for x, y, speed, offset in FLAKES:
        drift = round(3 * sin(2 * pi * (phase + offset / 12)))
        px = (x + drift) % SIZE
        py = (y + int((1 + speed) * phase * SIZE)) % SIZE
        if py < 119:
            draw.point((px, py), fill="#d4e5ec" if speed else "#8199b5")


def draw_farm_motion(draw, seconds, phase):
    # Preserve the original cabin lights' 80 ms beat.
    tick = round(seconds * 1000) // 80
    draw_cabin_lights(draw, phase)
    for offset, x in enumerate(range(13, 48, 5)):
        lamp = (tick + offset * 7) // 10 % 3
        draw.point((x, 103), fill=("#ffb276", "#a8e4cb", "#fb7668")[lamp])
    draw_chimney_smoke(draw, phase)
    draw_tree_lights(draw, phase)
    draw_snow_glints(draw, phase)
    draw_delivery(draw, seconds, phase)


def draw_frame(panorama, seconds):
    camera_x = follow_camera(seconds)
    phase = seconds % FARM_BEAT_SECONDS / FARM_BEAT_SECONDS
    woodland_phase = (seconds - PAN_END) / LOOP_SECONDS % 1

    sky, ridge, trees, ground = panorama
    sky_frame = sky.copy()
    draw_sky_motion(ImageDraw.Draw(sky_frame), phase, camera_x)
    sky_offset = round(camera_x * SKY_RATE)
    image = sky_frame.crop((sky_offset, 0, sky_offset + SIZE, SIZE))
    for layer, rate in ((ridge, RIDGE_RATE), (trees, TREE_RATE), (ground, 1)):
        offset = round(camera_x * rate)
        visible = layer.crop((offset, 0, offset + SIZE, SIZE))
        image.paste(visible, (0, 0), visible)

    if camera_x < SIZE:
        farm = Image.new("RGBA", (SIZE, SIZE))
        draw_farm_motion(ImageDraw.Draw(farm), seconds, phase)
        image.paste(farm, (-camera_x, 0), farm)
    if camera_x + SIZE > WOODLAND_X:
        woodland = Image.new("RGBA", (SIZE, SIZE))
        draw = ImageDraw.Draw(woodland)
        draw_snow_glints(draw, woodland_phase)
        draw_woodland_motion(woodland, woodland_phase, seconds, WOODLAND_X)
        image.paste(woodland, (WOODLAND_X - camera_x, 0), woodland)

    draw = ImageDraw.Draw(image)
    draw_flurries(draw, phase)
    draw_flyby(draw, seconds, camera_x, MOON_X + MOON_SIZE // 2 - sky_offset)
    draw_stylized_snowflakes(draw, phase)
    if camera_x < SIZE:
        draw_title(image, phase, -camera_x)
    return image


def loop_frame(panorama, index):
    seconds = index * DELAY_MS / 1000
    if seconds < FADE_START:
        return draw_frame(panorama, seconds), 1
    if seconds < FADE_MID:
        return draw_frame(panorama, seconds), (FADE_MID - seconds) / (FADE_MID - FADE_START)
    # Ease back into the farm at the loop seam. Its effects resume at time zero.
    return draw_frame(panorama, seconds - LOOP_SECONDS), (seconds - FADE_MID) / (LOOP_SECONDS - FADE_MID)


def build(output):
    panorama = make_panorama()
    frames = [loop_frame(panorama, index) for index in range(FRAME_COUNT)]
    colors = sorted({color for frame, _ in frames for _, color in frame.getcolors(SIZE * SIZE)})
    if len(colors) > 256:
        raise ValueError(f"The Christmas artwork uses {len(colors)} colors; the GIF palette allows 256")
    palette_bytes = [channel for color in colors for channel in color]
    palette = Image.new("P", (1, 1))
    palette.putpalette(palette_bytes)
    indexed = []
    for frame, brightness in frames:
        pixels = frame.quantize(palette=palette, dither=Image.Dither.NONE)
        if brightness < 1:
            # Local palettes give the reset a fade while preserving approved LED hues in both scenes.
            pixels.putpalette([round(channel * brightness) for channel in palette_bytes])
        indexed.append(pixels)
    output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(output, format="GIF", save_all=True, append_images=indexed[1:],
                    loop=0, duration=DELAY_MS, disposal=1, optimize=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
