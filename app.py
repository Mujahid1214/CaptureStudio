"""
Flask Capture App  –  SINGLE FILE VERSION
==========================================
Drop this ONE file anywhere and run:  python app.py
No templates/ folder needed.  HTML is embedded via render_template_string().

Requirements (install once):
    pip install flask playwright requests
    python -m playwright install chromium
"""

import os
import time
import uuid
import base64
import threading
import traceback
from datetime import datetime
from pathlib import Path

import requests
from flask import (
    Flask, request, jsonify,
    render_template_string, send_from_directory, abort
)
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# App setup  –  folders are created next to THIS script file, wherever it is
# ---------------------------------------------------------------------------

app = Flask(__name__)

BASE_DIR        = Path(__file__).parent          # same folder as app.py
SCREENSHOTS_DIR = BASE_DIR / "screenshots"       # ./screenshots/
RECORDINGS_DIR  = BASE_DIR / "recordings"        # ./recordings/

SCREENSHOTS_DIR.mkdir(exist_ok=True)
RECORDINGS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# HTML template  (embedded so no templates/ folder is required)
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Capture Studio</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg: #0c0c0f; --surface: #141418; --surface2: #1c1c22;
      --border: #2a2a35; --accent1: #00ffc8; --accent2: #ff5c87;
      --text: #e8e8f0; --muted: #7070a0;
      --mono: 'Space Mono', monospace; --sans: 'DM Sans', sans-serif;
      --radius: 12px; --transition: 0.2s cubic-bezier(.4,0,.2,1);
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--sans); background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }
    body::before {
      content: ''; position: fixed; inset: 0;
      background-image: linear-gradient(var(--border) 1px, transparent 1px),
                        linear-gradient(90deg, var(--border) 1px, transparent 1px);
      background-size: 40px 40px; opacity: .18; pointer-events: none; z-index: 0;
    }
    .shell { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 40px 24px 80px; }
    header { display: flex; align-items: center; gap: 16px; margin-bottom: 48px; }
    .logo-icon {
      width: 44px; height: 44px; border-radius: 10px;
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .logo-text h1 { font-family: var(--mono); font-size: 1.3rem; letter-spacing: -1px; }
    .logo-text p  { font-size: .8rem; color: var(--muted); margin-top: 2px; }
    .panels { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 720px) { .panels { grid-template-columns: 1fr; } }
    .panel {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 28px; position: relative; overflow: hidden;
    }
    .panel.screenshot::before { background: var(--accent1); }
    .panel.radio::before      { background: var(--accent2); }
    .panel::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
    .panel-title { font-family: var(--mono); font-size: .75rem; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; }
    .panel.screenshot .panel-title { color: var(--accent1); }
    .panel.radio      .panel-title { color: var(--accent2); }
    .field { margin-bottom: 14px; }
    .field label { display: block; font-size: .78rem; color: var(--muted); margin-bottom: 6px; font-weight: 600; }
    .field input {
      width: 100%; background: var(--surface2); border: 1px solid var(--border);
      border-radius: 8px; color: var(--text); font-family: var(--mono);
      font-size: .82rem; padding: 10px 14px; outline: none; transition: border-color var(--transition);
    }
    .field input:focus { border-color: var(--accent1); }
    .panel.radio .field input:focus { border-color: var(--accent2); }
    .field input::placeholder { color: var(--muted); }
    .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .btn {
      display: inline-flex; align-items: center; gap: 8px; border: none;
      border-radius: 8px; padding: 11px 22px; font-family: var(--mono);
      font-size: .8rem; font-weight: 700; letter-spacing: .5px;
      cursor: pointer; transition: all var(--transition);
    }
    .btn:disabled { opacity: .45; cursor: not-allowed; }
    .btn-teal { background: var(--accent1); color: #000; }
    .btn-teal:not(:disabled):hover { background: #00e8b4; box-shadow: 0 0 20px rgba(0,255,200,.35); }
    .btn-pink { background: var(--accent2); color: #fff; }
    .btn-pink:not(:disabled):hover { background: #ff4076; box-shadow: 0 0 20px rgba(255,92,135,.35); }
    .result-area { margin-top: 20px; min-height: 48px; display: none; }
    .result-area.visible { display: block; }
    .spinner {
      width: 22px; height: 22px; border: 2px solid var(--border);
      border-top-color: var(--accent1); border-radius: 50%;
      animation: spin .7s linear infinite; display: inline-block; vertical-align: middle;
    }
    .panel.radio .spinner { border-top-color: var(--accent2); }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status-msg { display: inline-block; font-size: .82rem; color: var(--muted); margin-left: 10px; vertical-align: middle; }
    .preview-box { margin-top: 12px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    .preview-box img { width: 100%; display: block; }
    .action-row { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: .78rem; color: var(--muted); }
    .action-row a { color: var(--accent1); text-decoration: none; font-family: var(--mono); }
    .action-row a:hover { text-decoration: underline; }
    .error-box {
      background: rgba(255,60,60,.1); border: 1px solid rgba(255,60,60,.3);
      border-radius: 8px; padding: 10px 14px; font-size: .8rem; color: #ff7070;
    }
    .success-chip {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(255,92,135,.1); border: 1px solid rgba(255,92,135,.25);
      border-radius: 6px; padding: 6px 12px; font-family: var(--mono); font-size: .78rem; color: var(--accent2);
    }
    audio { width: 100%; margin-top: 10px; accent-color: var(--accent2); }
    .history-section { margin-top: 40px; }
    .history-section h2 { font-family: var(--mono); font-size: .75rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); margin-bottom: 16px; }
    .history-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
    .tab {
      padding: 6px 16px; border: 1px solid var(--border); border-radius: 6px;
      font-size: .8rem; font-family: var(--mono); cursor: pointer;
      background: transparent; color: var(--muted); transition: all var(--transition);
    }
    .tab.active      { border-color: var(--accent1); color: var(--accent1); }
    .tab.radio-tab.active { border-color: var(--accent2); color: var(--accent2); }
    .history-list { display: flex; flex-direction: column; gap: 8px; }
    .history-item {
      display: flex; align-items: center; justify-content: space-between;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 12px 16px; font-size: .8rem;
    }
    .history-item .name { font-family: var(--mono); color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 55%; }
    .history-item .meta { color: var(--muted); font-size: .74rem; }
    .history-item a { color: var(--accent1); text-decoration: none; font-family: var(--mono); font-size: .74rem; }
    .history-item a:hover { text-decoration: underline; }
    .empty-msg { color: var(--muted); font-size: .82rem; padding: 20px 0; text-align: center; }
  </style>
</head>
<body>
<div class="shell">
  <header>
    <div class="logo-icon">📸</div>
    <div class="logo-text">
      <h1>Capture Studio</h1>
      <p>Screenshot &amp; Radio Recorder — Flask + Playwright</p>
    </div>
  </header>

  <div class="panels">
    <!-- SCREENSHOT PANEL -->
    <div class="panel screenshot">
      <div class="panel-title">🖥 Web Screenshot</div>
      <div class="field">
        <label>Page URL</label>
        <input id="ss-url" type="url" placeholder="https://example.com"/>
      </div>
      <div class="row2">
        <div class="field"><label>Width (px)</label><input id="ss-w" type="number" value="1280" min="320" max="3840"/></div>
        <div class="field"><label>Height (px)</label><input id="ss-h" type="number" value="900" min="200" max="4000"/></div>
      </div>
      <button class="btn btn-teal" id="ss-btn" onclick="takeScreenshot()">📷 Capture</button>
      <div class="result-area" id="ss-result"></div>
    </div>

    <!-- RADIO PANEL -->
    <div class="panel radio">
      <div class="panel-title">📻 Radio Recorder</div>
      <div class="field">
        <label>Stream URL (.mp3 / .aac / .ogg)</label>
        <input id="radio-url" type="url" placeholder="http://stream.example.com/live.mp3"/>
      </div>
      <div class="field">
        <label>Duration (seconds, max 120)</label>
        <input id="radio-dur" type="number" value="30" min="5" max="120"/>
      </div>
      <button class="btn btn-pink" id="radio-btn" onclick="startRadio()">⏺ Record</button>
      <div class="result-area" id="radio-result"></div>
    </div>
  </div>

  <!-- HISTORY -->
  <div class="history-section">
    <h2>Saved Files</h2>
    <div class="history-tabs">
      <button class="tab active"   id="tab-ss"    onclick="switchTab('screenshots')">Screenshots</button>
      <button class="tab radio-tab" id="tab-radio" onclick="switchTab('recordings')">Recordings</button>
      <button class="tab" onclick="loadHistory()" style="margin-left:auto">↻ Refresh</button>
    </div>
    <div class="history-list" id="history-list"><p class="empty-msg">Loading…</p></div>
  </div>
</div>

<script>
let _historyData = { screenshots: [], recordings: [] };
let _activeTab   = 'screenshots';
let _radioJobId  = null;
let _radioPollId = null;

async function takeScreenshot() {
  const url  = document.getElementById('ss-url').value.trim();
  const w    = parseInt(document.getElementById('ss-w').value) || 1280;
  const h    = parseInt(document.getElementById('ss-h').value) || 900;
  const btn  = document.getElementById('ss-btn');
  const area = document.getElementById('ss-result');
  if (!url) { alert('Please enter a URL.'); return; }
  btn.disabled = true;
  area.className = 'result-area visible';
  area.innerHTML = '<span class="spinner"></span><span class="status-msg">Launching headless browser…</span>';
  try {
    const res  = await fetch('/screenshot', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url,width:w,height:h}) });
    const data = await res.json();
    if (data.success) {
      area.innerHTML = `<div class="preview-box"><img src="${data.preview}" alt="preview"/></div>
        <div class="action-row"><span>✅ ${data.taken_at}</span>
        <a href="/download/screenshots/${data.filename}" download>⬇ Download</a></div>`;
      loadHistory();
    } else {
      area.innerHTML = `<div class="error-box">❌ ${data.error}</div>`;
    }
  } catch(e) {
    area.innerHTML = `<div class="error-box">❌ ${e.message}</div>`;
  } finally { btn.disabled = false; }
}

async function startRadio() {
  const url      = document.getElementById('radio-url').value.trim();
  const duration = parseInt(document.getElementById('radio-dur').value) || 30;
  const btn      = document.getElementById('radio-btn');
  const area     = document.getElementById('radio-result');
  if (!url) { alert('Please enter a stream URL.'); return; }
  if (_radioPollId) { clearInterval(_radioPollId); _radioPollId = null; }
  btn.disabled = true;
  area.className = 'result-area visible';
  area.innerHTML = '<span class="spinner"></span><span class="status-msg">Connecting…</span>';
  try {
    const res  = await fetch('/radio', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url,duration}) });
    const data = await res.json();
    if (!data.success) { area.innerHTML=`<div class="error-box">❌ ${data.error}</div>`; btn.disabled=false; return; }
    _radioJobId = data.job_id;
    let elapsed = 0;
    _radioPollId = setInterval(async () => {
      elapsed += 1.5;
      const pct = Math.min(100, Math.round((elapsed/duration)*100));
      area.innerHTML = `<span class="spinner"></span><span class="status-msg">Recording… ${pct}% (${Math.round(elapsed)}s/${duration}s)</span>`;
      const sr    = await fetch(`/radio_status/${_radioJobId}`);
      const sdata = await sr.json();
      if (sdata.status === 'done') {
        clearInterval(_radioPollId); btn.disabled = false;
        area.innerHTML = `<div class="success-chip">🎵 ${sdata.filename} — ${sdata.size_kb} KB</div>
          <audio controls src="${sdata.path}"></audio>
          <div class="action-row"><span>✅ ${sdata.recorded_at}</span>
          <a href="/download/recordings/${sdata.filename}" download>⬇ Download</a></div>`;
        loadHistory();
      } else if (sdata.status === 'error') {
        clearInterval(_radioPollId); btn.disabled = false;
        area.innerHTML = `<div class="error-box">❌ ${sdata.error}</div>`;
      }
    }, 1500);
  } catch(e) { area.innerHTML=`<div class="error-box">❌ ${e.message}</div>`; btn.disabled=false; }
}

