# 🛠️ Operations, Maintenance, and Development Guide (GUIDE_EN.md)

[🇰🇷 한국어 버전 (Korean)](GUIDE.md) | [🇺🇸 English Version](GUIDE_EN.md)

This comprehensive technical guide ensures consistent architecture, reliability, and deployment procedures for developers maintaining or extending Listening Monitor.

---

## 1. Architectural Principles & Design Guidelines

### 1.1 Ultra-Low Latency & Resource Efficiency
- **Minimal CPU & RAM Footprint**:
  - Engineered to run smoothly on low-power embedded single-board computers (Raspberry Pi) as well as desktop PCs and enterprise servers.
  - Avoid heavy real-time transcoding. Rely on a **single audio capture buffer distributed directly to multiple asynchronous WSS clients**.
  - Synchronous blocking loops (`while True: pass`) are strictly prohibited. Use asynchronous timers (`asyncio.sleep()`) or non-blocking queues (`asyncio.Queue`).
- **Memory Leak Prevention**:
  - Disconnected clients must be immediately purged from broadcaster sets and session maps.
  - Queues must enforce a strict `maxsize` to drop outdated chunks rather than accumulating unconsumed frames.

### 1.2 End-to-End Cryptographic Security
- **Strict TLS 1.2+ Requirement**:
  - Plaintext HTTP and unencrypted WebSocket (WS) are completely rejected. HTTPS and WSS are mandatory.
  - Even in private LAN deployments, eavesdropping is prevented by end-to-end TLS encryption.

### 1.3 Fault Tolerance & Zero-Crash Resilience
- **Microphone Disconnection Handling**:
  - Hardware failures, unplugged USB devices, or driver busy errors must never crash the server.
  - `core/audio_engine.py` automatically falls back to a 440Hz pulsed virtual test tone generator, allowing operators to diagnose hardware without restarting services.

---

## 2. Environment Setup

### 2.1 Python Environment (Python 3.8+)
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

### 2.2 System Package Prerequisites
- **Linux (Debian / Ubuntu / Raspberry Pi OS / ChromeOS Crostini)**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y alsa-utils libasound2-dev openssl
  ```
- **Windows 10/11**:
  - No external packages needed. Python 3.8+ and running `scripts\setup.bat` suffice.

### 2.3 Audio Capture Device Verification
- **Linux (ALSA)**:
  ```bash
  # Check recording hardware
  arecord -l
  ```
- **Windows**:
  ```cmd
  # Inspect sound devices via sounddevice
  python -m sounddevice
  ```

---

## 3. Configuration Parameters (`config.py`)

All core behaviors can be adjusted in `config.py` or overridden via environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SERVER_HOST` | `0.0.0.0` | Listen IP address (all interfaces) |
| `SERVER_PORT` | `443` | Service port (override with `PORT=8443`) |
| `AUDIO_CAPTURE_BACKEND` | `auto` | Driver backend: `auto`, `arecord`, `wasapi`, `directshow`, `virtual` |
| `AUDIO_DEVICE_NAME` | `default` | Audio device identifier or index |
| `AUDIO_SAMPLE_RATE` | `16000` | Sampling frequency (16kHz recommended for voice) |
| `ADMIN_USERNAME` | `admin` | Administrator login username |
| `ADMIN_PASSWORD` | `admin1234!` | Administrator master password |
| `MAX_CONCURRENT_LISTENERS`| `20` | Max simultaneous listener capacity |

---

## 4. Verification & Testing

Always execute the automated test suite before pushing or deploying modifications:

```bash
# Run full automated test suite
python3 test_system.py
```

The test validates:
1. TLS certificate creation and validation.
2. Admin authentication, listener invite generation, and QR code rendering.
3. Audio engine startup, gain amplification, and fallback tone generation.
4. Session kick, duplicate connection suppression, and immediate session cleanup.
5. System metrics telemetry and HTTP 303 form-login atomic redirection.

---

## 5. Linux Daemon Deployment (systemd)

To register and run Listening Monitor as an auto-starting system service:

```bash
# 1. Copy service unit definition
sudo cp scripts/listening-monitor.service /etc/systemd/system/

# 2. Reload daemon and enable on boot
sudo systemctl daemon-reload
sudo systemctl enable listening-monitor.service

# 3. Start service and check status
sudo systemctl start listening-monitor.service
sudo systemctl status listening-monitor.service
```

---

## 6. Troubleshooting Common Issues

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| **"Device or resource busy" (Linux)** | Another process is holding the audio device | Run `sudo fuser -v /dev/snd/*` to identify and terminate conflicting processes. |
| **No audio input on Windows** | Audio capture backend mismatch | Set `AUDIO_CAPTURE_BACKEND=wasapi` or `directshow` in `config.py` and restart. |
| **No audio on iOS Safari** | Browser autoplay security policy | The user must tap the **[Start Listening]** button to initialize the Web Audio context. |
| **Audio stops on iOS screen lock** | Background sleep throttling | The built-in 0.1s silent WAV audio anchor and MediaStream pipeline maintain background execution automatically. Simply start playback before locking the device. |
| **SSL Certificate Warning** | Self-signed certificate usage | Click **[Advanced] -> [Proceed to site]** or deploy a trusted Let's Encrypt certificate. |
