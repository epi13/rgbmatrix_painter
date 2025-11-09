# RGB Matrix Web Uploader/Editor + Importers

Run a Flask app on the Pi and push frames from any device on your LAN.

## Install
```bash
python3 -m venv web-env
source web-env/bin/activate
pip install pillow flask requests
# Optional (recommended on Pi): rgbmatrix (hzeller) to mirror to panel
```

## Run
```bash
python flask_app.py  # serves on 0.0.0.0:5000
```
Open `http://<pi>:5000` from your laptop/phone:
- Draw on the canvas and **Push** or enable **Live stream** to send frames.
- Upload **Image** (PNG/JPG), **GIF** (animated), or **Sprite Strip** (set cols/rows).
- Upload a **PICO-8 .p8** cart to preview its 128×128 sprite sheet.

## Network streaming from Fedora (or anywhere)
```bash
pip install requests
python client_streamer.py --host http://<pi>:5000 --folder /path/to/frames --fps 15 --loop
# Or a single frame:
python client_streamer.py --host http://<pi>:5000 --image out.png
```

## API (brief)
- `POST /frame?fit=1`  body: PNG -> pushes to panel (letterboxed when `fit=1`).
- `POST /upload_image`  form-data `file`: image -> pushes once.
- `POST /gif`           form-data `file`: .gif -> plays in loop (use `/stop` to halt).
- `POST /strip`         form-data `file`, `cols`, `rows`, `delay`: plays sprite strip.
- `POST /p8_sheet`      form-data `file`: .p8 -> returns 128×128 PNG of sprite sheet.
- `POST /stop`          stop any active playback.
- `GET  /snapshot`      returns the current panel image (PNG).
