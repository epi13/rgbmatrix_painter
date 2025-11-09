from __future__ import annotations
import io, threading, time, os
from typing import Optional
from flask import Flask, request, send_file, jsonify, render_template_string, redirect, url_for, session
from PIL import Image, ImageEnhance

from config import MATRIX_WIDTH, MATRIX_HEIGHT, DEFAULT_GAMMA, PANEL_BRIGHTNESS, CHAIN_LENGTH, PARALLEL, GPIO_SLOWDOWN
from tools_image import to_panel_image
from pico8 import load_p8_gfx
from anim import gif_frames, strip_frames
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

# Optional RGB matrix hardware initialization
HAVE_MATRIX = False
matrix = None
MATRIX_INIT_ERROR = None
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    HAVE_MATRIX = True
except Exception as e:
    RGBMatrix = None
    RGBMatrixOptions = None
    HAVE_MATRIX = False
    MATRIX_INIT_ERROR = f"import_error: {e}"

if HAVE_MATRIX:
    try:
        opts = RGBMatrixOptions()
        opts.rows = MATRIX_HEIGHT
        opts.cols = MATRIX_WIDTH
        opts.chain_length = CHAIN_LENGTH
        opts.parallel = PARALLEL
        opts.gpio_slowdown = GPIO_SLOWDOWN
        opts.brightness = int(PANEL_BRIGHTNESS)
        matrix = RGBMatrix(options=opts)
    except Exception as e:
        matrix = None
        HAVE_MATRIX = False
        MATRIX_INIT_ERROR = f"init_error: {e}"

current_img = Image.new('RGB', (MATRIX_WIDTH, MATRIX_HEIGHT), (0,0,0))
anim_thread = None
stop_flag = threading.Event()

