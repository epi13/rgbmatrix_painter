"""A Christmas gathering in a snowy Alaska spruce clearing, drawn at native scale."""
from math import pi, sin

from PIL import Image, ImageDraw

from santa_flyby import HO_PIXELS, SANTA_HAND, flight_pose
from winter_delivery import draw_falling_present, draw_wrapped_present
from winter_scenery import ORNAMENT_COLORS


TREE_X = 66
TREE_SPRITE = ((43, 43, 90, 111), (45, 53), (41, 58))
WOODLAND_DROP_AT = 11.80
WOODLAND_GIFT_COLORS = ("#568d9a", "#3d607f", "#85b7bc", "#ffedad")
HOO_PIXELS = tuple(row + "." + row[4:] for row in HO_PIXELS)
WOODLAND_ORNAMENTS = (
    (65, 57, 1), (67, 65, 0), (62, 71, 3), (74, 73, 2),
    (56, 80, 0), (67, 82, 1), (76, 84, 3), (55, 93, 2),
    (66, 92, 0), (80, 96, 1), (50, 101, 3), (72, 102, 2),
)


def place_sprite(image, paint, bounds, position, size, *args):
    # Keep the existing shaded silhouettes while changing their native pixel scale.
    sprite = Image.new("RGBA", image.size)
    paint(ImageDraw.Draw(sprite), *args)
    image.alpha_composite(sprite.crop(bounds).resize(size, Image.Resampling.NEAREST), position)


def draw_woodland_tree(draw):
    draw.rectangle((TREE_X - 2, 99, TREE_X + 3, 110), fill="#8a665f", outline="#694b58")
    draw.line((TREE_X + 2, 105, TREE_X + 2, 109), fill="#b28a83")
    for top, hem, width in ((77, 106, 22), (66, 95, 17), (56, 82, 12), (48, 69, 8)):
        left, right = TREE_X - width, TREE_X + width
        draw.polygon(
            ((TREE_X, top), (left + 6, hem - 10), (left, hem - 4),
             (left + 4, hem - 3), (left + 8, hem - 4), (TREE_X - 5, hem),
             (TREE_X + 2, hem - 1), (right - 6, hem + 1), (right - 2, hem - 3),
             (right, hem - 3), (right - 5, hem - 8)),
            fill="#29594e",
        )
        draw.polygon(
            ((TREE_X, top), (left + 6, hem - 10), (left + 1, hem - 5),
             (TREE_X - 8, hem - 6), (TREE_X + 1, hem - 3), (TREE_X + 3, hem - 10)),
            fill="#457962",
        )
        draw.polygon(
            ((TREE_X, top + 1), (TREE_X + 3, hem - 10), (TREE_X + 1, hem - 3),
             (right - 2, hem - 4), (right - 6, hem - 9)),
            fill="#619b79",
        )
        draw.line(((left + 1, hem - 5), (left + 8, hem - 6), (TREE_X - 5, hem - 5)),
                  fill="#a9c7ab")
        draw.line(((TREE_X + 5, hem - 10), (right - 6, hem - 7), (right - 3, hem - 5)),
                  fill="#89b89b")

    for garland in (
        ((61, 65), (67, 67), (73, 65)),
        ((55, 77), (62, 80), (70, 81), (79, 79)),
        ((49, 90), (56, 93), (64, 94), (73, 93), (82, 90)),
        ((46, 100), (57, 103), (68, 104), (79, 103), (85, 101)),
    ):
        draw.line(tuple((x, y + 1) for x, y in garland), fill="#795f57")
        draw.line(garland, fill="#c6a271")


def draw_woodland_props(image):
    draw = ImageDraw.Draw(image)
    draw.ellipse((44, 106, 91, 119), fill="#7288a9")
    place_sprite(image, draw_woodland_tree, *TREE_SPRITE)
    # A snowy bough reaches in from the right for the owl.
    draw.line(((127, 77), (118, 79), (106, 79)), fill="#8a665f", width=3)
    draw.line(((127, 76), (118, 78), (108, 78)), fill="#9eb6cc")
    draw.line(((123, 79), (119, 83), (115, 83)), fill="#619b79")

    draw_wrapped_present(draw, 63, 117, 6, 6, ("#ad535b", "#783e54", "#e18881", "#ffc98c"))
    draw_wrapped_present(draw, 71, 119, 6, 5, ("#568d9a", "#3d607f", "#85b7bc", "#d8e3a6"))
    draw.ellipse((7, 112, 42, 121), fill="#7288a9")
    draw.ellipse((41, 117, 61, 124), fill="#7d9bbe")
    draw.ellipse((91, 113, 125, 123), fill="#7288a9")


