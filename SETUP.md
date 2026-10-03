# Setup guide — Pi Stop-Motion Workshop

Plain-English steps, first-time-Pi-user friendly.

## 1. What goes where

- The Pi does the work: camera + web server.
- Your phone is the remote: viewfinder, capture button, timeline.

## 2. Install the OS (if fresh)

Use Raspberry Pi Imager → Raspberry Pi OS (64-bit) → write to microSD.
Boot, connect to Wi-Fi, open a terminal.

## 3. Camera install

1. Power the Pi **off**.
2. Find the slot labeled **CAMERA** (between HDMI and audio jack on Pi 5).
3. Lift the latch gently, slide the ribbon in with the **blue side facing
   the Ethernet port**, press the latch back down.
4. Power on, then: `rpicam-hello -t 5s` — you should see a preview.
   If not, re-seat the cable (most common fix).

## 4. Install the workshop

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/walterxiao/pi-stopmotion-workshop.git
cd pi-stopmotion-workshop
chmod +x install.sh
./install.sh
```

## 5. Open the studio

On your phone (same Wi-Fi), open `http://<pi-ip>:5000/`.
Get the IP on the Pi with `hostname -I`.

## 6. Workshop tips

- **Lock the camera down.** Any bump ruins the shot.
- **Lock exposure.** Bright rooms with auto-exposure cause flicker —
  if you see flicker, add a lamp and keep lighting constant.
- **Onion skin** is your best friend: the ghost of the last frame
  shows exactly how far things moved.
- Start at **12 fps**, 5 seconds = 60 frames. Kids love seeing
  the first playback — export early and often.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `rpicam-hello` fails | re-seat ribbon cable, blue side to Ethernet |
| Stream is black | `journalctl -u pi-stopmotion -f` — check for camera errors |
| Export fails | `sudo apt install -y ffmpeg` then restart service |
| Can't reach `:5000` | phone on same Wi-Fi? `sudo systemctl status pi-stopmotion` |
