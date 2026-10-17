# Project Structure (structure_EN.md)

[🇰🇷 한국어 버전 (Korean)](structure.md) | [🇺🇸 English Version](structure_EN.md)

This document provides a comprehensive overview of the directory organization and module responsibilities for the Listening Monitor cross-platform audio security streaming system.

```text
zander/
├── config.py                 # Global configurations (ports, audio backend, auth, session TTL)
├── main.py                   # Application entry point (FastAPI app & Uvicorn HTTPS/WSS server)
├── structure_EN.md           # Architecture and file breakdown (this file)
├── README_EN.md              # Project overview, core features & quick-start guide
├── GUIDE_EN.md               # Operations, deployment, service setup & troubleshooting
├── requirements.txt          # Python dependencies (FastAPI, sounddevice, qrcode, etc.)
├── test_system.py            # Automated unit and integration test suite
│
├── core/                     # Backend domain logic
│   ├── __init__.py
│   ├── audio_engine.py       # Audio capture (ALSA arecord, WASAPI, DirectShow, virtual tone)
│   ├── broadcaster.py        # WSS binary chunk broadcasting & non-blocking ring buffer
│   ├── session_manager.py    # Session issuance, authentication, tracking & remote kick
│   ├── system_monitor.py     # System telemetry (CPU, RAM, temperature, uptime)
│   └── ssl_cert.py           # RSA 2048-bit TLS certificate generator & validator
│
├── routers/                  # HTTP & WebSocket route handlers
│   ├── __init__.py
│   ├── auth_router.py        # Admin login/logout, session checks, password changes
│   ├── session_router.py     # Session listing, QR code generation, kick control
│   ├── stream_router.py      # Realtime binary audio WebSocket (WSS) streaming
│   ├── system_router.py      # System telemetry & audio gain adjustment APIs
│   └── web_router.py         # Web dashboard & listener page rendering (SSR)
│
├── static/                   # Frontend static assets
│   ├── css/
│   │   └── style.css         # Dark-themed responsive dashboard styles & layout
│   └── js/
│       ├── i18n.js           # Internationalization module (Korean & English)
│       ├── audio_player.js   # Web Audio low-latency PCM player, VU meter, iOS anchor
│       └── app.js            # Admin dashboard interactivity, polling, QR rendering
│
├── templates/                # Jinja2 HTML templates
│   ├── login.html            # Admin login page (Atomic form submission)
│   ├── dashboard.html        # Integrated console (player, QR invite, session table, metrics)
│   └── listener.html         # Responsive mobile/desktop player (PWA ready)
│
├── certs/                    # TLS/SSL certificate storage (.gitignore managed)
│   ├── .gitkeep
│   ├── server.crt            # Public X.509 certificate
│   └── server.key            # Private RSA key
│
└── scripts/                  # Cross-platform installation and daemon scripts
    ├── setup.sh              # Linux / Raspberry Pi / ChromeOS setup script
    ├── setup.bat             # Windows setup script
    ├── run.bat               # Windows one-click run script
    └── listening-monitor.service # Linux systemd service unit definition
```

---

## Component Roles & Architecture Details

### 1. Root Files
- **`config.py`**: Manages environment settings, default port (443), capture driver (`auto`, `arecord`, `wasapi`, `directshow`), 16kHz PCM audio format, chunk sizes, and admin credentials.
- **`main.py`**: Configures the FastAPI app, attaches CORS and GZip middleware, mounts static files, and launches the Uvicorn server with TLS certificates.
- **`test_system.py`**: Automated end-to-end test suite verifying SSL, audio engines, session lifecycles, QR generation, and HTTP 303 form-login redirection.

### 2. Core Modules (`core/`)
- **`audio_engine.py`**: Multi-backend audio pipeline that interfaces with native hardware drivers. Falls back to a 440Hz pulsed sine wave generator when no microphone is detected.
- **`broadcaster.py`**: Asynchronously broadcasts binary PCM audio chunks to all connected WebSocket clients via bounded ring queues (`maxsize=15`), preventing lag and buffer buildup.
- **`session_manager.py`**: Handles admin and listener session lifecycles, token authentication, prevents duplicate sessions per invite token, and executes instant kick actions.
- **`ssl_cert.py`**: Self-generates a 10-year 2048-bit RSA TLS certificate with Subject Alternative Names (SAN) on startup if none exists.
- **`system_monitor.py`**: Gathers CPU usage, CPU temperature via sysfs/sensors, RAM consumption, and service uptime.

### 3. API Routers (`routers/`)
- **`auth_router.py`**: REST endpoints for admin login, logout, and credential updates with cookie management.
- **`session_router.py`**: Generates listener tokens, encodes SVG/PNG QR codes, and manages session revocation.
- **`stream_router.py`**: Secure WebSocket endpoint (`/ws/stream`) streaming 16-bit 16kHz PCM audio chunks.
- **`system_router.py`**: Exposes real-time system metrics and microphone software gain settings.
- **`web_router.py`**: Delivers Server-Side Rendered (SSR) HTML for the admin console, listener page, and handles atomic 303 login form submissions.

### 4. Static Assets & Templates (`static/`, `templates/`)
- **`style.css`**: Mobile-responsive CSS with CSS custom properties (variables) supporting dark mode.
- **`i18n.js`**: Client-side localization module facilitating instant toggling between Korean and English.
- **`audio_player.js`**: Low-latency Web Audio API player featuring an iOS background audio anchor (0.1s silent WAV loop) and MediaStreamDestination hardware output routing.
- **`app.js`**: Orchestrates client-side dashboard polling, modal dialogs, and session kick events.