def draw_woodland_lights(draw, phase):
    for index, (x, y, theme) in enumerate(WOODLAND_ORNAMENTS):
        shade, body, sparkle = ORNAMENT_COLORS[theme]
        pulse = (phase * 6 + index * 0.31) % 1
        draw.line((x - 1, y, x + 1, y), fill=body)
        draw.point((x, y + 1), fill=shade)
        draw.point((x, y - 1), fill=sparkle if pulse < 0.4 else body)
    draw.line((TREE_X - 2, 48, TREE_X + 2, 48), fill="#ffce88")
    draw.line((TREE_X, 46, TREE_X, 50), fill="#fff6dc")
    star = phase * 5 % 1
    if star < 0.34:
        reach = 4 if 0.09 <= star <= 0.25 else 3
        draw.point((TREE_X - reach, 48), fill="#ffc681")
        draw.point((TREE_X + reach, 48), fill="#ffc681")
        draw.point((TREE_X, 48 - reach), fill="#fff2c7")
        draw.point((TREE_X + 3, 45), fill="#e0d4e2")


def draw_moose(draw, phase, step):
    """A scarfed moose with broad antlers, looking up and nodding."""
    head_lift = round((1 + sin(phase * 8 * pi)) * 0.7)
    # Legs on the far side sit a little higher against the snow.
    draw.polygon(((13, 101), (17, 102), (15, 113), (11, 113)), fill="#70475a")
    draw.polygon(((30, 98), (34, 98), (34, 111), (31, 112)), fill="#70475a")
    draw.polygon(
        ((8, 97), (10, 94), (16, 92), (24, 92), (27, 87), (33, 86),
         (37, 90), (35, 101), (30, 106), (15, 106), (9, 102)),
        fill="#a9755b", outline="#aa826e",
    )
    draw.polygon(((11, 97), (17, 94), (25, 94), (30, 89), (33, 89), (31, 98),
                  (23, 101), (14, 100)), fill="#d6a478")
    draw.line(((12, 103), (19, 105), (30, 103)), fill="#87646e")
    draw.line(((10, 95), (7, 96), (6, 94 + int(phase * 19) % 2)), fill="#aa826e")
    draw.polygon(((15, 103), (20, 103), (20, 110), (18 + step, 117), (14 + step, 117)),
                 fill="#a9755b", outline="#aa826e")
    draw.polygon(((31, 101), (35, 100), (36 - step, 115), (32 - step, 115)),
                 fill="#a9755b", outline="#aa826e")
    draw.line((14 + step, 117, 18 + step, 117), fill="#514b42")
    draw.line((32 - step, 115, 36 - step, 115), fill="#514b42")

    def head(points):
        return tuple((x, y - head_lift) for x, y in points)

    # Broad, fingered antlers distinguish the moose from the flying reindeer.
    draw.polygon(head(((36, 85), (36, 76), (38, 72), (37, 68), (40, 65),
                       (41, 61), (43, 61), (44, 68), (46, 64), (48, 65),
                       (48, 71), (44, 74), (41, 75), (39, 81))), fill="#aa826e")
    draw.polygon(head(((34, 84), (32, 75), (27, 73), (23, 70), (21, 64),
                       (23, 62), (26, 67), (26, 61), (28, 59), (30, 61),
                       (30, 66), (33, 63), (35, 65), (34, 71), (37, 76),
                       (37, 84))), fill="#d4ab79", outline="#aa826e")
    draw.line(head(((24, 69), (30, 71), (33, 69))), fill="#f1c595")
    draw.polygon(head(((31, 90), (32, 82), (30, 78), (34, 79), (37, 82),
                       (41, 81), (45, 84), (47, 85), (47, 89),
                       (43, 91), (37, 89), (34, 93))),
                 fill="#a9755b", outline="#aa826e")
    draw.polygon(head(((35, 83), (40, 82), (44, 85), (43, 87), (37, 86))), fill="#d6a478")
    draw.line(head(((43, 88), (46, 88))), fill="#70475a")
    draw.point((40, 84 - head_lift), fill="#33334a")
    draw.line(((30, 88), (34, 91), (38, 91)), fill="#bb5372", width=3)
    draw.line(((35, 92), (35, 97), (37, 99)), fill="#d97282", width=2)
    draw.point((37, 99), fill="#ffc681")


