"""A Christmas gathering in a snowy Alaska spruce clearing, drawn at native scale."""
from math import pi, sin

from winter_delivery import draw_wrapped_present
from winter_scenery import ORNAMENT_COLORS


TREE_X = 66
WOODLAND_ORNAMENTS = (
    (65, 57, 1), (67, 65, 0), (62, 71, 3), (74, 73, 2),
    (56, 80, 0), (67, 82, 1), (76, 84, 3), (55, 93, 2),
    (66, 92, 0), (80, 96, 1), (50, 101, 3), (72, 102, 2),
)


def draw_woodland_props(draw):
    """Paint the decorated spruce and its foreground props at the woodland stop."""
    draw.ellipse((40, 104, 98, 119), fill="#7288a9")
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

    # A snowy bough reaches in from the right for the owl.
    draw.line(((127, 77), (118, 79), (106, 79)), fill="#8a665f", width=3)
    draw.line(((127, 76), (118, 78), (108, 78)), fill="#9eb6cc")
    draw.line(((123, 79), (119, 83), (115, 83)), fill="#619b79")

    draw_wrapped_present(draw, 63, 117, 6, 6, ("#ad535b", "#783e54", "#e18881", "#ffc98c"))
    draw_wrapped_present(draw, 71, 119, 6, 5, ("#568d9a", "#3d607f", "#85b7bc", "#d8e3a6"))
    draw_wrapped_present(draw, 79, 115, 5, 6, ("#ca788e", "#84546d", "#eba6a4", "#ffedad"))
    draw.ellipse((7, 112, 46, 119), fill="#7288a9")
    draw.ellipse((42, 117, 61, 122), fill="#7d9bbe")
    draw.ellipse((89, 112, 124, 120), fill="#7288a9")


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


def draw_moose(draw, phase):
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
    draw.polygon(((15, 103), (20, 103), (20, 110), (18, 117), (14, 117)),
                 fill="#a9755b", outline="#aa826e")
    draw.polygon(((31, 101), (35, 100), (36, 115), (32, 115)),
                 fill="#a9755b", outline="#aa826e")
    draw.line((14, 117, 18, 117), fill="#514b42")
    draw.line((32, 115, 36, 115), fill="#514b42")

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


def draw_hare(draw, phase):
    hop = phase * 5 % 1
    rise = round(4 * sin(pi * hop / 0.32)) if hop < 0.32 else 0
    y = 119 - rise
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
    # A little golden ornament in its front paws.
    draw.line((57, y - 5, 59, y - 5), fill=shade)
    draw.point((60, y - 6), fill="#ffce88")
    draw.point((60, y - 5), fill="#eaae70")


def draw_fox(draw, phase):
    tail_y = 105 + round(2 * sin(phase * 12 * pi))
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


def draw_owl(draw, phase):
    draw.ellipse((110, 65, 121, 78), fill="#a9755b", outline="#70475a")
    draw.ellipse((113, 71, 119, 77), fill="#d6a478")
    draw.polygon(((109, 69), (110, 62), (113, 64), (117, 64), (120, 62),
                  (122, 69), (120, 72), (112, 72)), fill="#aa826e")
    draw.ellipse((111, 65, 115, 70), fill="#f7f4e1")
    draw.ellipse((116, 65, 120, 70), fill="#f7f4e1")
    blink = (phase * 6 + 0.12) % 1 < 0.065
    for x in (113, 118):
        if blink:
            draw.line((x - 1, 68, x + 1, 68), fill="#514b42")
        else:
            draw.point((x, 67), fill="#33334a")
    draw.point((116, 70), fill="#ffce88")
    draw.point((114, 78), fill="#d4ab79")
    draw.point((118, 78), fill="#d4ab79")


def draw_woodland_animals(draw, phase):
    draw_moose(draw, phase)
    draw_hare(draw, phase)
    draw_fox(draw, phase)
    draw_owl(draw, phase)
