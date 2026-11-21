"""Native pixel sprites for Santa's pass through the Christmas sky."""
from math import pi, sin


FLIGHT_START = 0.6
FLIGHT_SECONDS = 7.6
HO_STARTS = (3.60, 4.34, 5.08)

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
HO_COLORS = ("#fff2c4", "#ffdc9c", "#dba980", "#a3829b", "#636787", "#404863", "#262d48")


def pixels(x, y, points):
    return tuple((x + dx, y + dy) for dx, dy in points)


def flight_pose(seconds):
    progress = (seconds - FLIGHT_START) / FLIGHT_SECONDS
    return round(-75 + 218 * progress), 20 + round(4 * sin(2 * pi * progress))


def draw_reindeer(draw, x, y, stride, leader, glow):
    fur, edge = "#222b43", "#8293b2"
    # The far legs use a cooler rim so the two pairs stay distinct in motion.
    for hip, poses in ((5, HIND_LEGS), (11, FRONT_LEGS)):
        for far in (True, False):
            knee, hoof = poses[(stride + 2 * far) % len(poses)]
            leg_x = x + hip + 2 * far
            draw.line(
                ((leg_x, y + 11), (leg_x + knee[0], y + 11 + knee[1]),
                 (leg_x + hoof[0], y + 11 + hoof[1] - far)),
                fill="#4d5d7c" if far else edge,
            )
    draw.polygon(pixels(x, y, DEER_BODY), fill=fur, outline=edge)
    draw.line(pixels(x, y, ((13, 5), (12, 2), (10, 0), (10, -1))), fill="#a6b1c5")
    draw.line(pixels(x, y, ((12, 2), (13, 1), (13, -1))), fill="#a6b1c5")
    draw.line(pixels(x, y, ((13, 4), (15, 2), (16, 1))), fill="#607593")
    draw.point((x + 15, y + 6), fill="#cfb798")
    draw.line(pixels(x, y, ((13, 7), (14, 8))), fill="#a68191")
    if leader:
        nose_x, nose_y = x + 18, y + 7
        if glow:
            draw.line((nose_x + 2, nose_y - 1, nose_x + 2, nose_y + 1), fill="#902c43")
            draw.point((nose_x + 3, nose_y), fill="#60263c")
        draw.line((nose_x - 1, nose_y, nose_x + 1, nose_y), fill="#e8404c")
        draw.line((nose_x, nose_y - 1, nose_x, nose_y + 1), fill="#f35354")
        draw.point((nose_x, nose_y), fill="#ffb084" if glow else "#ff6f62")


def draw_sleigh(draw, x, y, flutter):
    # A tied sack and the edge of one wrapped present rise behind Santa.
    draw.polygon(
        pixels(x, y, ((1, 9), (0, 6), (2, 3), (6, 2), (9, 4), (11, 8), (8, 11), (3, 11))),
        fill="#604253", outline="#bb8c73",
    )
    draw.line(pixels(x, y, ((4, 3), (4, 1), (6, 1), (6, 3))), fill="#b98674")
    draw.point((x + 5, y + 2), fill="#72ab99")

    # Side profile, hat, beard, and the hand on the reins.
    draw.polygon(pixels(x, y, ((9, 10), (10, 5), (13, 4), (17, 6), (20, 8), (17, 10))),
                 fill="#80384f", outline="#b76272")
    draw.line(pixels(x, y, ((14, 6), (17, 7), (20, 7))), fill="#a6495d")
    draw.point((x + 20, y + 7), fill="#d5b8a3")
    draw.rectangle((x + 13, y + 1, x + 16, y + 4), fill="#d29c87")
    draw.point((x + 17, y + 3), fill="#e4b79c")
    draw.line(pixels(x, y, ((16, 4), (17, 5), (15, 6), (14, 4))), fill="#d8d7e0")
    draw.polygon(pixels(x, y, ((11, 1), (11, -1), (13, -3), (15, -2), (17, 1))),
                 fill="#b34458")
    draw.line((x + 11, y + 1, x + 17, y + 1), fill="#ddd8e5")
    draw.point((x + 10, y - 1 - flutter), fill="#ddd8e5")

    # Curved sleigh sides and a gold runner distinct from the silhouette.
    draw.polygon(
        pixels(x, y, ((-2, 7), (1, 8), (3, 10), (16, 10), (21, 9), (24, 7),
                      (25, 8), (23, 11), (19, 13), (2, 13), (0, 11))),
        fill="#673650", outline="#b67a83",
    )
    draw.line(pixels(x, y, ((4, 13), (4, 15))), fill="#aa826e")
    draw.line(pixels(x, y, ((18, 13), (18, 15))), fill="#aa826e")
    draw.line(pixels(x, y, ((0, 14), (2, 16), (20, 16), (24, 14), (25, 12))), fill="#d4ab79")


def draw_trail(draw, seconds):
    for start in HO_STARTS:
        age = seconds - start
        if not 0 <= age < 1.4:
            continue
        start_x, start_y = flight_pose(start)
        x, y = start_x - 9, start_y - 7 - round(age * 6)
        fade = min(len(HO_COLORS) - 1, int(age * 5))
        ink = HO_COLORS[fade]
        for dy, row in enumerate(HO_PIXELS):
            for dx, pixel in enumerate(row):
                if pixel == "#":
                    draw.point((x + dx, y + dy), fill=ink)
        if age < 0.55:
            star_x = x + 9
            draw.point((star_x, y), fill="#fff2c4")
            if int(age * 12) % 3 == 1:
                draw.line((star_x - 1, y, star_x + 1, y), fill="#dba980")
                draw.line((star_x, y - 1, star_x, y + 1), fill="#fff2c4")


def draw_flyby(draw, seconds):
    draw_trail(draw, seconds)
    if not FLIGHT_START <= seconds < FLIGHT_START + FLIGHT_SECONDS:
        return
    x, y = flight_pose(seconds)
    stride = int((seconds - FLIGHT_START) * 11)
    first_y = y - 2 + int(stride % 4 == 1)
    lead_y = y - 4 + int(stride % 4 == 3)
    # Trace both reins behind the sprites so the harnesses visually connect.
    draw.line(((x + 20, y + 7), (x + 27, y + 9), (x + 45, first_y + 8)),
              fill="#9c8497")
    draw.line(((x + 45, first_y + 8), (x + 50, first_y + 10), (x + 66, lead_y + 8)),
              fill="#9c8497")
    draw_reindeer(draw, x + 32, first_y, stride % 4, leader=False, glow=False)
    draw_reindeer(draw, x + 53, lead_y, (stride + 1) % 4, leader=True, glow=stride % 6 < 3)
    draw_sleigh(draw, x, y, (stride // 3) % 2)