def draw_hare(draw):
    y = 119
    fur, shade, edge = "#f7f4e1", "#a7bfd4", "#53658e"
    draw.ellipse((45, y - 11, 56, y - 1), fill=shade, outline=edge)
    draw.ellipse((49, y - 11, 56, y - 3), fill=fur)
    draw.ellipse((42, y - 7, 47, y - 3), fill=fur, outline=edge)
    draw.line((50, y - 1, 58, y - 1), fill=shade)
    draw.ellipse((49, y - 20, 52, y - 11), fill=shade, outline=edge)
    draw.ellipse((53, y - 22, 56, y - 11), fill=fur, outline=edge)
    draw.line((55, y - 20, 55, y - 15), fill="#d97282")
    draw.ellipse((49, y - 14, 58, y - 6), fill=fur, outline=edge)
    draw.point((55, y - 11), fill="#33334a")
    draw.point((58, y - 9), fill="#bc6687")
    draw.line((49, y - 6, 56, y - 6), fill="#399782", width=2)
    draw.point((51, y - 5), fill="#6dc9ae")
    draw.line((57, y - 5, 58, y - 5), fill=shade)


def draw_fox(draw, seconds):
    excited = 11.4 <= seconds <= 14.4
    tail_y = 105 + round((4 if excited else 2) * sin(seconds * (8 if excited else 4)))
    draw.polygon(((105, 111), (116, 104), (121, tail_y - 5), (125, tail_y - 5),
                  (127, tail_y - 2), (125, tail_y + 4), (119, 113), (113, 115)),
                 fill="#b97a6d", outline="#aa826e")
    draw.polygon(((120, tail_y - 3), (123, tail_y - 5), (125, tail_y - 5),
                  (126, tail_y - 2), (124, tail_y + 3)), fill="#f7f4e1")
    draw.ellipse((99, 98, 116, 115), fill="#b46d6b", outline="#a9666e")
    draw.ellipse((103, 100, 113, 109), fill="#d8937c")
    draw.polygon(((103, 101), (107, 104), (105, 111), (99, 111), (96, 107)), fill="#f7f4e1")
    draw.line((102, 113, 99, 116), fill="#514b42", width=2)
    draw.polygon(((89, 101), (94, 97), (94, 90), (98, 93), (102, 90),
                  (104, 96), (106, 100), (101, 106), (94, 104)),
                 fill="#d8937c", outline="#a9666e")
    draw.point((95, 92), fill="#70475a")
    draw.point((102, 93), fill="#70475a")
    draw.polygon(((89, 101), (95, 100), (100, 102), (99, 105), (94, 104)), fill="#f7f4e1")
    draw.point((89, 101), fill="#33334a")
    draw.line((96, 97, 97, 97), fill="#33334a")


def hop_height(seconds, start, duration, height):
    progress = (seconds - start) / duration
    return round(height * sin(pi * progress)) if 0 < progress < 1 else 0


def draw_calf(draw, seconds):
    # Big ears, a lighter coat and long knees read as a calf without antlers.
    lift = hop_height(seconds, 12.7, 0.75, 2)
    draw.line(((24, 117 - lift), (23, 123 - lift), (26, 123 - lift)), fill="#87646e")
    draw.line(((32, 117 - lift), (33, 123 - lift), (35, 123 - lift)), fill="#87646e")
    draw.ellipse((21, 112 - lift, 35, 120 - lift), fill="#a9755b", outline="#aa826e")
    draw.polygon(((31, 113 - lift), (31, 109 - lift), (28, 106 - lift), (32, 106 - lift),
                  (34, 109 - lift), (37, 106 - lift), (37, 110 - lift),
                  (40, 112 - lift), (39, 114 - lift), (34, 115 - lift)),
                 fill="#d6a478", outline="#aa826e")
    draw.point((35, 110 - lift), fill="#33334a")


def draw_leveret(draw, seconds):
    y = 123 - hop_height(seconds, 12.65, 0.9, 5) - hop_height(seconds, 14.4, 0.6, 3)
    draw.ellipse((39, y - 6, 47, y), fill="#a7bfd4", outline="#53658e")
    draw.line((40, y - 5, 40, y - 10), fill="#f7f4e1")
    draw.line((43, y - 5, 43, y - 11), fill="#f7f4e1")
    draw.ellipse((40, y - 7, 47, y - 3), fill="#f7f4e1")
    draw.point((45, y - 5), fill="#33334a")
    draw.point((39, y - 2), fill="#f7f4e1")


