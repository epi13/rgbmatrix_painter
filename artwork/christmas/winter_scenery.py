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
    (5, -8, 101, 0.05), (40, -8, 45, 0.68),
    (122, -5, 103, 0.37), (108, 53, 73, 0.86),
)
FLAKE_SHAPE = ("..#..", "#.#.#", ".###.", "#.#.#", "..#..")
FLAKE_COLORS = (
    ("#344659", "#566b84", "#8b9fb2"),
    ("#444658", "#6b6984", "#a49ab4"),
    ("#394c52", "#5e7980", "#94b0b6"),
)
SNOW_GLINTS = (
    (3, 119), (5, 108), (9, 125), (20, 122), (32, 126), (46, 123), (56, 126), (56, 118),
    (63, 116), (67, 125), (73, 126), (78, 125), (85, 122), (92, 126), (92, 117),
    (100, 125), (109, 126), (115, 125), (118, 113), (122, 106), (126, 111), (126, 124),
)
MOON_X, MOON_Y = 94, 10
MOON_SIZE = 17


def make_crescent():
    mask = Image.new("1", (MOON_SIZE, MOON_SIZE))
    shape = ImageDraw.Draw(mask)
    shape.ellipse((0, 0, 16, 16), fill=1)
    shape.ellipse((5, -3, 18, 11), fill=0)
    return {(x, y) for y in range(MOON_SIZE) for x in range(MOON_SIZE) if mask.getpixel((x, y))}


MOON_PIXELS = make_crescent()


def draw_moon(draw):
    # Neutral luminance steps prevent the LED halo from reading as saturated blue.
    falloff = ((1, 106), (4, 86), (9, 70), (15, 56), (24, 45),
               (36, 36), (49, 28), (64, 22), (81, 17), (100, 13))
    for y in range(-10, MOON_SIZE + 10):
        for x in range(-10, MOON_SIZE + 10):
            position = (MOON_X + x, MOON_Y + y)
            if (x, y) in MOON_PIXELS:
                edge = not all((x + dx, y + dy) in MOON_PIXELS
                               for dx, dy in ((-1, 0), (0, -1), (1, 0), (0, 1)))
                if x <= 2 or y <= 3:
                    color = "#e9e8e3" if edge else "#dbdad6"
                elif y >= 14:
                    color = "#afadb0" if edge else "#c5c3c4"
                else:
                    color = "#bfbdbe" if edge else "#d6d4d2"
                draw.point(position, fill=color)
                continue
            distance = min((cx - x) ** 2 + (cy - y) ** 2 for cx, cy in MOON_PIXELS)
            for limit, value in falloff:
                if distance <= limit:
                    draw.point(position, fill=(value, value, value))
                    break
    # Crater pits and their lit lips stay inside the crescent.
    for x, y, color in ((2, 6, "#b9b7ba"), (3, 7, "#e5e4df"), (2, 10, "#b9b7ba"),
                        (4, 11, "#a6a5a9"), (5, 11, "#b9b7ba"), (5, 12, "#e5e4df"),
                        (8, 13, "#b9b7ba"), (9, 13, "#a6a5a9"), (9, 14, "#e5e4df"),
                        (12, 12, "#b9b7ba"), (12, 14, "#e5e4df")):
        if (x, y) in MOON_PIXELS:
            draw.point((MOON_X + x, MOON_Y + y), fill=color)


def draw_moon_shimmer(draw, phase):
    # Use the same diagonal sweep as the lettering, clipped to the moon's face.
    sweep = (phase * 2 + 0.18) % 1
    if sweep >= 0.35:
        return
    center = -3 + sweep / 0.35 * 30
    for x, y in MOON_PIXELS:
        distance = abs(x + y * 0.45 - center)
        if distance < 1.45:
            color = "#f9f7ee" if distance < 0.60 else "#eceae5"
            draw.point((MOON_X + x, MOON_Y + y), fill=color)


