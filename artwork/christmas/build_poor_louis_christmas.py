#!/usr/bin/env python3
"""Draw the Poor Louis Farms Christmas loop at its native 128×128 pixels."""
import argparse
from math import pi, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageChops, ImageDraw

from santa_flyby import draw_flyby
from winter_delivery import draw_delivery
from winter_scenery import (
    draw_cabin,
    draw_cabin_lights,
    draw_chimney_smoke,
    draw_moon,
    draw_tree,
    draw_tree_lights,
)


SIZE = 128
FRAME_COUNT = 192
DELAY_MS = 50
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


def draw_title(image, phase):
    for line, (mask, face, y) in enumerate(TITLE):
        x = (SIZE - mask.width) // 2
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


def scene():
    image = Image.new("RGB", (SIZE, SIZE), SKY)
    draw = ImageDraw.Draw(image)
    draw_moon(draw)

    for x, y, w, h in ((1, 81, 17, 24), (17, 86, 15, 21), (62, 84, 18, 23),
                       (72, 88, 14, 21), (121, 86, 14, 20)):
        spruce(draw, x, y, w, h, ("#172546", "#213055", "#172546"))
    draw.polygon(((0, 106), (19, 101), (44, 103), (69, 98), (101, 103), (127, 98),
                  (127, 127), (0, 127)), fill="#6e8eb7")
    draw.polygon(((0, 115), (20, 112), (52, 116), (72, 111), (101, 116), (127, 113),
                  (127, 127), (0, 127)), fill="#8ca5b8")
    draw.line(((0, 116), (20, 113), (38, 115)), fill="#d1e3e8")
    draw.line(((84, 121), (101, 118), (127, 116)), fill="#d1e3e8")
    draw.ellipse((8, 114, 62, 121), fill="#7d9bbe")
    draw.ellipse((85, 115, 114, 121), fill="#7d9bbe")

    draw_cabin(draw)
    draw_tree(draw)
    draw.rectangle((104, 115, 110, 121), fill="#b05054")
    draw.line((107, 115, 107, 121), fill="#ffc98c")
    draw.rectangle((111, 117, 116, 121), fill="#426f89")
    draw.line((113, 117, 113, 121), fill="#d8e3a6")
    draw.ellipse((64, 119, 84, 124), fill="#7288a9")
    return image


rng = Random(42)
STARS = tuple((rng.randrange(4, 124), rng.randrange(4, 35), rng.randrange(8)) for _ in range(34))
FLAKES = tuple((rng.randrange(SIZE), rng.randrange(SIZE), rng.randrange(2), rng.randrange(12))
               for _ in range(28))


def draw_frame(background, index):
    image = background.copy()
    draw = ImageDraw.Draw(image)
    phase = index / FRAME_COUNT
    seconds = index * DELAY_MS / 1000
    # Preserve the original cabin lights' 80 ms beat.
    tick = index * DELAY_MS // 80

    for x, y, offset in STARS:
        if 91 <= x <= 114 and 5 <= y <= 28:
            continue
        shine = (phase * 3 + offset / 8) % 1
        draw.point((x, y), fill="#f5d49c" if shine < 0.22 else "#7189a8")
        if shine < 0.10 and offset % 3 == 0:
            draw.line((x - 2, y, x + 2, y), fill="#94adcb")
            draw.line((x, y - 2, x, y + 2), fill="#f5d49c")

    for x, y, speed, offset in FLAKES:
        drift = round(3 * sin(2 * pi * (phase + offset / 12)))
        px = (x + drift) % SIZE
        py = (y + int((1 + speed) * phase * SIZE)) % SIZE
        if py < 119:
            draw.point((px, py), fill="#d4e5ec" if speed else "#8199b5")

    draw_cabin_lights(draw, phase)
    for offset, x in enumerate(range(13, 48, 5)):
        lamp = (tick + offset * 7) // 10 % 3
        draw.point((x, 103), fill=("#ffb276", "#a8e4cb", "#fb7668")[lamp])
    draw_chimney_smoke(draw, phase)
    draw_tree_lights(draw, phase)
    draw_flyby(draw, seconds)
    draw_delivery(draw, seconds, phase)
    draw_title(image, phase)
    return image


def build(output):
    background = scene()
    frames = [draw_frame(background, index) for index in range(FRAME_COUNT)]
    colors = sorted({color for frame in frames for _, color in frame.getcolors(256)})
    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for color in colors for channel in color])
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(output, format="GIF", save_all=True, append_images=indexed[1:],
                    loop=0, duration=DELAY_MS, disposal=1, optimize=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
