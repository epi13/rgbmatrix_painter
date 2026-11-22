"""Native pixel sprites and the sleigh's path through both Christmas scenes."""
from bisect import bisect_right
from math import exp, pi, sin


FLIGHT_START = 0.30
FARM_PASS_SECONDS = 8.25
DROP_AT = 6.70
SANTA_HAND = (20, 7)
FARM_HO_BEATS = tuple(4.05 + i * 0.48 for i in range(6))
WOODLAND_HO_BEATS = tuple(7.04 + i * 0.74 for i in range(14))
HO_COUNT = len(FARM_HO_BEATS) + len(WOODLAND_HO_BEATS)
# Empty beats leave room for the final three letters to fade as the sleigh exits.
HO_BEATS = FARM_HO_BEATS + WOODLAND_HO_BEATS + tuple(WOODLAND_HO_BEATS[-1] + i * 0.74 for i in (1, 2, 3))

DEER_BODY = (
    (0, 7), (3, 8), (5, 7), (10, 7), (12, 4), (12, 3), (14, 5),
    (16, 5), (18, 7), (18, 8), (14, 8), (12, 11), (10, 12), (4, 12), (2, 10),
)
# Knee and hoof offsets for a reach, plant, gather, and kick in the air.
FRONT_LEGS = (((2, 2), (4, 3)), ((1, 3), (1, 5)), ((-2, 2), (0, 3)), ((0, 2), (-3, 3)))
HIND_LEGS = (((-2, 2), (-4, 3)), ((0, 3), (-1, 5)), ((2, 2), (4, 3)), ((0, 2), (2, 4)))
HO_PIXELS = (
    "#.#.###",
    "#.#.#.#",
    "###.#.#",
    "#.#.#.#",
    "#.#.###",
)
HO_COLORS = ("#34364e", "#655773", "#a58099", "#ce9c96", "#ffcf94", "#fff5d2")


def pixels(x, y, points):
    return tuple((x + dx, y + dy) for dx, dy in points)


def flight_position(seconds):
    """Keep the original farm approach, then ease into a slower woodland cruise."""
    farm_speed = 240 / FARM_PASS_SECONDS
    if seconds <= DROP_AT:
        return -97 + (seconds - FLIGHT_START) * farm_speed
    elapsed = seconds - DROP_AT
    launch_x = -97 + (DROP_AT - FLIGHT_START) * farm_speed
    cruise_speed = 16
    coast_time = 0.65
    coast_distance = (farm_speed - cruise_speed) * coast_time * (1 - exp(-elapsed / coast_time))
    return launch_x + cruise_speed * elapsed + coast_distance


def flight_pose(seconds):
    progress = (seconds - FLIGHT_START) / FARM_PASS_SECONDS
    return round(flight_position(seconds)), 20 + round(4 * sin(2 * pi * progress))


def draw_reindeer(draw, x, y, stride, leader, glow, moon_x):
    # Match the sack and sleigh's browns, whose color was checked on the panel.
    lit_fur = "#dea878" if abs(x + 12 - moon_x) < 19 else "#d6a478"
    # Separate the legs by depth, with darker far legs.
    for hip, poses in ((5, HIND_LEGS), (11, FRONT_LEGS)):
        for far in (True, False):
            knee, hoof = poses[(stride + 2 * far) % len(poses)]
            leg_x = x + hip + 2 * far
            leg_tip = (leg_x + hoof[0], y + 11 + hoof[1] - far)
            draw.line(
                ((leg_x, y + 11), (leg_x + knee[0], y + 11 + knee[1]),
                 leg_tip),
                fill="#805266" if far else "#aa826e",
            )
            draw.point(leg_tip, fill="#514b42" if far else "#726458")
    draw.polygon(pixels(x, y, DEER_BODY), fill="#70475a", outline="#aa826e")
    draw.polygon(pixels(x, y, ((3, 9), (5, 8), (10, 8), (12, 6), (15, 5),
                               (17, 7), (14, 7), (11, 10), (8, 11), (4, 11))),
                 fill="#a9755b")
    draw.line(pixels(x, y, ((4, 9), (6, 8), (10, 8), (12, 6))), fill=lit_fur)
    draw.line(pixels(x, y, ((4, 12), (9, 12), (11, 11))), fill="#87646e")
    draw.line(pixels(x, y, ((13, 5), (15, 5), (17, 7))), fill=lit_fur)
    draw.line(pixels(x, y, ((13, 5), (12, 2), (10, 0), (10, -1))), fill="#a6b1c5")
    draw.line(pixels(x, y, ((12, 2), (13, 1), (13, -1))), fill="#a6b1c5")
    draw.line(pixels(x, y, ((13, 4), (15, 2), (16, 1))), fill="#607593")
    draw.point((x + 15, y + 6), fill="#cfb798")
    draw.line(pixels(x, y, ((13, 7), (14, 8))), fill="#aa826e")
    if leader:
        nose_x, nose_y = x + 18, y + 7
        if glow:
            draw.line((nose_x + 2, nose_y - 1, nose_x + 2, nose_y + 1), fill="#902c43")
            draw.point((nose_x + 3, nose_y), fill="#60263c")
        draw.line((nose_x - 1, nose_y, nose_x + 1, nose_y), fill="#e8404c")
        draw.line((nose_x, nose_y - 1, nose_x, nose_y + 1), fill="#f35354")
        draw.point((nose_x, nose_y), fill="#ffb084" if glow else "#ff6f62")


