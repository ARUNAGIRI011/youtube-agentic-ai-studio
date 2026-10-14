#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

# Run this script inside Termux from the cloned repository:
#   bash scripts/setup_android_termux.sh
# Recommended: install Termux from F-Droid or its official GitHub releases.

if [[ -z "${PREFIX:-}" || "${PREFIX}" != *com.termux* ]]; then
  echo "Run this inside Termux on Android, not Windows/Linux."
  exit 1
fi

cd "$(dirname "$0")/.."

echo "== Installing Android/Termux system packages =="
pkg update -y
pkg upgrade -y
pkg install -y python ffmpeg git clang make cmake rust pkg-config \
  libjpeg-turbo freetype libpng libxml2 libxslt openssl libffi

echo "== Installing Python dependencies =="
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Edit it and add GEMINI_API_KEY."
fi

mkdir -p output "music library"

echo
echo "Setup completed. Before running the workflow:"
echo "  1. Edit .env and add your Gemini API key."
echo "  2. Start the studio with: python gui.py"
echo "  3. Open http://127.0.0.1:7070 in Chrome on this Android device."
echo
echo "Android video rendering is experimental and may fail or be slow on some devices."
echo "Keep Termux open and disable battery optimization while a render is running."
