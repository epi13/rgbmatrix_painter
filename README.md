
# RGB Matrix Web Editor & Image Converter

A lightweight 64×64 (or any size) RGB LED matrix **image importer + pixel editor** served over the web. Runs on your computer and is accessible from other devices on your LAN.

- Load images (PNG/JPG/GIF) and auto-resize/letterbox to your matrix size
- Gamma correction & brightness control
- Optional ordered dithering for nicer downscales
- Simple pixel editor (brush, eraser, picker, fill)
- Runs as a Flask web server you can access from another device

> Built with Flask + Pillow. No Pi hardware or `rgbmatrix` required.

---

## Quick start

```bash
# On your computer (Python 3.10+ recommended)
python3 -m venv web-env
source web-env/bin/activate
pip install -r requirements.txt
```

Run:

```bash
python app.py             # starts the web server on 0.0.0.0:5000
```

Open http://<your-computer-ip>:5000 in a browser on any device on your LAN.

Login credentials:

- Username: User ID
- Password: User PW

From the web UI you can:

- Draw on the canvas and Push Frame (or enable Live stream)
- Upload an image (PNG/JPG), a GIF (plays looped), or a sprite strip
- Load a PICO-8 .p8 cart to preview its sprite sheet
- Download a snapshot of the current canvas

---

## Controls (UI)

- **Left Click**: draw with brush
- **Right Click**: erase (draw transparent/black)
- **Middle Click**: color picker
- **1–9**: select palette color
- **B**: toggle brush/line tool
- **F**: flood fill
- **E**: toggle eraser
- **G**: toggle ordered dithering (when importing)
- **[ / ]**: brush size –/+
- **Arrow keys**: move cursor 1px (hold Shift for 8px)
- **L**: load image
- **S**: save image
- **R**: reset canvas (black)
- **+ / -**: brightness up/down
- **, / .**: gamma down/up
- **Space**: toggle mirror-to-panel (if available)
- **Esc**: quit

---

## Matrix configuration

Edit `config.py` to match your panel(s):

```python
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64
CHAIN_LENGTH = 1
PARALLEL = 1
GPIO_SLOWDOWN = 2
PANEL_BRIGHTNESS = 50  # 1..100
```

If you have a 64×64 with four chained (64×256), set `CHAIN_LENGTH=4` and `MATRIX_WIDTH=64`, `MATRIX_HEIGHT=64`. The library composes a larger virtual canvas.

> Tip: For Pi Zero 2W, consider `GPIO_SLOWDOWN=3` or `4` if you see glitches.

---

## Headless mode

If you're SSH'd into a Pi without an HDMI display, use:

```bash
python app.py --no-ui --image in.png --save out.png
```

This will still mirror to the panel if `rgbmatrix` is installed.

---

## Notes

- Dithering uses a 4×4 Bayer matrix (ordered dithering) for speed.
- Gamma applies a simple power-law curve to each channel.
- The editor keeps an internal 24-bit RGB canvas; transparency is treated as black.

MIT License.