def draw_sleigh(draw, x, y, flutter):
    # The far edge of the sleigh is visible above its curved near side.
    draw.line(pixels(x, y, ((-1, 7), (5, 8), (17, 8), (21, 7), (24, 5), (25, 6))),
              fill="#956c79")
    draw.line(pixels(x, y, ((3, 14), (5, 15), (21, 15), (25, 13), (26, 11))),
              fill="#87646e")
    # The sack slumps over the back rail with two toys peeking out of its open cuff.
    draw.rectangle((x - 2, y + 2, x + 2, y + 6), fill="#6cbea8", outline="#399782")
    draw.line((x, y + 2, x, y + 6), fill="#f1dea2")
    draw.rectangle((x + 4, y, x + 8, y + 6), fill="#cc6475", outline="#9b4f68")
    draw.line((x + 6, y, x + 6, y + 6), fill="#ffd394")
    draw.polygon(
        pixels(x, y, ((-4, 4), (0, 5), (5, 4), (9, 3), (8, 7),
                      (11, 9), (8, 11), (-1, 11), (-3, 9), (-2, 7))),
        fill="#a9755b", outline="#dea878",
    )
    draw.polygon(pixels(x, y, ((-1, 6), (3, 6), (6, 5), (7, 6), (5, 8), (0, 8))),
                 fill="#d6a478")
    draw.line(pixels(x, y, ((-3, 5), (1, 6), (7, 5))), fill="#f1c595")
    draw.line(pixels(x, y, ((1, 7), (2, 9), (6, 10))), fill="#70475a")
    draw.line(pixels(x, y, ((5, 7), (5, 8), (8, 9))), fill="#805266")

    # Side profile, hat, beard, and the hand on the reins.
    draw.polygon(pixels(x, y, ((9, 10), (10, 5), (13, 4), (17, 6), (20, 8), (17, 10))),
                 fill="#9b4560", outline="#b76272")
    draw.polygon(pixels(x, y, ((10, 6), (12, 5), (14, 5), (16, 7), (12, 8))),
                 fill="#db7380")
    draw.line(pixels(x, y, ((14, 7), (17, 8), (20, 8))), fill="#72364f")
    draw.line(pixels(x, y, ((14, 6), (17, 7), (20, 7))), fill="#ca687b")
    hand_x, hand_y = SANTA_HAND
    draw.point((x + hand_x, y + hand_y), fill="#d5b8a3")
    draw.rectangle((x + 13, y + 1, x + 16, y + 4), fill="#d29c87")
    draw.line((x + 15, y + 2, x + 16, y + 2), fill="#f1c595")
    draw.point((x + 17, y + 3), fill="#e4b79c")
    draw.line(pixels(x, y, ((16, 4), (17, 5), (15, 6), (14, 4))), fill="#d8d7e0")
    draw.point((x + 15, y + 6), fill="#a1b6ca")
    draw.polygon(pixels(x, y, ((11, 1), (11, -1), (13, -3), (15, -2), (17, 1))),
                 fill="#b34458")
    draw.line(pixels(x, y, ((12, -2), (13, -3), (15, -2), (16, 0))), fill="#e37d83")
    draw.line((x + 11, y + 1, x + 17, y + 1), fill="#ddd8e5")
    draw.point((x + 10, y - 1 - flutter), fill="#ddd8e5")

    # Curved sleigh sides and a gold runner distinct from the silhouette.
    draw.polygon(
        pixels(x, y, ((-2, 7), (1, 8), (3, 10), (16, 10), (21, 9), (24, 7),
                      (25, 8), (23, 11), (19, 13), (2, 13), (0, 11))),
        fill="#783950", outline="#b67a83",
    )
    draw.polygon(pixels(x, y, ((1, 10), (4, 11), (16, 11), (22, 9), (20, 11),
                               (16, 12), (4, 12))), fill="#ac5865")
    draw.line(pixels(x, y, ((3, 10), (16, 10), (21, 9), (24, 7))), fill="#e4ab75")
    draw.line(pixels(x, y, ((4, 13), (17, 13), (22, 11))), fill="#5d304b")
    draw.line(pixels(x, y, ((4, 13), (4, 15))), fill="#aa826e")
    draw.line(pixels(x, y, ((18, 13), (18, 15))), fill="#aa826e")
    draw.line(pixels(x, y, ((0, 14), (2, 16), (20, 16), (24, 14), (25, 12))), fill="#d4ab79")
    draw.line(pixels(x, y, ((3, 16), (10, 16))), fill="#f1c595")