async function loadHistory() {
  try {
    const res  = await fetch('/files');
    _historyData = await res.json();
    renderHistory();
  } catch(e) { document.getElementById('history-list').innerHTML='<p class="empty-msg">Could not load history.</p>'; }
}

function switchTab(tab) {
  _activeTab = tab;
  document.getElementById('tab-ss').classList.toggle('active',    tab==='screenshots');
  document.getElementById('tab-radio').classList.toggle('active', tab==='recordings');
  renderHistory();
}

function renderHistory() {
  const list  = document.getElementById('history-list');
  const items = _historyData[_activeTab] || [];
  if (!items.length) { list.innerHTML=`<p class="empty-msg">No ${_activeTab} yet.</p>`; return; }
  const cat = _activeTab==='screenshots' ? 'screenshots' : 'recordings';
  list.innerHTML = items.map(f=>`
    <div class="history-item">
      <span class="name" title="${f.name}">${f.name}</span>
      <span class="meta">${f.size_kb} KB · ${f.modified}</span>
      <a href="/download/${cat}/${f.name}" download>⬇</a>
    </div>`).join('');
}

loadHistory();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def unique_filename(prefix: str, extension: str) -> str:
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:4]
    return f"{prefix}_{ts}_{uid}.{extension}"


# ---------------------------------------------------------------------------
# Screenshot logic
# ---------------------------------------------------------------------------