def draw_snow_glints(draw, phase):
    for index, (x, y) in enumerate(SNOW_GLINTS):
        pulse = (phase * 4 + index * 0.37) % 1
        if pulse < 0.32:
            draw.point((x, y), fill="#afc1d6")
        if 0.06 < pulse < 0.23:
            draw.line((x - 1, y, x + 1, y), fill="#c4d3de")
            draw.point((x, y), fill="#f7f4e1" if index % 3 else "#fff2c7")
            if index % 2 == 0 and 0.10 < pulse < 0.18:
                draw.point((x, y - 1), fill="#d9e4e5")
                draw.point((x, y + 1), fill="#afc1d6")


def draw_stylized_snowflakes(draw, phase):
    for index, (center_x, top, bottom, offset) in enumerate(SNOWFLAKE_PATHS):
        cycle = phase * 2 + offset
        age = cycle % 1
        if not 0.10 < age < 0.73:
            continue
        x = center_x + round(2 * sin(age * 4 * pi))
        y = round(top + (bottom - top) * age)
        # Briefly reach full brightness, then step down before leaving the path.
        visibility = min(1, (age - 0.10) * 8, (0.73 - age) * 6)
        tint = (index + int(cycle) % 2 + int(age > 0.35)) % len(FLAKE_COLORS)
        colors = FLAKE_COLORS[tint]
        for row, shape in enumerate(FLAKE_SHAPE):
            for col, pixel in enumerate(shape):
                if pixel == "#":
                    center = col == row == 2
                    step = min(2, int(visibility * (3 if center else 2.2)))
                    draw.point((x + col - 2, y + row - 2), fill=colors[step])


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
    draw.line((100, 112, 100, 117), fill="#b28a83")
    for top, bottom, width in ((94, 114, 15), (88, 107, 13), (83, 100, 10), (77, 92, 7)):
        left, right = 99 - width, 99 + width
        ridge = 100 + width // 5
        # Build each bough as sloping lit faces with a scalloped, shaded underside.
        draw.polygon(((99, top), (left, bottom - 2), (left + 3, bottom - 1),
                      (95, bottom - 1), (98, bottom + 1), (ridge + 1, bottom),
                      (right - 2, bottom - 1), (right, bottom - 2)), fill="#29594e")
        draw.polygon(((99, top), (left + 1, bottom - 2), (94, bottom - 3),
                      (ridge, bottom - 3)), fill="#457962")
        draw.polygon(((99, top), (ridge, bottom - 3), (right - 1, bottom - 2),
                      (right - 3, bottom - 5)), fill="#619b79")
        draw.line(((99, top + 2), (ridge - 1, bottom - 5), (ridge + 3, bottom - 4)),
                  fill="#89b89b")
        draw.line(((left + 2, bottom - 2), (left + 5, bottom - 3)), fill="#81a991")
        draw.line(((right - 4, bottom - 4), (right - 2, bottom - 3),
                   (right - 1, bottom - 3)), fill="#a9c7ab")
    for swag in (((95, 89), (99, 91), (104, 90)),
                 ((91, 97), (97, 100), (104, 100), (108, 98)),
                 ((87, 107), (94, 110), (103, 111), (111, 108))):
        draw.line(tuple((x, y + 1) for x, y in swag), fill="#795f57")
        draw.line(swag, fill="#c6a271")


def draw_tree_lights(draw, phase):
    for index, (x, y, theme) in enumerate(ORNAMENTS):
        shadow, body, glint = ORNAMENT_COLORS[theme]
        shine = (phase * 3 + index * 0.27) % 1
        draw.line((x - 1, y, x + 1, y), fill=body)
        draw.line((x, y + 1, x + 1, y + 1), fill=shadow)
        draw.point((x, y - 1), fill=glint if shine < 0.42 else body)
        if shine < 0.23:
            draw.point((x + 1, y), fill=glint)
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
