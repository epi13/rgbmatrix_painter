#!/usr/bin/env python3
"""Draw the Poor Louis Farms Christmas loop at its native 128×128 pixels."""
import argparse
from math import pi, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw


SIZE = 128
FRAME_COUNT = 120
DELAY_MS = 80
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
TREE_LIGHTS = (
    (99, 83), (94, 91), (105, 92), (99, 97), (91, 101), (109, 101),
    (101, 106), (88, 110), (110, 111), (96, 113),
)


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


TITLE = tuple((title_mask(line), y) for line, y in (("POOR LOUIS", 39), ("FARMS", 59)))


def draw_title(image):
    for mask, y in TITLE:
        x = (SIZE - mask.width) // 2
        image.paste("#23182e", (x + 2, y + 3), mask)
        image.paste("#754151", (x + 1, y + 2), mask)
        image.paste("#b67a63", (x + 1, y + 1), mask)
        image.paste("#c2e9d2", (x, y), mask)
        image.paste("#fff0c7", (x, y), mask.crop((0, 0, mask.width, 5)))


def spruce(draw, x, y, width, height, palette, snow=None):
    dark, light, trunk = palette
    draw.rectangle((x - 1, y + height - 7, x + 1, y + height + 1), fill=trunk)
    for tier in range(3):
        top = y + tier * height // 5
        bottom = y + (tier + 3) * height // 5 - 3
        tips = max(2, (tier + 2) * width // 8)
        draw.polygon(((x, top), (x - tips, bottom), (x + tips, bottom)), fill=dark)
        draw.polygon(((x, top), (x - tips, bottom), (x, bottom - 2)), fill=light)
        if snow:
            draw.line((x, top + 2, x - tips + 1, bottom, x - tips + 4, bottom),
                      fill=snow)


def scene():
    image = Image.new("RGB", (SIZE, SIZE), SKY)
    draw = ImageDraw.Draw(image)
    draw.ellipse((93, 8, 112, 27), fill="#eac58f")
    draw.arc((93, 8, 112, 27), 60, 260, fill="#fff0c7")
    draw.ellipse((99, 5, 114, 21), fill=SKY)
    draw.point((96, 20), fill="#c6997b")

    for x, y, w, h in ((1, 81, 17, 24), (17, 86, 15, 21), (62, 84, 18, 23),
                       (72, 88, 14, 21), (121, 86, 14, 20)):
        spruce(draw, x, y, w, h, ("#172546", "#213055", "#172546"))
    draw.polygon(((0, 106), (19, 101), (44, 103), (69, 98), (101, 103), (127, 98),
                  (127, 127), (0, 127)), fill="#6e8eb7")
    draw.polygon(((0, 115), (20, 112), (52, 116), (72, 111), (101, 116), (127, 113),
                  (127, 127), (0, 127)), fill="#b1c9dc")
    draw.line(((0, 116), (20, 113), (38, 115)), fill="#d1e3e8")
    draw.line(((84, 121), (101, 118), (127, 116)), fill="#d1e3e8")
    draw.ellipse((8, 114, 62, 121), fill="#7d9bbe")
    draw.ellipse((85, 115, 114, 121), fill="#7d9bbe")

    # The little farm stand has a snow-covered roof, cedar planks and a wreath.
    draw.rectangle((45, 82, 50, 98), fill="#624051")
    draw.line((45, 82, 50, 82), fill="#b1c9dc")
    draw.rectangle((14, 98, 54, 117), fill="#8d454c", outline="#502837")
    for x in range(17, 54, 4):
        draw.line((x, 104, x, 116), fill="#a85152")
    draw.polygon(((8, 102), (33, 82), (59, 102)), fill="#3d2941")
    draw.line(((9, 100), (33, 81), (58, 100)), fill="#b1c9dc", width=3)
    draw.line(((9, 98), (33, 80), (58, 98)), fill="#e1e8df", width=2)
    draw.rectangle((29, 106, 38, 117), fill="#432b38", outline="#593440")
    draw.rectangle((32, 108, 35, 111), fill="#f4c47e")
    draw.point((36, 114), fill="#f4c47e")
    draw.ellipse((30, 94, 36, 100), outline="#69a878")
    draw.point((33, 94), fill="#fb7668")
    draw.line((29, 118, 39, 118), fill="#e1e8df")

    # Evergreen, small wrapped presents, and a round snowman.
    spruce(draw, 99, 77, 30, 40, ("#164d48", "#347961", "#79564e"), "#a1c6c1")
    draw.rectangle((104, 115, 110, 121), fill="#b05054")
    draw.line((107, 115, 107, 121), fill="#ffc98c")
    draw.rectangle((111, 117, 116, 121), fill="#426f89")
    draw.line((113, 117, 113, 121), fill="#d8e3a6")
    draw.ellipse((66, 118, 82, 122), fill="#7d9bbe")
    draw.ellipse((68, 109, 80, 120), fill="#e1e8df")
    draw.arc((68, 109, 80, 120), 0, 145, fill="#a0b9cd", width=2)
    draw.ellipse((70, 101, 78, 110), fill="#e1e8df")
    draw.rectangle((71, 99, 77, 102), fill="#32304a")
    draw.line((69, 103, 79, 103), fill="#32304a")
    draw.point((72, 105), fill="#32304a")
    draw.point((76, 105), fill="#32304a")
    draw.line((74, 107, 76, 107), fill="#d68156")
    draw.line((70, 110, 78, 110), fill="#b05054", width=2)
    draw.point((74, 114), fill="#32304a")
    draw.point((74, 117), fill="#32304a")
    return image


rng = Random(42)
STARS = tuple((rng.randrange(4, 124), rng.randrange(4, 35), rng.randrange(8)) for _ in range(34))
FLAKES = tuple((rng.randrange(SIZE), rng.randrange(SIZE), rng.randrange(2), rng.randrange(12))
               for _ in range(28))


def draw_frame(background, index):
    image = background.copy()
    draw = ImageDraw.Draw(image)
    phase = index / FRAME_COUNT

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

    # Small window and tree lights take turns glowing through the snowfall.
    for offset, x in enumerate((20, 44)):
        bright = sin((phase * 4 + offset / 3) * 2 * pi) > -0.25
        draw.rectangle((x, 107, x + 4, 112), fill="#ffd098" if bright else "#d49271",
                       outline="#603944")
        draw.line((x + 2, 108, x + 2, 111), fill="#a55e55")
    for offset, x in enumerate(range(14, 54, 5)):
        lamp = (index + offset * 7) // 10 % 3
        draw.point((x, 102), fill=("#ffb276", "#a8e4cb", "#fb7668")[lamp])
    for offset, (x, y) in enumerate(TREE_LIGHTS):
        palette = ("#ffc98c", "#fa8c81", "#b6e7db")
        lamp = (index + offset * 7) // 10 % 4
        draw.point((x, y), fill=palette[offset % 3] if lamp != 0 else "#739985")
    draw.line((97, 78, 101, 78), fill="#ffc98c")
    draw.line((99, 75, 99, 80), fill="#fff0c7")

    for offset in range(3):
        rise = (index + offset * 10) % 30
        if rise < 24:
            draw.point((48 + rise // 6, 80 - rise // 4), fill="#8199b5" if rise < 12 else "#415471")
    draw.line((77, 111, 81, 112, 83, 111 + (index // 10) % 3), fill="#b05054")
    draw_title(image)
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