def draw_fox_kit(draw, seconds):
    tail_y = 116 + round(2 * sin(seconds * 8 + 1))
    draw.line(((115, 120), (121, 119), (125, tail_y)), fill="#b97a6d", width=3)
    draw.point((125, tail_y), fill="#f7f4e1")
    draw.ellipse((110, 114, 120, 122), fill="#b46d6b")
    draw.polygon(((106, 116), (109, 113), (109, 109), (112, 111), (115, 109),
                  (117, 115), (114, 119), (110, 118)), fill="#d8937c")
    draw.line(((106, 116), (110, 118), (113, 118)), fill="#f7f4e1")
    draw.point((110, 114), fill="#33334a")
    draw.point((106, 116), fill="#33334a")


def draw_owl_family(draw, seconds):
    for x, base, width in ((107, 78, 11), (119, 79, 8)):
        chick = width == 8
        top = base - (9 if chick else 13)
        draw.ellipse((x, top + 2, x + width, base), fill="#a9755b", outline="#70475a")
        draw.line((x + 2, top + 1, x + 2, top - 1), fill="#aa826e")
        draw.line((x + width - 2, top + 1, x + width - 2, top - 1), fill="#aa826e")
        look_up = 11.25 < seconds < 15.1
        blink = (seconds + (0.25 if chick else 0)) % 1.85 < 0.13
        for eye in (x + 3, x + width - 2):
            y = top + 4
            if blink:
                draw.line((eye - 1, y, eye + 1, y), fill="#514b42")
            else:
                draw.ellipse((eye - 1, y - 2, eye + 1, y + 1), fill="#f7f4e1")
                draw.point((eye - int(look_up), y - int(look_up)), fill="#33334a")
        beak_x = x + width // 2
        draw.point((beak_x, top + 6), fill="#ffce88")
        draw.line((beak_x - 2, base, beak_x + 2, base), fill="#d4ab79")

    # Three calls next to the branch, distinct from Santa's moving HO trail.
    for start, x, y in ((11.85, 101, 56), (12.75, 103, 54), (13.65, 105, 55)):
        age = seconds - start
        if 0 <= age < 0.80:
            ink = "#fff2c7" if age < 0.40 else "#a7bfd4" if age < 0.62 else "#53658e"
            for dy, row in enumerate(HOO_PIXELS):
                for dx, pixel in enumerate(row):
                    if pixel == "#":
                        draw.point((x + dx, y + dy - round(age * 3)), fill=ink)


def draw_hung_ornament(draw, x, y, color):
    draw.point((x, y - 1), fill="#d4ab79")
    draw.line((x - 1, y, x + 1, y), fill=color)
    draw.point((x, y + 1), fill=color)


def draw_woodland_motion(image, phase, seconds, world_x):
    place_sprite(image, draw_woodland_lights, *TREE_SPRITE, phase)
    forward = hop_height(seconds, 11.45, 1.7, 9)
    step = round(2 * sin(seconds * 18)) if forward else 0
    place_sprite(image, draw_moose, (5, 57, 49, 118), (5 + forward, 70), (33, 47), phase, step)
    leap = hop_height(seconds, 12.0, 1.35, 10)
    place_sprite(image, draw_hare, (42, 96, 60, 120), (46 + leap // 3, 100 - leap), (15, 20))
    place_sprite(image, draw_fox, (88, 89, 128, 118), (88, 97), (24, 18), seconds)

    draw = ImageDraw.Draw(image)
    draw_calf(draw, seconds)
    draw_leveret(draw, seconds)
    draw_fox_kit(draw, seconds)
    draw_owl_family(draw, seconds)

    # The moose leans in with a berry ornament. The hare lifts a gold one in its leap.
    reach = max(0, min(1, (seconds - 11.82) / 0.50))
    draw_hung_ornament(draw, round((35 + forward) * (1 - reach) + 50 * reach), 93, "#e47783")
    if seconds < 12.67:
        draw_hung_ornament(draw, 60 + leap // 3, 113 - leap, "#ffce88")
    else:
        draw_hung_ornament(draw, 63, 103, "#ffce88")
    for at, x, y in ((12.32, 50, 93), (12.67, 63, 103)):
        if 0 <= seconds - at < 0.23:
            draw.point((x + 2, y - 2), fill="#fff2c7")
            draw.point((x, y), fill="#fff6dc")

    sleigh_x, sleigh_y = flight_pose(WOODLAND_DROP_AT)
    launch = (sleigh_x - world_x + SANTA_HAND[0], sleigh_y + SANTA_HAND[1] + 2)
    draw_falling_present(draw, seconds - WOODLAND_DROP_AT, 1.28, launch, (81, 115), WOODLAND_GIFT_COLORS)