def draw_trail(draw, seconds, camera_x):
    newest = bisect_right(HO_BEATS, seconds) - 1
    if newest < 0 or newest >= len(HO_BEATS) - 1:
        return
    interval = HO_BEATS[newest + 1] - HO_BEATS[newest]
    progress = (seconds - HO_BEATS[newest]) / interval
    # Only the newest three emissions are eligible to draw. The middle slot
    # stays brighter than either of its neighbours throughout the crossfade.
    for emission in range(max(0, newest - 2), min(newest + 1, HO_COUNT)):
        slot = newest - emission
        if slot == 0:
            tone = round(3 * progress)
        elif slot == 1:
            tone = 5 if 0.18 <= progress < 0.78 else 4
        else:
            tone = round(3 * (1 - progress))
        start_x, start_y = flight_pose(HO_BEATS[emission])
        x = start_x - camera_x - 10
        y = start_y - 7 - round((slot + progress) * 2.6)
        for dy, row in enumerate(HO_PIXELS):
            for dx, pixel in enumerate(row):
                if pixel == "#":
                    draw.point((x + dx, y + dy), fill=HO_COLORS[tone])
        if slot == 1 and 0.30 <= progress < 0.64:
            star_x = x + 9
            draw.line((star_x - 1, y, star_x + 1, y), fill=HO_COLORS[3])
            draw.line((star_x, y - 1, star_x, y + 1), fill=HO_COLORS[5])


def draw_flyby(draw, seconds, camera_x, moon_x):
    draw_trail(draw, seconds, camera_x)
    if seconds < FLIGHT_START:
        return
    x, y = flight_pose(seconds)
    x -= camera_x
    stride = int((seconds - FLIGHT_START) * 11)
    herd = [(x + offset, y - rise + int((stride + index) % 4 == 1))
            for index, (offset, rise) in enumerate(((30, 1), (50, 3), (70, 5)))]
    # Paint the reins first, with a dip between each pair of harness points.
    start_x, start_y = x + SANTA_HAND[0], y + SANTA_HAND[1]
    for deer_x, deer_y in herd:
        end_x, end_y = deer_x + 13, deer_y + 8
        sag = ((start_x + end_x) // 2, (start_y + end_y) // 2 + 2)
        draw.line(((start_x, start_y), sag, (end_x, end_y)), fill="#a58a9c")
        start_x, start_y = end_x, end_y
    for index, (deer_x, deer_y) in enumerate(herd):
        leader = index == len(herd) - 1
        draw_reindeer(draw, deer_x, deer_y, (stride + index) % 4, leader,
                      glow=stride % 6 < 3, moon_x=moon_x)
    draw_sleigh(draw, x, y, (stride // 3) % 2)
