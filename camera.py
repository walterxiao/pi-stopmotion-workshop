#!/usr/bin/env python3
"""Camera wrapper: picamera2 on Pi, synthetic fallback for dev."""
import io
import threading
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def load_config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


class Camera:
    def __init__(self):
        self.cfg = load_config()["camera"]
        self._picam = None
        self._lock = threading.Lock()
        self._init()

    def _init(self):
        try:
            from picamera2 import Picamera2
            w, h = self.cfg["resolution"]
            pw, ph = self.cfg["preview_resolution"]
            self._picam = Picamera2()
            # Still config for captures, video config for preview stream
            self._picam.configure(self._picam.create_still_configuration(
                main={"size": (w, h)}))
            self._picam.start()
            time.sleep(1.5)
            if self.cfg.get("autofocus"):
                try:
                    from libcamera import controls
                    self._picam.set_controls(
                        {"AfMode": controls.AfModeEnum.Continuous})
                    print("camera: continuous autofocus on", flush=True)
                except Exception as e:
                    print(f"camera: autofocus unavailable ({e})", flush=True)
            print(f"camera: picamera2 ready {w}x{h}", flush=True)
        except Exception as e:
            print(f"camera: picamera2 not available ({e}), using mock",
                  flush=True)
            self._picam = None

    def capture_frame(self, dest: Path):
        """Capture a full-res still to dest."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self._picam:
                self._picam.capture_file(str(dest))
            else:
                # Mock: generate a placeholder image with timestamp
                self._mock_image(dest, full=True)
        return dest

    def get_preview_jpeg(self) -> bytes:
        """Return a JPEG byte string for the MJPEG stream."""
        with self._lock:
            if self._picam:
                import io as _io
                buf = _io.BytesIO()
                # fast preview: capture array then encode via PIL/OpenCV
                # Use capture_file to a memory buffer at lower res is
                # expensive to reconfigure, so we downscale the array.
                try:
                    import numpy as np
                    from PIL import Image
                    arr = self._picam.capture_array()
                    img = Image.fromarray(arr)
                    pw, ph = self.cfg["preview_resolution"]
                    img = img.resize((pw, ph))
                    out = _io.BytesIO()
                    img.save(out, format="JPEG",
                             quality=self.cfg.get("jpeg_quality", 80))
                    return out.getvalue()
                except Exception:
                    pass
            # mock fallback
            buf = io.BytesIO()
            self._mock_bytes(buf)
            return buf.getvalue()

    # ---- mock helpers (dev on non-Pi machines) ----
    def _mock_image(self, dest: Path, full=False):
        from PIL import Image, ImageDraw
        import datetime
        w, h = self.cfg["resolution"] if full else self.cfg[
            "preview_resolution"]
        img = Image.new("RGB", (w, h), (30, 30, 40))
        d = ImageDraw.Draw(img)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        d.text((w//2-60, h//2-10), f"MOCK CAM {ts}", fill=(200, 200, 200))
        img.save(dest, "JPEG",
                 quality=self.cfg.get("jpeg_quality", 85))

    def _mock_bytes(self, buf: io.BytesIO):
        from PIL import Image
        import datetime
        pw, ph = self.cfg["preview_resolution"]
        # simple animated placeholder so the stream looks alive
        t = int(time.time() * 2) % 256
        img = Image.new("RGB", (pw, ph), (t % 256, 80, 120))
        img.save(buf, format="JPEG")
        buf.seek(0)
