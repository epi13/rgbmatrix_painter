
# Matrix + app configuration

MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64

# If chaining multiple panels horizontally, set chain length;
# width remains the width of ONE panel (the library composes them).
CHAIN_LENGTH = 1
PARALLEL = 1
GPIO_SLOWDOWN = 2
PANEL_BRIGHTNESS = 60  # 1..100 default

# App defaults
DEFAULT_GAMMA = 2.2
DEFAULT_BRIGHTNESS = 0.9  # multiplier 0..1 (in addition to PANEL_BRIGHTNESS)
TARGET_FPS = 30
PALETTE = [
    (255, 255, 255), # 1
    (255,   0,   0), # 2
    (  0, 255,   0), # 3
    (  0,   0, 255), # 4
    (255, 255,   0), # 5
    (255,   0, 255), # 6
    (  0, 255, 255), # 7
    (255, 128,   0), # 8
    (128,   0, 255), # 9
]
