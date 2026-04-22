# 📸 CaptureStudio

> A self-contained Flask web app that screenshots any live webpage and records internet radio streams — all from a sleek browser dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![Playwright](https://img.shields.io/badge/Playwright-Chromium-green?style=flat-square&logo=playwright)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## ✨ Features

- **🖥 Web Screenshot** — Enter any URL and capture a full-page PNG screenshot using a real headless Chromium browser. Dynamic content, JavaScript-rendered pages, and single-page apps all render correctly.
- **📻 Radio Recorder** — Paste any internet radio stream URL (.mp3 / .aac / .ogg) and record up to 2 minutes of live audio. A built-in progress bar tracks recording in real time.
- **🗂 File History** — Every screenshot and recording is saved locally and listed in the dashboard with file size, timestamp, and one-click download.
- **⚡ Single-File Deploy** — The entire app is one `app.py` file. No template folders, no static asset pipeline, no configuration files needed.

---

## 🖼 Preview

```
┌─────────────────────────────────────────────────┐
│  📸  Capture Studio                             │
│  Screenshot & Radio Recorder                    │
├──────────────────────┬──────────────────────────┤
│  🖥 Web Screenshot   │  📻 Radio Recorder       │
│                      │                          │
│  URL ____________    │  Stream URL __________   │
│  Width   Height       │  Duration (sec) ______   │
│                      │                          │
│  [ 📷 Capture ]      │  [ ⏺ Record ]           │
│                      │                          │
│  [ preview image ]   │  [ ▶ audio player ]      │
├──────────────────────┴──────────────────────────┤
│  Saved Files   [ Screenshots ] [ Recordings ]   │
│  screenshot_20240421_153012.png   45 KB  ⬇      │
│  radio_20240421_153512.mp3        320 KB ⬇      │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/CaptureStudio.git
cd CaptureStudio
```

### 2. Install dependencies

```bash
pip install flask playwright requests
python -m playwright install chromium
```

### 3. Run the app

```bash
python app.py
```

### 4. Open in browser

```
http://127.0.0.1:5000
```

That's it. No `.env` files, no databases, no configuration.

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `flask` | ≥ 3.0 | Web framework & routing |
| `playwright` | ≥ 1.44 | Headless Chromium browser for screenshots |
| `requests` | ≥ 2.31 | HTTP streaming for radio recording |

Python 3.10 or higher is required.

---

## 📁 Project Structure

```
CaptureStudio/
├── app.py              ← Entire application (Flask + HTML embedded)
├── requirements.txt    ← pip dependencies
├── screenshots/        ← Auto-created on first run
└── recordings/         ← Auto-created on first run
```

---

## 🔌 API Reference

The frontend communicates with Flask via these endpoints. You can also call them directly with any HTTP client.

### `POST /screenshot`
Capture a full-page screenshot of a URL.

**Request body (JSON):**
```json
{
  "url": "https://example.com",
  "width": 1280,
  "height": 900
}
```

**Response:**
```json
{
  "success": true,
  "filename": "screenshot_20240421_153012_a7fc.png",
  "path": "/serve/screenshots/screenshot_20240421_153012_a7fc.png",
  "preview": "data:image/png;base64,...",
  "taken_at": "2024-04-21 15:30:12"
}
```

---

### `POST /radio`
Start recording a radio stream (runs in background).

**Request body (JSON):**
```json
{
  "url": "http://stream.example.com/live.mp3",
  "duration": 30
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "f3a91c04b2",
  "message": "Recording started for 30s."
}
```

---

### `GET /radio_status/<job_id>`
Poll for recording progress. Frontend polls this every 1.5 seconds.

**Response (while recording):**
```json
{ "success": true, "status": "recording" }
```

**Response (when done):**
```json
{
  "success": true,
  "status": "done",
  "filename": "radio_20240421_153512_b2c1.mp3",
  "path": "/serve/recordings/radio_...",
  "size_kb": 320,
  "recorded_at": "2024-04-21 15:35:12"
}
```

---

### `GET /files`
List all saved screenshots and recordings.

### `GET /download/<category>/<filename>`
Force-download a saved file (`category` = `screenshots` or `recordings`).

---

## ⚙️ How It Works

### Screenshot Engine
Playwright launches a real headless Chromium browser (same engine as Google Chrome). It navigates to the target URL, waits for all JavaScript and network requests to settle (`networkidle` state), then captures the entire page — including content below the fold — as a PNG. The result is base64-encoded and sent back to the browser as an inline data URI for instant preview.

### Radio Recorder
Internet radio stations serve an infinite HTTP stream. The app opens the connection with `requests.get(..., stream=True)` so the response body is never fully buffered in memory. It reads 8 KB chunks at a time, writing each to a file, and stops when the wall-clock duration is reached. Recording happens in a daemon thread so Flask stays responsive throughout.

### Single-File Architecture
`render_template_string()` is used instead of `render_template()`, which means the HTML dashboard lives as a Python string inside `app.py`. No `templates/` folder is required — you can drop the single file anywhere and run it.

---

## 🛠 Troubleshooting

**`TemplateNotFound: index.html`**
You are running an older version of the app. Replace `app.py` with the latest version — the HTML is now embedded and no `templates/` folder is needed.

**`playwright._impl._errors.Error: Executable doesn't exist`**
Run the browser installer: `python -m playwright install chromium`

**Screenshot shows a blank or partial page**
Some heavy sites take longer to load. The app waits up to 20 seconds, but very slow pages may still time out. Try again or use a simpler URL.

**Radio recording saves 0 KB file**
The stream URL may require authentication, use HTTPS with a self-signed cert, or serve a playlist file (`.m3u` / `.pls`) rather than a direct audio stream. Use the direct stream URL, not the playlist.

---

## 🗺 Roadmap

- [ ] Scheduled / recurring screenshots
- [ ] Screenshot diff comparison (before vs after)
- [ ] ZIP export of all saved files
- [ ] Dark / light theme toggle
- [ ] Docker support

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙌 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

*Built with Flask, Playwright, and a lot of ☕*
