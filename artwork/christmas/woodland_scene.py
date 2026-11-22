"""A Christmas gathering in a snowy Alaska spruce clearing, drawn at native scale."""
from math import pi, sin

from PIL import Image, ImageDraw

from santa_flyby import SANTA_HAND, flight_pose
from winter_delivery import draw_falling_present, draw_wrapped_present
from winter_scenery import ORNAMENT_COLORS


TREE_X = 66
TREE_SPRITE = ((43, 43, 90, 111), (45, 53), (41, 58))
WOODLAND_DROP_AT = 11.80
WOODLAND_GIFT_COLORS = ("#568d9a", "#3d607f", "#85b7bc", "#ffedad")
UPPER_BERRY_WRAP = ((58, 79), (60, 81), (64, 83), (68, 83), (71, 82), (73, 81))
LOWER_BERRY_WRAP = ((77, 92), (74, 94), (69, 96), (64, 96), (58, 95), (55, 93), (53, 91))
ADULT_WRAP_TIMES = (11.75, 13.30)
OWLET_WRAP_TIMES = (13.90, 15.40)
ADULT_PERCH = (110, 72)
OWLET_PERCH = (123, 74)
ADULT_LANDS_AT, OWLET_LANDS_AT = 17.05, 17.50
WINGBEAT_RATE = 16  # radians per second
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

    # Leave the upper tiers open for the berry garlands the owls install.
    base_garland = ((46, 100), (57, 103), (68, 104), (79, 103), (85, 101))
    draw.line(tuple((x, y + 1) for x, y in base_garland), fill="#795f57")
    draw.line(base_garland, fill="#c6a271")


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


def draw_leveret(draw, seconds):
    y = 123 - hop_height(seconds, 12.65, 0.9, 5) - hop_height(seconds, 14.4, 0.6, 3)
    draw.ellipse((39, y - 6, 47, y), fill="#a7bfd4", outline="#53658e")
    draw.line((40, y - 5, 40, y - 10), fill="#f7f4e1")
    draw.line((43, y - 5, 43, y - 11), fill="#f7f4e1")
    draw.ellipse((40, y - 7, 47, y - 3), fill="#f7f4e1")
    draw.point((45, y - 5), fill="#33334a")
    draw.point((39, y - 2), fill="#f7f4e1")


def draw_fox_kit(draw, x, y, seconds):
    tail_y = y + round(sin(seconds * 8) * 2)
    draw.line(((x + 5, y + 2), (x + 8, y + 2), (x + 10, tail_y)), fill="#b97a6d", width=2)
    draw.point((x + 10, tail_y), fill="#f7f4e1")
    draw.ellipse((x + 2, y - 1, x + 7, y + 4), fill="#b46d6b")
    draw.polygon(((x, y), (x + 1, y - 2), (x + 1, y - 4), (x + 3, y - 2),
                  (x + 5, y - 4), (x + 6, y - 1), (x + 4, y + 2)),
                 fill="#d8937c")
    draw.line((x, y, x + 3, y + 1), fill="#f7f4e1")
    draw.point((x + 2, y - 1), fill="#33334a")


def along_path(points, progress):
    """Interpolate evenly timed waypoints and round to native screen pixels."""
    position = max(0, min(1, progress)) * (len(points) - 1)
    index = min(len(points) - 2, int(position))
    weight = position - index
    (x, y), (next_x, next_y) = points[index:index + 2]
    return round(x + (next_x - x) * weight), round(y + (next_y - y) * weight)


def draw_adult_owl(draw, x, y, seconds, flying):
    # Keep the round eye disks and tufts in a smaller silhouette.
    draw.ellipse((x - 5, y - 4, x + 4, y + 6), fill="#a9755b", outline="#70475a")
    draw.ellipse((x - 2, y + 1, x + 2, y + 5), fill="#d6a478")
    draw.polygon(((x - 5, y - 1), (x - 5, y - 7), (x - 2, y - 5),
                  (x + 1, y - 5), (x + 4, y - 7), (x + 5, y - 1),
                  (x + 3, y + 1), (x - 3, y + 1)), fill="#aa826e")
    for eye in (x - 2, x + 2):
        draw.ellipse((eye - 1, y - 4, eye + 1, y), fill="#f7f4e1")
        if seconds % 1.85 < 0.13:
            draw.line((eye - 1, y - 2, eye + 1, y - 2), fill="#514b42")
        else:
            draw.point((eye - int(flying), y - 3), fill="#33334a")
    draw.point((x, y), fill="#ffce88")
    if not flying:
        draw.point((x - 2, y + 6), fill="#d4ab79")
        draw.point((x + 2, y + 6), fill="#d4ab79")


