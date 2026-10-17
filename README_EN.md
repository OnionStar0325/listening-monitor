# 🎙️ Listening Monitor (Cross-Platform Realtime Audio Security Streaming & Monitoring System)

[🇰🇷 한국어 버전 (Korean)](README.md) | [🇺🇸 English Version](README_EN.md)

Listening Monitor captures microphone audio on diverse host systems including **Linux, Windows, ChromeOS, and Raspberry Pi**, streaming it with ultra-low latency to **Android, iOS, Windows, and Web browsers**. It features end-to-end encrypted transmission (WSS/HTTPS), granular session management, and smartphone camera QR code integration.

---

## 🌟 Key Features

1. **Ultra-Low Latency Realtime Streaming (WSS + Web Audio API)**
   - Binary PCM 16-bit 16kHz audio streaming over WebSocket Secure (WSS).
   - Near-instantaneous listening with 100~200ms latency without buffering delays.
   - **Cross-Platform**: No dedicated app required. Listens directly on Android (Chrome), iOS (Safari), Windows/macOS (Chrome/Edge/Safari) via any standard web browser.
   - **iOS Background Playback**: Integrated 0.1s silent WAV loop anchor and MediaSession API support ensure continuous audio playback even when the iPhone screen is turned off or locked.

2. **End-to-End Encryption (TLS/SSL Security)**
   - All HTTP web interfaces and WSS audio streams are encrypted with TLS/SSL.
   - Built-in **automatic self-signed certificate generator** for immediate zero-config setup.
   - Supports seamless replacement with commercial or Let's Encrypt certificates.

3. **Session Management & Smartphone QR Code Integration**
   - Admin password authentication and listener token generation with customizable expiration.
   - **Instant QR Code Generation**: Generates SVG and PNG QR codes on-the-fly upon invite creation, allowing quick scanning with smartphone cameras.
   - Real-time tracking of active sessions (IP address, client device/User-Agent, connection duration, streaming status).
   - Remote **instant kick (force disconnect)** and token revocation from the admin console.

4. **Web-Based Unified Admin Dashboard**
   - Modern, responsive web UI optimized for mobile, tablet, and desktop displays.
   - **Realtime Web Audio Player**: Play/Pause, volume slider, VU meter frequency spectrum visualizer.
   - **Host System Monitoring**: Realtime CPU usage, RAM utilization, CPU temperature, and system uptime.
   - **Multiple Audio Capture Backends**:
     - `arecord`: Lightweight native Linux ALSA backend.
     - `WASAPI`: Low-latency Windows 10/11 Audio Session API.
     - `DirectShow`: Windows DirectSound compatible backend.
     - `auto`: Automatically detects and selects the best driver for the host OS.
     - Automatic fallback to 440Hz virtual test tone generator if no microphone hardware is connected.

5. **Ultra-Lightweight & High-Performance Design**
   - Powered by Python Asyncio and FastAPI event loop, maintaining minimal CPU/memory footprint on low-spec hardware and modern PCs alike.

---

## 📋 System Requirements

- **Supported OS**: Linux (Ubuntu, Debian, Raspberry Pi OS), Windows 10/11, ChromeOS (Linux environment / Crostini)
- **Audio Input**: USB Microphone, Built-in Laptop/PC Mic, USB Sound Card, I2S Mic Module
  > 💡 **Note**: The system operates normally even without a physical microphone by falling back to the 'Virtual Test Tone' generator.
- **Network**: Wired Ethernet or Wi-Fi connectivity

---

## 🚀 Quick Start Guide

### A. Linux / ChromeOS (Crostini)
```bash
# 1. Run automated setup script (installs apt packages & sets up venv)
./setup.sh
# (or bash scripts/setup.sh)

# 2. Launch server (Default port: 8443)
./run.sh
# (or python3 main.py)
```
> 💡 **Chromebook (ChromeOS) Mic Setup**: To capture the built-in microphone on ChromeOS, go to `Settings > Advanced > Developers > Linux development environment` and turn on **"Allow Linux to access your microphone"**. (If no mic is found, virtual tone mode will activate automatically)

### B. Windows 10/11
```cmd
:: 1. Run automated setup script
scripts\setup.bat

:: 2. Start server
scripts\run.bat
```

---

## 🌐 Web Console Access

Open your web browser and navigate to:
```text
https://<SERVER_IP>:443/
(or https://<SERVER_IP>:8443/ if custom port was set)
```

* **Default Admin Username**: `admin`
* **Default Admin Password**: `admin1234!` (Can be changed in the dashboard or via `config.py` / environment variable)
* *Note*: When accessing via self-signed certificates, click **[Advanced] -> [Proceed]** to bypass the initial browser warning.

---

## 📱 Listening on Mobile / Inviting Users

1. Log in to the Admin Dashboard.
2. In the **"Invite Listeners & Issue QR Code"** panel, enter a client name (e.g., `Living Room Tablet`, `iPhone`) and click **[Create Invite]**.
3. Scan the generated QR code with your smartphone camera, or copy and send the invite URL.
4. On the listener page, tap **[▶ Start Listening]** to receive audio instantly.
   * *iOS Note*: You can turn off the screen or lock the phone; audio will continue playing uninterrupted.

---

## 📂 Project Structure

```text
zander/
├── config.py              # Central configuration (Ports, Audio, SSL, Auth)
├── main.py                # FastAPI app lifecycle & Uvicorn HTTPS server
├── core/
│   ├── audio_engine.py    # Multi-backend audio capture (arecord, WASAPI, etc.)
│   ├── broadcaster.py     # Binary WSS real-time audio chunk broadcaster
│   ├── session_manager.py # Session lifecycle, token authentication & kick
│   ├── ssl_cert.py        # Automatic RSA 2048-bit TLS certificate generation
│   └── system_monitor.py  # System telemetry (CPU, RAM, Temp, Uptime)
├── routers/               # API & Web routes (auth, session, stream, system)
├── static/                # CSS, JS (Audio player, Dashboard, i18n)
├── templates/             # Jinja2 templates (login, dashboard, listener)
├── scripts/               # Linux systemd service & Windows batch scripts
├── GUIDE_EN.md            # In-depth administration guide
└── test_system.py         # Full automated verification test suite
```

---

## 🧪 Automated Testing

Run the end-to-end verification suite:
```bash
python3 test_system.py
```

---

## 📄 License
This project is licensed under the MIT License.
