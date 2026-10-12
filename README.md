# RGB Matrix Web Editor and Poor Louis Farms Sign

The existing web editor works on a computer on the local network. A standalone Raspberry Pi service also displays an animated Poor Louis Farms advertisement directly on a HUB75 matrix.

## Animated farm sign

The sign features a bold, pixelated Poor Louis Farms wordmark with a matching amber face and blocky 3D extrusion on both lines. The wordmark gently bobs beneath a detailed crescent moon while a witch flies across the sky. Colorful stars twinkle around a layered Halloween marquee, a blinking black cat, and detailed jack-o'-lanterns that animate from neutral faces to smiles among swaying, curling vines. It uses the matrix dimensions and GPIO settings in `config.py`. All animation frames are rendered once at startup; each update writes only pixels that changed. The scene updates at eight frames per second while the matrix refresh continues independently.

For the 2×2 64×64 panel setup, `config.py` uses a four-bit PWM depth, no temporal dithering, a 120Hz refresh cap, and GPIO slowdown 3 to give the Pi Zero 2 W more signal timing margin. The refresh thread uses precise busy waiting on isolated CPU 3 to avoid timing jitter; device interrupts are routed to CPUs 0–2 so Wi-Fi and normal system work can use the other cores. This reserves one of the Pi Zero 2 W's four cores for panel refresh. The scene updates at eight frames per second using pre-rendered frames and small pixel changes.

The upstream C++ driver supports sleep-based refresh waiting, but its Python binding does not expose that option. Rebuild a private binding for the sign with the included patch, then configure the Pi for headless operation before enabling the service:

```bash
sudo ./deploy/install_low_load_binding.sh /home/epi13/rpi-rgb-led-matrix
sudo ./deploy/configure_headless_pi.sh
sudo ./deploy/install_service.sh
```

The binding installer builds against the Pi's existing driver checkout and places the patched Python modules inside `/opt/rgbmatrix_painter`, leaving the system-wide binding alone. The headless script stops the desktop and unrelated Bluetooth, printer, modem, and removable-disk services while checking that Wi-Fi, SSH, and mDNS remain active. It also isolates CPU 3 and routes device interrupts to CPUs 0–2 in the kernel command line; a reboot is needed for those settings to take effect. The service has a restart limit so a driver fault cannot create a rapid restart loop.

The sign expects the `rgbmatrix` Python binding from [`rpi-rgb-led-matrix`](https://github.com/hzeller/rpi-rgb-led-matrix) and Pillow to be installed for the Pi's system Python. On Raspberry Pi OS, install Pillow with `sudo apt install python3-pil`, and install the matrix library's Python binding using its upstream installation instructions for your Pi and panel.

After copying this repository to the Pi, install and start the boot service:

```bash
sudo ./deploy/install_service.sh
```

The installer puts the sign and matrix config in `/opt/rgbmatrix_painter`, enables `poor-louis-farms.service` at boot, and starts it immediately. Inspect it with `sudo systemctl status poor-louis-farms.service` and its logs with `sudo journalctl -u poor-louis-farms.service -f`.

The service runs as root because the RGB matrix driver needs direct GPIO access. It restarts automatically if the process exits. Adjust `MATRIX_WIDTH`, `MATRIX_HEIGHT`, `CHAIN_LENGTH`, `PARALLEL`, `GPIO_SLOWDOWN`, and `PANEL_BRIGHTNESS` in `config.py` for the connected panel before installation.

---

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
