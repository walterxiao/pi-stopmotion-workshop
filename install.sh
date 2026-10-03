#!/bin/bash
# Pi Stop-Motion Workshop installer — run on the Raspberry Pi.
set -e
cd "$(dirname "$0")"

echo "== Installing system packages =="
sudo apt update
sudo apt install -y python3-picamera2 python3-yaml python3-numpy \
  python3-pil ffmpeg

echo "== Python deps (venv optional) =="
# system packages cover picamera2; pip only for anything missing
pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
  pip3 install -r requirements.txt || true

echo "== Systemd service =="
sudo cp systemd/pi-stopmotion.service /etc/systemd/system/
# fix placeholder path to this checkout
sudo sed -i "s|/home/pi/pi-stopmotion-workshop|$(pwd)|g" \
  /etc/systemd/system/pi-stopmotion.service
sudo systemctl daemon-reload
sudo systemctl enable pi-stopmotion.service
sudo systemctl restart pi-stopmotion.service

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "🎬 Done! Open http://$IP:5000/ on your phone or laptop."
echo "   Logs: journalctl -u pi-stopmotion -f"
