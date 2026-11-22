"""Draw the moon, cabin, and decorated evergreen for the native Christmas loop."""
from math import pi, sin

from PIL import Image, ImageDraw


# The mouth of the chimney is aligned with the smoke's starting point.
CHIMNEY_X, CHIMNEY_Y = 19, 84
SMOKE_TONES = ("#d9e3e7", "#aec2d2", "#879fbc", "#677d9d", "#485b7f", "#293958")
ORNAMENTS = (
    (98, 86, 0), (102, 91, 1), (94, 96, 2), (103, 98, 0), (98, 101, 3),
    (108, 104, 1), (91, 107, 0), (100, 110, 2), (108, 112, 3),
)
ORNAMENT_COLORS = (
    ("#a84960", "#e47783", "#ffd2ae"),
    ("#a96c50", "#eaae70", "#fff2be"),
    ("#786291", "#ab8aca", "#f1c6ed"),
    ("#378b87", "#6dc9ae", "#ddffe7"),
)
SNOWFLAKE_PATHS = (
    (5, -8, 94, 0.08), (40, -8, 37, 0.68),
    (123, -8, 108, 0.39), (108, 57, 72, 0.86),
)
SNOW_GLINTS = (
    (3, 119), (9, 125), (20, 122), (32, 126), (46, 123), (56, 126), (63, 116),
    (72, 126), (85, 122), (92, 126), (103, 125), (115, 125), (120, 110), (126, 124),
)


def draw_moon(draw):
    left, top = 86, 1
    mask = Image.new("1", (35, 35))
    shape = ImageDraw.Draw(mask)
    shape.ellipse((7, 7, 26, 26), fill=1)
    shape.ellipse((13, 4, 28, 20), fill=0)
    crescent = {(x, y) for y in range(35) for x in range(35) if mask.getpixel((x, y))}
    outer_halo = ("#303955", "#262f4c", "#1d2741", "#151e35", "#0e162a", "#0b1122")
    warm_halo = ("#b08b9f", "#997b9c", "#786995", "#565480", "#41476b") + outer_halo
    cool_halo = ("#9f9dc2", "#818eb8", "#697ba4", "#55668e", "#424f75") + outer_halo
    # The light falls off in fine steps so that the outer edge blends into the sky.
    for y in range(-1, 40):
        for x in range(-8, 42):
            if (x, y) in crescent:
                edge = not all((x + dx, y + dy) in crescent
                               for dx, dy in ((-1, 0), (0, -1), (1, 0), (0, 1)))
                if x <= 9 or y < 11:
                    color = "#fff2c7" if edge else "#ffe3ae"
                elif y >= 23:
                    color = "#c9968d" if edge else "#edbb9a"
                else:
                    color = "#e7ba98" if edge else "#f5d39e"
                draw.point((left + x, top + y), fill=color)
                continue
            distance = min((cx - x) ** 2 + (cy - y) ** 2 for cx, cy in crescent)
            palette = warm_halo if x + y > 19 and x < 17 else cool_halo
            for limit, color in zip((2, 5, 10, 17, 26, 38, 53, 72, 95, 125, 160), palette):
                if distance <= limit:
                    draw.point((left + x, top + y), fill=color)
                    break
    for x, y, color in (
        (11, 12, "#cc9985"), (10, 13, "#d6a98f"), (13, 16, "#d1a08a"),
        (12, 17, "#ffe9b9"), (9, 18, "#d3a08a"), (13, 20, "#bd8e80"),
        (14, 20, "#c69a86"), (14, 21, "#ffeab9"), (17, 23, "#d2a089"),
        (20, 24, "#ffdeb1"), (23, 23, "#bd8e80"),
    ):
        if (x, y) in crescent:
            draw.point((left + x, top + y), fill=color)


def draw_moon_shimmer(draw, phase):
    # A soft highlight follows the underside, with small glints in the nearby light.
    path = ((93, 15), (93, 18), (94, 21), (96, 24), (99, 26),
            (102, 27), (105, 27), (108, 26), (110, 25))
    sweep = (phase * 2 + 0.14) % 1
    if sweep < 0.70:
        index = int(sweep / 0.70 * len(path))
        x, y = path[index]
        draw.point((x, y), fill="#fff4d2")
        if index:
            draw.point(path[index - 1], fill="#ffe3ae")

    for index, (x, y) in enumerate(((91, 11), (89, 20), (98, 30), (110, 29), (114, 21))):
        shimmer = (phase * 2 + index * 0.39) % 1
        if shimmer < 0.30:
            bright = 0.08 < shimmer < 0.18
            draw.point((x, y), fill="#e5d9e8" if bright else "#9f9dc2")
            if bright and index % 2 == 0:
                draw.point((x, y + 1), fill="#818eb8")


