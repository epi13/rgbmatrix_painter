#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0 /path/to/rpi-rgb-led-matrix [app-dir]" >&2
    exit 1
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: sudo $0 /path/to/rpi-rgb-led-matrix [app-dir]" >&2
    exit 2
fi

DRIVER_SOURCE=$1
APP_DIR=${2:-/opt/rgbmatrix_painter}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PATCH_FILE="$SCRIPT_DIR/patches/python-sleep-wait.patch"

if [ ! -f "$DRIVER_SOURCE/.git/HEAD" ] || [ ! -f "$DRIVER_SOURCE/lib/librgbmatrix.a" ]; then
    echo "The driver source checkout and its built lib/librgbmatrix.a are required." >&2
    exit 1
fi

BUILD_DIR=$(mktemp -d /tmp/poor-louis-rgbmatrix.XXXXXX)
trap 'rm -rf "$BUILD_DIR"' EXIT HUP INT TERM

mkdir -p "$BUILD_DIR/source" "$BUILD_DIR/source/lib"
git -C "$DRIVER_SOURCE" archive --format=tar HEAD bindings/python include | tar -xf - -C "$BUILD_DIR/source"
install -m 0644 "$DRIVER_SOURCE/lib/librgbmatrix.a" "$BUILD_DIR/source/lib/"

(
    cd "$BUILD_DIR/source"
    patch --batch --silent -p1 < "$PATCH_FILE"
)

make -C "$BUILD_DIR/source/bindings/python/rgbmatrix" core.cpp graphics.cpp
(
    cd "$BUILD_DIR/source/bindings/python"
    /usr/bin/python3 setup.py build_ext \
        --build-lib "$BUILD_DIR/compiled" \
        --build-temp "$BUILD_DIR/objects"
)

PACKAGE_DIR="$BUILD_DIR/package/rgbmatrix"
install -d -m 0755 "$PACKAGE_DIR"
install -m 0644 \
    "$BUILD_DIR/source/bindings/python/rgbmatrix/__init__.py" \
    "$PACKAGE_DIR/"
install -m 0755 "$BUILD_DIR/compiled/rgbmatrix/"*.so "$PACKAGE_DIR/"

PYTHONPATH="$BUILD_DIR/package" /usr/bin/python3 -c \
    'from rgbmatrix import RGBMatrixOptions; options = RGBMatrixOptions(); options.disable_busy_waiting = True; assert options.disable_busy_waiting'

install -d -m 0755 "$APP_DIR"
if [ -d "$APP_DIR/rgbmatrix" ]; then
    BACKUP_DIR="$APP_DIR/rgbmatrix.before-sleep-wait.$(date +%Y%m%d%H%M%S)"
    cp -a "$APP_DIR/rgbmatrix" "$BACKUP_DIR"
fi
install -d -m 0755 "$APP_DIR/rgbmatrix"
install -m 0644 "$PACKAGE_DIR/__init__.py" "$APP_DIR/rgbmatrix/"
install -m 0755 "$PACKAGE_DIR/"*.so "$APP_DIR/rgbmatrix/"

(
    cd "$APP_DIR"
    /usr/bin/python3 -c \
        'import rgbmatrix; from rgbmatrix import RGBMatrixOptions; options = RGBMatrixOptions(); options.disable_busy_waiting = True; print(rgbmatrix.__file__)'
)
