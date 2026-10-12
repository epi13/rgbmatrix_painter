#!/bin/sh
set -eu

APP_DIR=/opt/rgbmatrix_painter
SERVICE=/etc/systemd/system/poor-louis-farms.service
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0" >&2
    exit 1
fi

if ! /usr/bin/python3 -c 'from rgbmatrix import RGBMatrix, RGBMatrixOptions; from PIL import Image' 2>/dev/null; then
    echo "Install Pillow and the rpi-rgb-led-matrix Python binding first." >&2
    exit 1
fi

install -d -m 0755 "$APP_DIR"
install -m 0644 "$REPO_DIR/poor_louis_farms.py" "$REPO_DIR/config.py" "$APP_DIR/"
install -m 0644 "$SCRIPT_DIR/systemd/poor-louis-farms.service" "$SERVICE"

if ! (cd "$APP_DIR" && /usr/bin/python3 -c 'from rgbmatrix import RGBMatrixOptions; from PIL import Image; options = RGBMatrixOptions(); options.disable_busy_waiting = True'); then
    echo "Install the sleep-wait rgbmatrix binding before enabling the service." >&2
    exit 1
fi

systemctl daemon-reload
systemctl enable --now poor-louis-farms.service
systemctl --no-pager --full status poor-louis-farms.service
