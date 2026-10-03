# 🎬 Pi Stop-Motion Workshop

Turn a Raspberry Pi + camera into a stop-motion animation studio.
Capture frames from a web UI on your phone, onion-skin the last frame,
preview at any FPS, and export to MP4.

## What you need

- Raspberry Pi 5 (4GB+ fine) with Raspberry Pi OS
- Raspberry Pi Camera Module 3 / ArduCam IMX708 (or any picamera2 camera)
- Phone or laptop on the same Wi-Fi

## Quick start (on the Pi)

```bash
git clone https://github.com/walterxiao/pi-stopmotion-workshop.git
cd pi-stopmotion-workshop
chmod +x install.sh
./install.sh
```

Then open `http://<pi-ip>:5000/` — find the IP with `hostname -I`.

## Manual run (dev)

```bash
pip install -r requirements.txt
python3 app.py
# open http://localhost:5000/
```

No camera? The app runs with a mock camera so you can develop the UI
on a laptop.

## How to animate

1. Fix the camera so it can't wobble — tripod, stack of books, tape.
2. Put your LEGO / clay / toys in frame.
3. Move the subject a *tiny* bit, hit **📸 Capture** (or Spacebar).
4. The onion-skin ghost shows the last frame — line up the next move.
5. Hit **▶ Play** to preview, adjust FPS, then **🎞 Export MP4**.

Tips: small moves = smooth motion. 12 fps is the classic look;
24 fps is buttery but twice the frames.

## API

| Method | Path | What |
|---|---|---|
| GET | `/api/projects` | list projects |
| POST | `/api/projects` | create `{name}` |
| DELETE | `/api/projects/:id` | delete project |
| GET | `/api/projects/:id/frames` | list frames |
| POST | `/api/projects/:id/capture` | capture a frame |
| DELETE | `/api/projects/:id/frames/:file` | delete a frame |
| POST | `/api/projects/:id/export` | export MP4 `{fps}` |
| GET | `/stream.mjpg` | live MJPEG preview |

## Files

- `app.py` — web server + API + MJPEG stream
- `camera.py` — picamera2 wrapper (mock fallback for dev)
- `config.yaml` — resolutions, port, export defaults
- `static/` — the workshop UI (no build step)
- `data/projects/<id>/frames/` — your captured JPEGs
- `data/projects/<id>/exports/` — exported MP4s