def capture_screenshot(url: str, width: int = 1280, height: int = 900) -> dict:
    """
    Launches a headless Chromium browser via Playwright, navigates to `url`,
    waits for the page to fully load, captures a full-page PNG screenshot,
    saves it to ./screenshots/, and returns the filename + base64 preview.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    filename  = unique_filename("screenshot", "png")
    save_path = SCREENSHOTS_DIR / filename

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(url, timeout=20_000)
        page.wait_for_load_state("networkidle", timeout=15_000)
        page.screenshot(path=str(save_path), full_page=True)
        browser.close()

    raw_bytes  = save_path.read_bytes()
    b64_string = base64.b64encode(raw_bytes).decode("utf-8")

    return {
        "filename" : filename,
        "path"     : f"/serve/screenshots/{filename}",
        "preview"  : f"data:image/png;base64,{b64_string}",
        "taken_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Radio recording logic
# ---------------------------------------------------------------------------

_radio_jobs: dict = {}
_radio_lock = threading.Lock()


def record_radio_stream(job_id: str, stream_url: str, duration_sec: int):
    """
    Downloads `duration_sec` seconds of a streaming radio URL into a file.
    Runs in a background thread; updates _radio_jobs[job_id] with progress.
    """
    url_lower = stream_url.split("?")[0].lower()
    ext = "aac" if url_lower.endswith(".aac") else "ogg" if url_lower.endswith(".ogg") else "mp3"

    filename  = unique_filename("radio", ext)
    save_path = RECORDINGS_DIR / filename

    try:
        with _radio_lock:
            _radio_jobs[job_id]["status"] = "recording"

        response = requests.get(
            stream_url, stream=True, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 RadioRecorder/1.0"},
        )
        response.raise_for_status()

        start_time = time.monotonic()
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8_192):
                if chunk:
                    f.write(chunk)
                if time.monotonic() - start_time >= duration_sec:
                    break

        size_kb = save_path.stat().st_size // 1024
        with _radio_lock:
            _radio_jobs[job_id].update({
                "status"     : "done",
                "filename"   : filename,
                "path"       : f"/serve/recordings/{filename}",
                "size_kb"    : size_kb,
                "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    except Exception as exc:
        with _radio_lock:
            _radio_jobs[job_id].update({"status": "error", "error": str(exc)})


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    # render_template_string() renders HTML from a Python string — no file needed
    return render_template_string(HTML)


@app.route("/screenshot", methods=["POST"])
def screenshot():
    data   = request.get_json(silent=True) or {}
    url    = (data.get("url") or "").strip()
    width  = int(data.get("width")  or 1280)
    height = int(data.get("height") or 900)

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400

    try:
        result = capture_screenshot(url, width, height)
        return jsonify({"success": True, **result})
    except PWTimeout:
        return jsonify({"success": False, "error": "Page timed out. Check the URL and try again."}), 504
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "trace": traceback.format_exc()}), 500


@app.route("/radio", methods=["POST"])
def radio():
    data     = request.get_json(silent=True) or {}
    url      = (data.get("url") or "").strip()
    duration = min(int(data.get("duration") or 30), 120)

    if not url:
        return jsonify({"success": False, "error": "Stream URL is required"}), 400

    job_id = uuid.uuid4().hex[:10]
    with _radio_lock:
        _radio_jobs[job_id] = {"status": "starting", "url": url, "duration": duration}

    t = threading.Thread(target=record_radio_stream, args=(job_id, url, duration), daemon=True)
    t.start()

    return jsonify({"success": True, "job_id": job_id,
                    "message": f"Recording started for {duration}s."})


@app.route("/radio_status/<job_id>")
def radio_status(job_id: str):
    with _radio_lock:
        job = _radio_jobs.get(job_id)
    if job is None:
        return jsonify({"success": False, "error": "Unknown job ID"}), 404
    return jsonify({"success": True, **job})


@app.route("/files")
def list_files():
    def file_info(path: Path, category: str) -> dict:
        stat = path.stat()
        return {
            "name"    : path.name,
            "category": category,
            "size_kb" : stat.st_size // 1024,
            "path"    : f"/serve/{category}/{path.name}",
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
    screenshots = [file_info(p, "screenshots") for p in sorted(SCREENSHOTS_DIR.iterdir(), reverse=True) if p.is_file()]
    recordings  = [file_info(p, "recordings")  for p in sorted(RECORDINGS_DIR.iterdir(),  reverse=True) if p.is_file()]
    return jsonify({"screenshots": screenshots, "recordings": recordings})


@app.route("/serve/<category>/<filename>")
def serve_file(category: str, filename: str):
    """Serve saved files (screenshots / recordings) directly in the browser."""
    if category not in ("screenshots", "recordings"):
        abort(404)
    directory = SCREENSHOTS_DIR if category == "screenshots" else RECORDINGS_DIR
    return send_from_directory(directory, filename)


@app.route("/download/<category>/<filename>")
def download_file(category: str, filename: str):
    """Force-download a saved file."""
    if category not in ("screenshots", "recordings"):
        abort(404)
    directory = SCREENSHOTS_DIR if category == "screenshots" else RECORDINGS_DIR
    return send_from_directory(directory, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Flask Capture App  –  http://127.0.0.1:5000")
    print(f"  Screenshots → {SCREENSHOTS_DIR}")
    print(f"  Recordings  → {RECORDINGS_DIR}")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