def draw_owlet(draw, x, y, seconds):
    draw.ellipse((x - 4, y - 4, x + 4, y + 3), fill="#a9755b", outline="#70475a")
    for eye in (x - 1, x + 2):
        draw.line((eye, y - 5, eye, y - 7), fill="#aa826e")
        if (seconds + 0.25) % 1.85 < 0.13:
            draw.line((eye - 1, y - 2, eye + 1, y - 2), fill="#514b42")
        else:
            draw.ellipse((eye - 1, y - 4, eye + 1, y - 1), fill="#f7f4e1")
            draw.point((eye, y - 2), fill="#33334a")
    draw.point((x, y), fill="#ffce88")
    draw.line((x - 2, y + 3, x + 2, y + 3), fill="#d4ab79")


def draw_wings(draw, x, y, width, flap):
    root_depth = width - 3
    for side in (-1, 1):
        tip = (x + side * width, y + flap)
        draw.polygon(((x + side * 2, y + 2), tip, (tip[0] - side * 2, tip[1] + 3),
                      (x + side * 3, y + root_depth)), fill="#a9755b", outline="#aa826e")


def timed_path(seconds, waypoints):
    if seconds <= waypoints[0][0]:
        return waypoints[0][1]
    for (start, origin), (end, target) in zip(waypoints, waypoints[1:]):
        if seconds <= end:
            return along_path((origin, target), (seconds - start) / (end - start))
    return waypoints[-1][1]


def owl_positions(seconds):
    adult_start, adult_finish = ADULT_WRAP_TIMES
    chick_start, chick_finish = OWLET_WRAP_TIMES
    if seconds < adult_start:
        adult = timed_path(seconds, (
            (10.3, (44, 55)), (10.9, (46, 58)), (11.35, (51, 65)), (adult_start, (59, 74)),
        ))
    elif seconds < adult_finish:
        x, y = along_path(UPPER_BERRY_WRAP, (seconds - adult_start) / (adult_finish - adult_start))
        adult = (x + 1, y - 5)
    else:
        adult = timed_path(seconds, (
            (adult_finish, (74, 76)), (13.65, (83, 58)), (14.12, (88, 52)), (15.15, (92, 51)),
            (15.9, (98, 53)), (16.48, (106, 61)), (ADULT_LANDS_AT, ADULT_PERCH),
        ))
    if seconds < chick_start:
        owlet = timed_path(seconds, (
            (9.85, (93, 58)), (11.85, (96, 62)), (13.15, (101, 67)),
            (13.48, (94, 76)), (chick_start, (76, 87)),
        ))
    elif seconds < chick_finish:
        x, y = along_path(LOWER_BERRY_WRAP, (seconds - chick_start) / (chick_finish - chick_start))
        owlet = (x - 1, y - 5)
    else:
        owlet = timed_path(seconds, (
            (chick_finish, (52, 86)), (15.81, (48, 70)), (16.22, (65, 53)),
            (16.60, (87, 46)), (16.96, (108, 49)), (17.20, (119, 61)),
            (OWLET_LANDS_AT, OWLET_PERCH),
        ))
    return adult, owlet


def draw_berry(draw, x, y, highlight):
    draw.line((x - 1, y, x + 1, y), fill="#e47783")
    draw.point((x, y + 1), fill="#b76272")
    if highlight:
        draw.point((x, y - 1), fill="#ffd2ae")


