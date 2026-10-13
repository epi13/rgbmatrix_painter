
# Matrix + app configuration

MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64

# Four 64x64 panels arranged in a 2x2 U-shaped chain.
# Width/height remain the dimensions of ONE panel; the mapper folds the
# four-panel chain into a 128x128 canvas.
CHAIN_LENGTH = 4
PARALLEL = 1
PIXEL_MAPPER_CONFIG = "U-mapper"
GPIO_SLOWDOWN = 3  # Increase signal timing margin on the Pi Zero 2 W.
PANEL_BRIGHTNESS = 60  # 1..100 default
PWM_BITS = 4
PWM_DITHER_BITS = 0
MATRIX_REFRESH_LIMIT_HZ = 120
DISABLE_BUSY_WAITING = False
# Native cached frames swap on every fourth 120Hz panel refresh.
ANIMATION_FPS = 30.0

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
