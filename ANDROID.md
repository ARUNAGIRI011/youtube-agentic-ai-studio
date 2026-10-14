# Android support

AI Vidro supports two Android workflows. The UI is responsive for phone-sized screens and can be installed as a Progressive Web App (PWA) when served from a secure context. The video workflow requires a running Python/FFmpeg backend.

## Option A — Run the whole workflow on Android (experimental)

This runs the Flask UI and attempts to run research, script generation, narration, image downloads, rendering, review, and optional upload directly on the Android device using Termux.

1. Install **Termux** from its official F-Droid distribution or official GitHub releases. Do not use an outdated Play Store build.
2. Open Termux and run:

   ```bash
   pkg update -y
   pkg install -y git
   git clone https://github.com/ARUNAGIRI011/youtube-agentic-ai-studio.git
   cd youtube-agentic-ai-studio
   git checkout feature/free-stock-providers
   bash scripts/setup_android_termux.sh
   ```

3. Edit the local `.env` file and set `GEMINI_API_KEY`. `PIXABAY_API_KEY` is optional; Openverse is the no-key fallback.
4. Start the app:

   ```bash
   python gui.py
   ```

5. Open **http://127.0.0.1:7070** in Chrome on the same phone. Keep Termux running in the foreground or configure its battery settings so Android does not stop the render process.

### Android rendering limits

On-device rendering is experimental. MoviePy, NumPy, Pillow, FFmpeg, and Edge TTS dependencies can vary by Android/Termux/Python version; rendering long videos may be slow or exceed available RAM/storage. The setup script installs dependencies but cannot guarantee that every dependency builds on every device. Start with a short video to validate the device before attempting a long render. If a dependency fails, use Option B.

## Option B — Android UI, Windows rendering (recommended)

This gives the phone the full dashboard workflow while the Windows PC performs the resource-intensive work.

1. On Windows, install Python 3.10+, FFmpeg, and the project requirements as described in [SETUP.md](SETUP.md).
2. In the local `.env` file, set `AI_VIDRO_HOST=0.0.0.0`, then run `python gui.py`.
3. Keep the phone and PC on the same trusted Wi-Fi network. If Windows Firewall prompts, allow Python on **Private networks only**.
4. Run `ipconfig` on Windows and open `http://PC-LAN-IP:7070` in the Android browser.

**Security:** this dashboard does not implement user login. Never expose it to the public internet, use port forwarding, or connect from an untrusted network. For access outside your home network, put it behind a properly authenticated HTTPS deployment rather than exposing the Flask development server.

## Install the dashboard on Android

When using `http://127.0.0.1:7070` on the same phone or a proper HTTPS deployment, Chrome may offer **Install app** / **Add to Home screen**. LAN IP addresses over plain HTTP generally do not qualify as secure contexts for PWA installation, but the responsive web UI still works in the browser. The PWA shell may show a cached page offline; generation, settings, logs, and uploads require the backend and network connection.

## Current status

- Responsive mobile layout, touch-sized controls, and portrait/landscape layouts.
- PWA manifest and service worker for installable app-shell behavior in supported secure contexts.
- Same-origin API workflow for research, script, image search, narration, video render, review, and upload.
- Android Termux setup helper for attempting on-device execution.
- No Android-specific performance guarantee; validate with a short test render.