def draw_snow_glints(draw, phase):
    for index, (x, y) in enumerate(SNOW_GLINTS):
        pulse = (phase * 3 + index * 0.37) % 1
        if pulse < 0.27:
            draw.point((x, y), fill="#afc1d6")
        if 0.06 < pulse < 0.20:
            draw.line((x - 1, y, x + 1, y), fill="#c4d3de")
            draw.point((x, y), fill="#f7f4e1")
            if index % 3 == 0 and 0.10 < pulse < 0.16:
                draw.point((x, y - 1), fill="#d9e4e5")


def draw_large_snowflakes(draw, phase):
    for center_x, top, bottom, offset in SNOWFLAKE_PATHS:
        age = (phase + offset) % 1
        if not 0.04 < age < 0.94:
            continue
        x = center_x + round(2 * sin(age * 4 * pi))
        y = round(top + (bottom - top) * age)
        color = "#afc1d6" if 0.12 < age < 0.82 else "#879fbc"
        # Six stems and their forks read as a crystalline flake at a distance.
        for pole in (-1, 1):
            draw.line((x, y, x, y + 4 * pole), fill=color)
            for side in (-1, 1):
                draw.line((x, y + 2 * pole, x + side, y + 3 * pole), fill=color)
                draw.line((x, y, x + 4 * side, y + 2 * pole), fill=color)
                draw.point((x + 3 * side, y + 3 * pole), fill=color)
                draw.point((x + 4 * side, y + pole), fill=color)
        draw.point((x, y), fill="#e5d9e8")


def draw_cabin(draw):
    # Two faces and a receding roof ridge keep the cabin legible at 128 pixels.
    draw.polygon(((47, 101), (60, 96), (60, 112), (47, 118)), fill="#815265", outline="#674457")
    draw.line(((48, 106), (59, 101)), fill="#a9666e")
    draw.line(((48, 112), (59, 107)), fill="#a9666e")
    draw.line(((47, 117), (61, 111)), fill="#b28a83")
    draw.polygon(((12, 102), (30, 85), (47, 102), (47, 117), (12, 117)),
                 fill="#b46d6b", outline="#774b58")
    draw.polygon(((13, 102), (30, 87), (46, 102)), fill="#965c69")
    for y in (102, 106, 110, 114):
        draw.line((13, y, 46, y), fill="#a15d62")
        draw.line((13, y + 1, 46, y + 1), fill="#c87f73")
    draw.line((12, 103, 12, 116), fill="#d8937c")
    draw.line((47, 102, 47, 116), fill="#a26468")
    draw.line((11, 117, 47, 117), fill="#d6b2a0")

    roof = ((30, 84), (43, 79), (64, 96), (49, 103))
    draw.polygon(roof, fill="#7593b5", outline="#5b729a")
    draw.polygon(((30, 84), (43, 79), (61, 93), (57, 94), (56, 92),
                  (49, 96), (46, 94), (43, 96)), fill="#bdd4e1")
    draw.line(((34, 88), (46, 83)), fill="#e6edf0")
    draw.line(((47, 100), (61, 94)), fill="#9eb6cc")
    draw.line(((49, 103), (64, 96)), fill="#566486", width=2)

    # Brick stack with staggered mortar and a shaded return.
    draw.polygon(((22, 84), (25, 82), (25, 92), (22, 95)), fill="#8d5660", outline="#6e4b5f")
    draw.rectangle((15, 84, 22, 96), fill="#b97a6d", outline="#815361")
    for y in (87, 90, 93):
        draw.line((16, y, 21, y), fill="#dea592")
        joint = 18 if y % 2 else 20
        draw.line((joint, y - 2, joint, y - 1), fill="#dea592")
        draw.line(((23, y), (24, y - 1)), fill="#b68383")
    draw.polygon(((14, 84), (17, 81), (24, 81), (26, 83), (22, 85), (14, 85)),
                 fill="#b1c2d3", outline="#e1e8df")
    draw.line((17, 83, 22, 83), fill="#655169")

    # Snow wraps the front gable and catches more light on the left rafter.
    draw.line(((8, 103), (30, 84), (50, 103)), fill="#5e5875", width=3)
    draw.line(((8, 101), (30, 83), (50, 101)), fill="#dbe7ec", width=2)
    draw.line(((10, 101), (30, 85)), fill="#f2efdd")
    draw.line(((31, 85), (48, 102)), fill="#aabbd3")

    draw.rectangle((25, 105, 34, 117), fill="#695067", outline="#e0a783")
    draw.rectangle((28, 107, 31, 110), fill="#efbf80")
    draw.point((32, 114), fill="#ffda97")
    draw.line((24, 118, 35, 118), fill="#e4e5dc")
    draw.ellipse((27, 94, 33, 100), outline="#88c093", width=2)
    draw.point((30, 94), fill="#f4827d")