current_gamma = DEFAULT_GAMMA
current_brightness = PANEL_BRIGHTNESS

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>RGB Matrix Web Editor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, sans-serif; background: radial-gradient(1200px 800px at 20% 0%, #1b2330, #0f1420) fixed; color:#eaeaea; margin:0; height:100vh; overflow:hidden; }
    header { height:56px; display:flex; align-items:center; padding: 0 16px; background: rgba(26,29,38,0.95); border-bottom:1px solid #2b3445; box-shadow: 0 6px 20px rgba(0,0,0,0.45); position:sticky; top:0; backdrop-filter: blur(6px); }
    .topbar { height:56px; display:flex; align-items:center; gap:10px; padding: 0 16px; background: rgba(28,33,46,0.9); border-bottom:1px solid #2b3445; box-shadow: 0 10px 24px rgba(0,0,0,0.35); }
    main { height: calc(100vh - 56px - 56px); display:grid; grid-template-columns: 360px 1fr; grid-template-rows: 1fr; gap:16px; padding:16px; overflow:hidden; }
    .card { background: linear-gradient(180deg, #23262f, #171a22); border:1px solid #2a3342; border-radius:14px; padding:12px; box-shadow: 0 12px 30px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.05); }
    .card.visual { padding:0; display:flex; }
    .stage { flex:1; display:flex; align-items:center; justify-content:center; }
    #canvas { image-rendering: pixelated; background:#0a0d14; box-shadow: 0 10px 40px rgba(0,0,0,0.6), 0 0 0 1px #2b3445; }
    button, input[type=file], input, select { margin:6px 0; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    label { font-size:12px; color:#c7d2e0; }
    button { padding:8px 12px; border-radius:10px; border:1px solid #2b5cb3; background: linear-gradient(180deg,#3a7bd5,#2851a3); color:#fff; box-shadow: 0 6px 16px rgba(20,30,60,0.35), inset 0 1px 0 rgba(255,255,255,0.08); cursor:pointer; transition: all .15s ease; }
    button:hover { filter: brightness(1.05); transform: translateY(-1px); }
    button:active { transform: translateY(0); }
    input, select { padding:6px 8px; border-radius:8px; border:1px solid #2a3342; background:#0f141c; color:#eaeaea; }
    input[type=number] { width:64px; }
    input[type=range] { accent-color:#3fa0ff; }
  </style>
</head>
<body>
  <header>
    <strong>RGB Matrix Web Editor</strong>
  </header>
  <div class="topbar">
    <div class="row">
      <button data-tool="brush">Brush</button>
      <button data-tool="eraser">Eraser</button>
      <button data-tool="fill">Fill</button>
      <label>Size <input type="number" id="size" value="1" min="1" max="16"></label>
      <label>Color <input type="color" id="color" value="#ffffff"></label>
    </div>
  </div>
  <main>
    <section class="card controls">
      <h3>Controls</h3>
      <div class="row">
        <button id="btnPush">Push Frame</button>
        <label><input type="checkbox" id="live"> Live stream</label>
        <label>FPS <input type="number" id="fps" value="10" min="1" max="60" style="width:64px"></label>
      </div>
      <div class="row">
        <label>Gamma <input type="number" id="gamma" value="{{gamma}}" min="0.5" max="3" step="0.1" style="width:72px"></label>
        <label>Brightness <input type="range" id="brightness" min="1" max="100" value="{{brightness}}"></label>
        <span id="bval">{{brightness}}</span>
      </div>
      <div class="row">
        <input type="file" id="fileImage" accept="image/*">
        <button id="btnUpload">Upload Image</button>
      </div>
      <div class="row">
        <input type="file" id="fileGif" accept="image/gif">
        <button id="btnPlayGif">Play GIF</button>
        <button id="btnStop">Stop</button>
      </div>
      <div class="row">
        <input type="file" id="fileStrip" accept="image/*">
        <label>Cols <input type="number" id="cols" value="8" min="1" style="width:56px"></label>
        <label>Rows <input type="number" id="rows" value="1" min="1" style="width:56px"></label>
        <label>Delay ms <input type="number" id="delay" value="80" min="1" style="width:72px"></label>
        <button id="btnPlayStrip">Play Strip</button>
      </div>
      <div class="row">
        <input type="file" id="fileP8" accept=".p8">
        <button id="btnP8Sheet">Load PICO-8 Sheet</button>
      </div>
      <hr/>
      <div class="row">
        <button id="btnClear">Clear</button>
        <button id="btnSnapshot">Download Snapshot</button>
      </div>
    </section>
    <section id="canvasCard" class="card visual">
      <div class="stage">
        <canvas id="canvas" width="{{w}}" height="{{h}}"></canvas>
      </div>
    </section>
  </main>

<script>
const W={{w}}, H={{h}};
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d', { willReadFrequently:true });
ctx.imageSmoothingEnabled = false;
const gammaEl = document.getElementById('gamma');
const brightEl = document.getElementById('brightness');
const bvalEl = document.getElementById('bval');

let tool = 'brush';
let size = 1;
let color = '#ffffff';
let live = false;
let fps = 10;
let streamingTimer = null;

// Responsive integer scaling so canvas fits the visual panel with no page scroll
const canvasCard = document.getElementById('canvasCard');
let SCALE = 1;
function updateCanvasScale(){
  const rect = canvasCard.getBoundingClientRect();
  const availW = Math.max(1, rect.width - 24);
  const availH = Math.max(1, rect.height - 24);
  let s = Math.floor(Math.min(availW / W, availH / H));
  s = Math.max(2, Math.min(16, s));
  SCALE = s;
  canvas.style.width = (W*SCALE) + 'px';
  canvas.style.height = (H*SCALE) + 'px';
}
window.addEventListener('resize', updateCanvasScale);
updateCanvasScale();

function drawPoint(x,y) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, size, size);
}

function fill(x,y) {
  // simple flood fill on pixel data
  const img = ctx.getImageData(0,0,W,H);
  const data = img.data;
  const idx = (x + y*W)*4;
  const target = data.slice(idx, idx+4).join(',');
  const [r,g,b] = hexToRgb(color);
  const stack = [[x,y]];
  const seen = new Set();
  while (stack.length) {
    const [cx,cy] = stack.pop();
    if (cx<0||cy<0||cx>=W||cy>=H) continue;
    const i = (cx + cy*W)*4;
    const key = i;
    if (seen.has(key)) continue; seen.add(key);
    const cur = data.slice(i,i+4).join(',');
    if (cur !== target) continue;
    data[i]=r; data[i+1]=g; data[i+2]=b; data[i+3]=255;
    stack.push([cx-1,cy],[cx+1,cy],[cx,cy-1],[cx,cy+1]);
  }
  ctx.putImageData(img,0,0);
}

function hexToRgb(hex){
  const v = parseInt(hex.slice(1), 16);
  return [(v>>16)&255,(v>>8)&255,v&255];
}

let settingsTimer = null;
function scheduleSettingsPush(){
  if (settingsTimer) clearTimeout(settingsTimer);
  settingsTimer = setTimeout(pushSettings, 150);
}
async function pushSettings(){
  const g = parseFloat(gammaEl?.value || '{{gamma}}');
  const b = parseInt(brightEl?.value || '{{brightness}}', 10);
  if (bvalEl) bvalEl.textContent = b;
  try {
    await fetch('/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ gamma: g, brightness: b })});
  } catch (e) {}
}

function pushFrame(){
  canvas.toBlob(async (blob)=>{
    const res = await fetch('/frame?fit=1', {method:'POST', body: blob});
  }, 'image/png');
}

function startStream(){
  stopStream();
  streamingTimer = setInterval(pushFrame, Math.max(16, 1000/Math.min(60, Math.max(1, fps))));
}
function stopStream(){ if (streamingTimer) clearInterval(streamingTimer); streamingTimer=null; }

// Mouse painting
let painting=false;
canvas.addEventListener('mousedown', (e)=>{
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / SCALE);
  const y = Math.floor((e.clientY - rect.top) / SCALE);
  painting=true;
  if (tool==='fill') fill(x,y);
  else if (tool==='eraser'){ ctx.clearRect(x,y,size,size); }
  else drawPoint(x,y);
  if (live) pushFrame();
});
canvas.addEventListener('mousemove', (e)=>{
  if (!painting) return;
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / SCALE);
  const y = Math.floor((e.clientY - rect.top) / SCALE);
  if (tool==='eraser'){ ctx.clearRect(x,y,size,size); }
  else if (tool==='brush'){ drawPoint(x,y); }
});
document.addEventListener('mouseup', ()=>{ painting=false; if (live) pushFrame(); });

// UI hooks
document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>tool=b.dataset.tool);
document.getElementById('size').oninput = (e)=> size = parseInt(e.target.value||'1',10);
document.getElementById('color').oninput = (e)=> color = e.target.value;
document.getElementById('btnPush').onclick = pushFrame;
gammaEl && (gammaEl.oninput = scheduleSettingsPush);
brightEl && (brightEl.oninput = scheduleSettingsPush);
document.getElementById('live').onchange = (e)=>{ live = e.target.checked; live ? startStream() : stopStream(); };
document.getElementById('fps').oninput = (e)=>{ fps = parseInt(e.target.value||'10',10); if (live) startStream(); };
document.getElementById('btnClear').onclick = ()=>{ ctx.clearRect(0,0,W,H); if (live) pushFrame(); };

document.getElementById('btnSnapshot').onclick = ()=>{
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = 'snapshot.png'; a.click();
};

// Upload single image
document.getElementById('btnUpload').onclick = async ()=>{
  const f = document.getElementById('fileImage').files[0];
  if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  await fetch('/upload_image', { method:'POST', body: fd });
  // Also update canvas preview
  const img = new Image();
  img.onload = ()=>{ ctx.clearRect(0,0,W,H); ctx.drawImage(img,0,0,W,H); };
  img.src = URL.createObjectURL(f);
};

// GIF
document.getElementById('btnPlayGif').onclick = async ()=>{
  const f = document.getElementById('fileGif').files[0];
  if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  await fetch('/gif', {method:'POST', body: fd});
};

// Strip
document.getElementById('btnPlayStrip').onclick = async ()=>{
  const f = document.getElementById('fileStrip').files[0];
  if (!f) return;
  const cols = document.getElementById('cols').value;
  const rows = document.getElementById('rows').value;
  const delay = document.getElementById('delay').value;
  const fd = new FormData(); fd.append('file', f);
  fd.append('cols', cols); fd.append('rows', rows); fd.append('delay', delay);
  await fetch('/strip', {method:'POST', body: fd});
};

// Stop animations
document.getElementById('btnStop').onclick = ()=> fetch('/stop', {method:'POST'});

// PICO-8
document.getElementById('btnP8Sheet').onclick = async ()=>{
  const f = document.getElementById('fileP8').files[0];
  if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/p8_sheet', {method:'POST', body: fd});
  const blob = await res.blob();
  const img = new Image();
  img.onload = ()=>{
    // draw the 128x128 sheet scaled into our canvas for quick picking
    ctx.clearRect(0,0,W,H); ctx.drawImage(img,0,0,W,H);
  };
  img.src = URL.createObjectURL(blob);
};
</script>
</body>
</html>
"""

LOGIN_HTML = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Login</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#111; color:#eee; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
    form { background:#1e1e1e; padding:20px; border-radius:12px; width:300px; display:flex; flex-direction:column; gap:10px; }
    input { padding:8px; border-radius:6px; border:1px solid #333; background:#111; color:#eee; }
    button { padding:8px 10px; }
    .err { color:#f55; font-size:12px; }
  </style>
  </head>
<body>
  <form method=\"post\" action=\"/login\"> 
    <h3>Sign in</h3>
    {% if error %}<div class=\"err\">{{error}}</div>{% endif %}
    <input name=\"username\" placeholder=\"Username\" autocomplete=\"username\" />
    <input name=\"password\" type=\"password\" placeholder=\"Password\" autocomplete=\"current-password\" />
    <button type=\"submit\">Login</button>
  </form>
</body>
</html>
"""

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user") != "epi13":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.get("/login")
def login():
    if session.get("user") == "epi13":
        return redirect(url_for("index"))
    return render_template_string(LOGIN_HTML, error=None)

@app.post("/login")
def do_login():
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "")
    if u == "epi13" and p == "1324":
        session["user"] = "epi13"
        return redirect(url_for("index"))
    return render_template_string(LOGIN_HTML, error="Invalid credentials")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def _set_current(img: Image.Image):
    global current_img
    im = img.convert('RGB')
    try:
        factor = max(1, min(100, int(current_brightness))) / 100.0
    except Exception:
        factor = 1.0
    if factor != 1.0:
        im = ImageEnhance.Brightness(im).enhance(factor)
    current_img = im
    # Push to hardware if available
    if matrix is not None:
        try:
            matrix.SetImage(im, 0, 0, unsafe=False)
        except Exception:
            pass

@app.get("/")
@login_required
def index():
    return render_template_string(INDEX_HTML, w=MATRIX_WIDTH, h=MATRIX_HEIGHT, gamma=current_gamma, brightness=current_brightness)

@app.post("/upload_image")
@login_required
def upload_image():
    f = request.files.get('file')
    if not f: return ('no file', 400)
    im = Image.open(f.stream)
    panel = to_panel_image(im, MATRIX_WIDTH, MATRIX_HEIGHT, gamma=current_gamma, dither=False)
    _set_current(panel)
    return ('ok', 200)

@app.post("/frame")
@login_required
def frame():
    # Accept raw PNG blob; if fit=1, letterbox to panel
    fit = request.args.get('fit', '0') == '1'
    data = request.get_data()
    im = Image.open(io.BytesIO(data))
    if fit:
        im = to_panel_image(im, MATRIX_WIDTH, MATRIX_HEIGHT, gamma=current_gamma, dither=False)
    else:
        im = im.resize((MATRIX_WIDTH, MATRIX_HEIGHT))
    _set_current(im)
    return ('ok', 200)

@app.get("/snapshot")
@login_required
def snapshot():
    buf = io.BytesIO()
    current_img.save(buf, 'PNG'); buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.get("/settings")
@login_required
def get_settings():
    return jsonify({"gamma": current_gamma, "brightness": current_brightness})

@app.post("/settings")
@login_required
def set_settings():
    data = request.get_json(silent=True) or {}
    global current_gamma, current_brightness
    g = data.get("gamma")
    b = data.get("brightness")
    if g is not None:
        try:
            current_gamma = max(0.1, min(5.0, float(g)))
        except Exception:
            pass
    if b is not None:
        try:
            v = int(b)
            v = max(1, min(100, v))
            current_brightness = v
        except Exception:
            pass
    # Apply hardware brightness if available
    if matrix is not None:
        try:
            matrix.brightness = int(current_brightness)
        except Exception:
            pass
    return jsonify({"gamma": current_gamma, "brightness": current_brightness})

@app.get("/status")
@login_required
def status():
    return jsonify({
        "have_matrix": HAVE_MATRIX,
        "init_error": MATRIX_INIT_ERROR,
    })

def _play_frames(frames, delays_ms):
    stop_flag.clear()
    while not stop_flag.is_set():
        for f, d in zip(frames, delays_ms):
            if stop_flag.is_set(): break
            _set_current(to_panel_image(f, MATRIX_WIDTH, MATRIX_HEIGHT, gamma=current_gamma, dither=False))
            time.sleep(max(0.001, d/1000.0))

def _start_anim_thread(target, *args):
    global anim_thread
    stop()
    anim_thread = threading.Thread(target=target, args=args, daemon=True)
    anim_thread.start()

def stop():
    stop_flag.set()

@app.post("/stop")
@login_required
def stop_route():
    stop()
    return ('stopped', 200)

@app.post("/gif")
@login_required
def gif_route():
    f = request.files.get('file')
    if not f: return ('no file', 400)
    frames = []
    delays = []
    for fr, delay in gif_frames(f.stream):
        frames.append(fr)
        delays.append(delay or 100)
    _start_anim_thread(_play_frames, frames, delays)
    return ('playing', 200)

@app.post("/strip")
@login_required
def strip_route():
    f = request.files.get('file')
    if not f: return ('no file', 400)
    cols = int(request.form.get('cols', 8))
    rows = int(request.form.get('rows', 1))
    delay = int(request.form.get('delay', 80))
    img = Image.open(f.stream).convert('RGBA')
    frames = strip_frames(img, cols, rows)
    delays = [delay for _ in frames]
    _start_anim_thread(_play_frames, frames, delays)
    return ('playing', 200)

@app.post("/p8_sheet")
@login_required
def p8_sheet():
    f = request.files.get('file')
    if not f: return ('no file', 400)
    sheet = load_p8_gfx(f.stream)
    # return the raw sheet as PNG for preview
    buf = io.BytesIO()
    sheet.save(buf, 'PNG'); buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    # Run on all interfaces so your laptop can connect
    app.run(host='0.0.0.0', port=5000, debug=False)
