"""Animate the gift delivery and the snowman's reaction at native size."""
from math import cos, pi, sin, sqrt

from santa_flyby import SANTA_HAND, flight_pose


DROP_AT = 6.70
FALL_SECONDS = 1.0
LAND_AT = DROP_AT + FALL_SECONDS
GIFT_X, GIFT_Y = 122, 118
GIFT_FADE_START = 9.12
GIFT_FADE_STEP = 0.12
GIFT_COLORS = (
    ("#e08fa0", "#684562", "#ffedad"),
    ("#c899ad", "#755771", "#dfd5b4"),
    ("#ac9eb2", "#806d84", "#c0bfb5"),
    ("#97a2b6", "#878c9f", "#a4b1b9"),
)
SNOWBALL_SHADES = ("#53658e", "#7b96b5", "#a7bfd4", "#d2e4e7", "#f7f4e1")


def draw_gift(draw, seconds):
    if seconds < DROP_AT:
        return
    progress = (seconds - DROP_AT) / FALL_SECONDS
    tilt = 0
    fade = 0
    if progress < 1:
        sleigh_x, sleigh_y = flight_pose(DROP_AT)
        start_x, start_y = sleigh_x + SANTA_HAND[0], sleigh_y + SANTA_HAND[1] + 2
        x = round(GIFT_X - (GIFT_X - start_x) * (1 - progress) ** 4)
        y = round(start_y + (GIFT_Y - start_y) * (0.20 * progress + 0.80 * progress ** 2))
        tilt = (0, 1, 0, -1)[int(progress * 12) % 4]
    else:
        landed = seconds - LAND_AT
        # A short bounce and a few displaced snow pixels mark contact.
        bounce = sin(pi * min(1, landed / 0.20)) * 2
        x, y = GIFT_X, GIFT_Y - round(bounce)
        if landed < 0.33:
            spread = round(landed * 10)
            draw.point((x - 4 - spread, y + 3 - spread), fill="#d9e4e5")
            draw.point((x + 4 + spread, y + 3 - spread), fill="#c4d3de")
            draw.point((x - 2 - spread, y + 4), fill="#afc1d6")
        if seconds >= GIFT_FADE_START:
            fade = 1 + int((seconds - GIFT_FADE_START) / GIFT_FADE_STEP)
            if fade >= len(GIFT_COLORS):
                return

    paper, edge, ribbon = GIFT_COLORS[fade]
    draw.polygon(((x - 3, y - 3 + tilt), (x + 3, y - 3 - tilt),
                  (x + 3, y + 3 - tilt), (x - 3, y + 3 + tilt)), fill=paper, outline=edge)
    draw.line((x - 2, y - 1 + tilt, x + 2, y - 1 - tilt), fill=ribbon)
    draw.line((x, y - 3, x, y + 2), fill=ribbon)
    draw.point((x + 1, y - 4), fill=ribbon)


def draw_snowball(draw, x, y, rx, ry):
    # Use the surface normal of an ellipse with light from the upper right.
    for py in range(y - ry, y + ry + 1):
        ny = (py - y) / ry
        for px in range(x - rx, x + rx + 1):
            nx = (px - x) / rx
            depth_squared = 1 - nx * nx - ny * ny
            if depth_squared < 0:
                continue
            light = 0.45 * nx - 0.46 * ny + 0.77 * sqrt(depth_squared)
            shade = sum(light > threshold for threshold in (0.04, 0.34, 0.61, 0.82))
            draw.point((px, py), fill=SNOWBALL_SHADES[shade])


def draw_snowman(draw, seconds, phase):
    x = 74
    wave_age = seconds - LAND_AT
    wave = 0 <= wave_age < 1.30
    lift = max(0, min(wave_age / 0.16, (1.30 - wave_age) / 0.19, 1))
    elbow_x, elbow_y = x + 9, 111 - round(5 * lift)
    # Rotate the same length of twig around the elbow throughout the wave.
    angle = 0.45 - lift * (1.55 + 0.50 * sin(wave_age * 7 * pi))
    hand_x = elbow_x + round(5 * cos(angle))
    hand_y = elbow_y + round(5 * sin(angle))

    twig = "#be956f"
    draw.line(((x - 5, 113), (x - 9, 110), (x - 12, 107)), fill=twig, width=2)
    draw.line(((x - 10, 109), (x - 13, 109)), fill=twig)
    draw.line(((x + 5, 112), (elbow_x, elbow_y), (hand_x, hand_y)), fill=twig, width=2)
    draw.line(((hand_x, hand_y), (hand_x + 2, hand_y - 1)), fill=twig)

    draw_snowball(draw, x, 114, 8, 8)
    for button_y in (115, 118):
        draw.point((x + 1, button_y - 1), fill="#7b96b5")
        draw.point((x, button_y), fill="#33334a")

    # The head tilts toward Santa on the wave; idle motion comes from the scarf and blinks.
    head_x = x + int(lift >= 0.5)
    draw_snowball(draw, head_x, 105, 5, 6)
    draw.rectangle((head_x - 4, 96, head_x + 4, 100), fill="#554364", outline="#ad96b7")
    draw.ellipse((head_x - 4, 95, head_x + 4, 97), fill="#89749e")
    draw.line((head_x + 3, 97, head_x + 3, 99), fill="#a891aa")
    draw.rectangle((head_x - 5, 100, head_x + 5, 101), fill="#bc6687")
    draw.line((head_x - 6, 102, head_x + 6, 102), fill="#735b80")

    blink = not wave and (phase * 3 + 0.18) % 1 < 0.045
    eyes_x = head_x + int(wave)
    eyes_y = 104 + int(blink)
    draw.point((eyes_x - 2, eyes_y), fill="#373b51")
    draw.point((eyes_x + 2, eyes_y), fill="#373b51")
    draw.line((head_x, 106, head_x + 2 + int(wave), 106), fill="#e68958")
    draw.point((head_x + 1 + int(wave), 105), fill="#ffc681")
    draw.line(((head_x - 1, 107), (head_x, 108), (head_x + 1, 108)), fill="#715568")
    draw.line((x - 5, 110, x + 5, 110), fill="#bb5372", width=2)
    tail = round(sin(phase * 12 * pi))
    draw.line(((x + 4, 110), (x + 5, 113), (x + 6, 114 + tail)), fill="#d97282", width=2)


def draw_delivery(draw, seconds, phase):
    draw_snowman(draw, seconds, phase)
    draw_gift(draw, seconds)