def lay_garland(draw, seconds, bird, route, times, carry_side):
    start, finish = times
    progress = (seconds - start) / (finish - start)
    if progress < 0:
        # Each bird carries a short coil of berries of its own.
        x, y = bird
        coil = ((x, y), (x + carry_side, y + 3), (x + 4 * carry_side, y + 5))
        draw.line(coil, fill="#ffc681")
        draw_berry(draw, *coil[-1], True)
        return

    end = along_path(route, progress)
    placed = min(len(route) - 1, int(progress * (len(route) - 1)))
    strand = (*route[:placed + 1], end)
    draw.line(tuple((x, y + 1) for x, y in strand), fill="#70475a")
    draw.line(strand, fill="#ffc681")
    for index, (x, y) in enumerate(route[:placed + 1]):
        draw_berry(draw, x, y + 1, index % 2 == 0)

    if progress < 1:
        # A short loose end follows the bird's beak while the rest stays on the tree.
        draw.line((end, bird), fill="#ffc681")
        draw.point((end[0], end[1] + 1), fill="#ffd2ae")
    elif seconds - finish < 0.24:
        x, y = route[-1]
        draw.line((x - 1, y - 2, x + 1, y - 2), fill="#ffd2ae")
        draw.point((x, y - 2), fill="#fff6dc")


def draw_owl_garland(draw, seconds):
    adult, owlet = owl_positions(seconds)
    adult_flying = seconds < ADULT_LANDS_AT
    if adult_flying:
        draw_wings(draw, *adult, 8, round(4 * sin(seconds * WINGBEAT_RATE)))
    if seconds < OWLET_LANDS_AT - 0.27:
        # Fold the wing tips up on approach so they stay above the snowy perch.
        flap = round(3 * sin(seconds * WINGBEAT_RATE + 1.5))
        if owlet[0] >= 119:
            flap = min(flap, 0)
        draw_wings(draw, *owlet, 7, flap)
    lay_garland(draw, seconds, adult, UPPER_BERRY_WRAP, ADULT_WRAP_TIMES, -1)
    lay_garland(draw, seconds, owlet, LOWER_BERRY_WRAP, OWLET_WRAP_TIMES, 1)
    draw_adult_owl(draw, *adult, seconds, adult_flying)
    draw_owlet(draw, *owlet, seconds)


def draw_hung_ornament(draw, x, y, color):
    draw.point((x, y - 1), fill="#d4ab79")
    draw.line((x - 1, y, x + 1, y), fill=color)
    draw.point((x, y + 1), fill=color)


def draw_fox_family(image, seconds):
    approach = hop_height(seconds, 13.0, 2.5, 9)
    lift = hop_height(seconds, 13.65, 1.15, 5)
    adult_x, adult_y = 88 - approach, 97 - lift
    kit_x = 109 - hop_height(seconds, 12.92, 2.45, 17)
    kit_y = 118 - hop_height(seconds, 13.20, 0.85, 3)
    place_sprite(image, draw_fox, (88, 89, 128, 118), (adult_x, adult_y), (24, 18), seconds)

    draw = ImageDraw.Draw(image)
    draw_fox_kit(draw, kit_x, kit_y, seconds)
    # The kit brings the ornament to the adult, who reaches the right bough.
    handoff = (seconds - 13.42) / 0.55
    hang = (seconds - 13.97) / 0.54
    mouth = (adult_x, adult_y + 7)
    branch = (80, 98)
    if handoff < 1:
        ornament = along_path(((kit_x - 1, kit_y), mouth), handoff)
    else:
        ornament = along_path((mouth, branch), hang)
    draw_hung_ornament(draw, *ornament, "#ab8aca")
    if 0 <= seconds - 14.51 < 0.24:
        draw.point((branch[0] + 1, branch[1] - 2), fill="#fff2c7")


def draw_woodland_motion(image, phase, seconds, world_x):
    place_sprite(image, draw_woodland_lights, *TREE_SPRITE, phase)
    forward = hop_height(seconds, 11.45, 1.7, 9)
    step = round(2 * sin(seconds * 18)) if forward else 0
    place_sprite(image, draw_moose, (5, 57, 49, 118), (5 + forward, 70), (33, 47), phase, step)
    leap = hop_height(seconds, 12.0, 1.35, 10)
    place_sprite(image, draw_hare, (42, 96, 60, 120), (46 + leap // 3, 100 - leap), (15, 20))
    draw_fox_family(image, seconds)

    draw = ImageDraw.Draw(image)
    draw_leveret(draw, seconds)
    draw_owl_garland(draw, seconds)

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
