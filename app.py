#!/usr/bin/env python3
"""Pi Stop-Motion Workshop — web server.

Endpoints:
  GET  /                          -> static/index.html
  GET  /api/projects              -> [{id, name, frames, created}]
  POST /api/projects {name}      -> create project
  DELETE /api/projects/<id>      -> delete project
  GET  /api/projects/<id>/frames -> [{file, url}]
  POST /api/projects/<id>/capture -> capture frame, returns {file, url}
  DELETE /api/projects/<id>/frames/<file>
  POST /api/projects/<id>/export {fps} -> {video_url}
  GET  /stream.mjpg               -> MJPEG live preview
  GET  /data/...                  -> project files (frames, exports)

Beginner-friendly: everything is plain stdlib http.server, no frameworks.
"""
import json
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

from camera import Camera  # noqa: E402

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
DATA = ROOT / cfg["paths"]["data_dir"]
DATA.mkdir(parents=True, exist_ok=True)

cam = Camera()


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower())
    s = s.strip("-") or "untitled"
    return s[:40]


def project_dir(pid: str) -> Path:
    return DATA / "projects" / pid


def list_projects():
    out = []
    base = DATA / "projects"
    if not base.exists():
        return out
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        meta = {}
        mf = p / "meta.json"
        if mf.exists():
            try:
                meta = json.loads(mf.read_text())
            except Exception:
                pass
        frames = sorted(f.name for f in (p / "frames").glob("*.jpg")
                        ) if (p / "frames").exists() else []
        out.append({
            "id": p.name,
            "name": meta.get("name", p.name),
            "created": meta.get("created", ""),
            "frames": len(frames),
        })
    return out


def list_frames(pid: str):
    d = project_dir(pid) / "frames"
    if not d.exists():
        return []
    files = sorted(d.glob("*.jpg"))
    return [{"file": f.name,
             "url": f"/data/projects/{pid}/frames/{f.name}"} for f in files]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ---- helpers ----
    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode() or "{}")

    # ---- routing ----
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.path = "/static/index.html"
            return super().do_GET()
        if path == "/stream.mjpg":
            return self.handle_mjpeg()
        if path == "/api/projects":
            return self.send_json(list_projects())
        m = re.match(r"^/api/projects/([^/]+)/frames$", path)
        if m:
            pid = m.group(1)
            if not project_dir(pid).exists():
                return self.send_json({"error": "no such project"}, 404)
            return self.send_json(list_frames(pid))
        # /data/... static files fall through to SimpleHTTPRequestHandler
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/projects":
            body = self.read_json()
            name = body.get("name", "Untitled").strip() or "Untitled"
            base = slugify(name)
            pid = base
            i = 2
            while project_dir(pid).exists():
                pid = f"{base}-{i}"
                i += 1
            pd = project_dir(pid)
            (pd / "frames").mkdir(parents=True)
            (pd / "exports").mkdir(parents=True)
            (pd / "meta.json").write_text(json.dumps({
                "name": name,
                "created": datetime.now().isoformat(timespec="seconds"),
            }))
            return self.send_json({"id": pid, "name": name}, 201)

        m = re.match(r"^/api/projects/([^/]+)/capture$", path)
        if m:
            pid = m.group(1)
            pd = project_dir(pid)
            if not pd.exists():
                return self.send_json({"error": "no such project"}, 404)
            frames = list_frames(pid)
            nxt = len(frames) + 1
            # zero-padded so lexical sort == chronological
            fname = f"frame_{nxt:04d}.jpg"
            # avoid collision after deletes
            while (pd / "frames" / fname).exists():
                nxt += 1
                fname = f"frame_{nxt:04d}.jpg"
            dest = pd / "frames" / fname
            try:
                cam.capture_frame(dest)
            except Exception as e:
                return self.send_json({"error": str(e)[:200]}, 500)
            return self.send_json({
                "file": fname,
                "url": f"/data/projects/{pid}/frames/{fname}",
            }, 201)

        m = re.match(r"^/api/projects/([^/]+)/export$", path)
        if m:
            pid = m.group(1)
            pd = project_dir(pid)
            if not pd.exists():
                return self.send_json({"error": "no such project"}, 404)
            body = self.read_json()
            fps = int(body.get("fps",
                               cfg["export"]["default_fps"]))
            fps = max(1, min(60, fps))
            frames = sorted((pd / "frames").glob("*.jpg"))
            if not frames:
                return self.send_json({"error": "no frames to export"}, 400)
            # ffmpeg needs a sequential pattern; link into a temp dir
            tmp = pd / "exports" / "_seq"
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.mkdir(parents=True)
            for i, f in enumerate(frames, 1):
                (tmp / f"img_{i:04d}.jpg").symlink_to(f.resolve())
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = pd / "exports" / f"stopmotion_{fps}fps_{ts}.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(tmp / "img_%04d.jpg"),
                "-c:v", cfg["export"]["codec"],
                "-pix_fmt", cfg["export"]["pix_fmt"],
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                str(out),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True,
                               timeout=300)
            except FileNotFoundError:
                return self.send_json(
                    {"error": "ffmpeg not installed (sudo apt install ffmpeg)"},
                    500)
            except subprocess.CalledProcessError as e:
                return self.send_json(
                    {"error": e.stderr.decode()[-300:]}, 500)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            return self.send_json({
                "video_url": f"/data/projects/{pid}/exports/{out.name}",
                "frames": len(frames),
                "fps": fps,
            })

        return self.send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        m = re.match(r"^/api/projects/([^/]+)/frames/([^/]+)$", path)
        if m:
            pid, fname = m.group(1), m.group(2)
            if ".." in fname or "/" in fname:
                return self.send_json({"error": "bad filename"}, 400)
            f = project_dir(pid) / "frames" / fname
            if f.exists():
                f.unlink()
                return self.send_json({"deleted": fname})
            return self.send_json({"error": "not found"}, 404)
        m = re.match(r"^/api/projects/([^/]+)$", path)
        if m:
            pid = m.group(1)
            pd = project_dir(pid)
            if pd.exists():
                shutil.rmtree(pd)
                return self.send_json({"deleted": pid})
            return self.send_json({"error": "not found"}, 404)
        return self.send_json({"error": "not found"}, 404)

    def handle_mjpeg(self):
        self.send_response(200)
        self.send_header("Content-Type",
                         "multipart/x-mixed-replace; boundary=FRAME")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                jpeg = cam.get_preview_jpeg()
                self.wfile.write(b"--FRAME\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(
                    f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(0.1)  # ~10 fps preview
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass  # quiet; see systemd journal for prints


def main():
    host = cfg["server"]["host"]
    port = cfg["server"]["port"]
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Stop-motion workshop at http://{host}:{port}/  (Ctrl+C to stop)",
          flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