def draw_cabin_lights(draw, phase):
    for offset, x in enumerate((15, 39)):
        glass = "#ffda9f" if sin((phase * 4 + offset / 3) * 2 * pi) > -0.25 else "#dfa374"
        draw.rectangle((x, 106, x + 6, 113), fill=glass, outline="#e8ae88")
        draw.line((x + 3, 107, x + 3, 112), fill="#91606a")
        draw.line((x + 1, 109, x + 5, 109), fill="#91606a")
    draw.polygon(((52, 105), (57, 103), (57, 109), (52, 111)),
                 fill="#d99b77", outline="#e6af87")
    draw.line((54, 105, 54, 109), fill="#905d6a")


def draw_chimney_smoke(draw, phase):
    for offset in range(3):
        age = (phase * 5 + offset / 3) % 1
        x = CHIMNEY_X + round((7 + 2 * sin(2 * pi * phase)) * age)
        y = CHIMNEY_Y - 3 - round(19 * age)
        radius = 1 + int(4 * age)
        height = max(1, (radius + 1) // 2)
        color = SMOKE_TONES[int(age * len(SMOKE_TONES))]
        ring = (x - radius, y - height, x + radius, y + height)
        if age < 0.73:
            draw.ellipse(ring, outline=color)
            if age < 0.25:
                draw.point((x, y), fill="#859ab9")
        else:
            draw.arc(ring, 0, 300, fill=color)


def draw_tree(draw):
    draw.rectangle((97, 108, 101, 118), fill="#8a665f", outline="#694b58")
    for top, bottom, width in ((94, 114, 15), (88, 107, 13), (83, 100, 10), (77, 92, 7)):
        left, right = 99 - width, 99 + width
        draw.polygon(((99, top), (left, bottom - 1), (96, bottom - 2), (right, bottom)),
                     fill="#327b68", outline="#245b56")
        draw.polygon(((99, top + 1), (left + 1, bottom - 2), (98, bottom - 4)),
                     fill="#59a68a")
        draw.line(((left + 1, bottom - 2), (left + 4, bottom - 2), (left + 6, bottom - 3)),
                  fill="#a1c6be")
        draw.line(((98, bottom - 2), (right - 1, bottom - 1)), fill="#499881")
    for swag in (((95, 89), (99, 91), (104, 90)),
                 ((91, 97), (97, 100), (104, 100), (108, 98)),
                 ((87, 107), (94, 110), (103, 111), (111, 108))):
        draw.line(swag, fill="#c6a271")


def draw_tree_lights(draw, phase):
    for index, (x, y, theme) in enumerate(ORNAMENTS):
        shadow, body, glint = ORNAMENT_COLORS[theme]
        shine = (phase * 3 + index * 0.27) % 1
        draw.line((x - 1, y, x + 1, y), fill=body)
        draw.point((x, y + 1), fill=shadow)
        draw.point((x, y - 1), fill=glint if shine < 0.42 else body)
    x, y = 99, 76
    shine = (phase * 4 + 0.1) % 1
    draw.line((x - 2, y, x + 2, y), fill="#ffce88")
    draw.line((x, y - 2, x, y + 2), fill="#ffdf9e")
    draw.point((x, y), fill="#fff6dc")
    if shine < 0.37:
        radius = 4 if 0.09 <= shine < 0.27 else 3
        draw.point((x - radius, y), fill="#ffc681")
        draw.point((x + radius, y), fill="#ffc681")
        draw.point((x, y - radius), fill="#fff2c7")
        draw.point((x + 3, y - 3), fill="#e0d4e2")
