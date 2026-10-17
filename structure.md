# 프로젝트 디렉토리 구조 (Project Structure)

[🇰🇷 한국어 버전 (Korean)](structure.md) | [🇺🇸 English Version](structure_EN.md)

크로스 플랫폼(Linux, Windows, ChromeOS, Raspberry Pi) 실시간 오디오 보안 스트리밍 및 모니터링 시스템의 전체 프로젝트 구조입니다.

```text
zander/
├── config.py                 # 전역 설정 (오디오, 포트, 보안, 캡처 백엔드, 세션 등 환경설정)
├── main.py                   # 애플리케이션 진입점 (FastAPI 및 HTTPS/WSS 서버 실행)
├── structure.md              # 프로젝트 구조 및 모듈 설명서 (본 파일)
├── README.md                 # 프로젝트 개요, 주요 특징 및 빠른 시작 설명서
├── GUIDE.md                  # 환경 설정, 유지보수, 백엔드 확장 및 서비스 등록 가이드
├── requirements.txt          # Python 의존 패키지 목록 (FastAPI, sounddevice, qrcode 등)
├── test_system.py            # 단위 및 통합 전체 검증 테스트 스위트
│
├── core/                     # 백엔드 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── audio_engine.py       # 오디오 캡처 (ALSA arecord, Windows WASAPI/DirectShow, 가상 톤 폴백)
│   ├── broadcaster.py        # WSS 기반 오디오 브로드캐스트 및 클라이언트 스트림 분배 (지연 방지 드롭 링버퍼)
│   ├── session_manager.py    # 세션 발급, 인증 검증, 활성 세션 추적, 원격 강제 추방(Kick) 관리
│   ├── system_monitor.py     # 호스트 시스템 CPU, RAM, 온도, 네트워크 상태 수집
│   └── ssl_cert.py           # 자체 서명 TLS/SSL 인증서 자동 생성 및 관리
│
├── routers/                  # API 엔드포인트 라우팅
│   ├── __init__.py
│   ├── auth_router.py        # 관리자 로그인, 로그아웃, 세션 검증, 비밀번호 변경 API
│   ├── session_router.py     # 세션 목록 조회, 스마트폰 QR 코드 발급, 강제 종료(Kick) 관리 API
│   ├── stream_router.py      # 실시간 오디오 스트리밍 WebSocket (WSS) 엔드포인트
│   ├── system_router.py      # 호스트 시스템 상태 및 오디오 장치/게인 설정 API
│   └── web_router.py         # 웹 관리 대시보드 및 청취자 페이지 서빙
│
├── static/                   # 프론트엔드 정적 파일
│   ├── css/
│   │   └── style.css         # 대시보드 커스텀 스타일 (반응형 다크 테마, QR 코드 카드 레이아웃)
│   └── js/
│       ├── audio_player.js   # Web Audio API 초저지연 PCM 플레이어, VU 미터, iOS 백그라운드 앵커
│       └── app.js            # 관리자 대시보드 인터랙션, 실시간 폴링, QR 코드 렌더링, 추방 제어
│
├── templates/                # 웹 대시보드 HTML 템플릿
│   ├── login.html            # 관리자 로그인 페이지
│   ├── dashboard.html        # 통합 웹 관리 콘솔 (플레이어, QR 초대 카드, 세션 관리, 시스템 정보)
│   └── listener.html         # 스마트폰/PC 반응형 청취자 전용 미니 웹 플레이어 (PWA 지원)
│
├── certs/                    # TLS/SSL 인증서 저장 디렉토리 (자동 생성 또는 사용자 등록)
│   ├── server.crt            # 서버 공개 인증서
│   └── server.key            # 서버 개인 키
│
└── scripts/                  # 크로스 플랫폼 운영 및 설치 자동화 스크립트
    ├── setup.sh              # Linux / Raspberry Pi / ChromeOS 의존성 설치 스크립트
    ├── setup.bat             # Windows 의존성 설치 스크립트
    ├── run.bat               # Windows 원클릭 서버 실행 스크립트
    ├── generate_cert.sh      # OpenSSL 인증서 수동 생성 스크립트
    └── listening-monitor.service # Linux systemd 자동 실행 서비스 등록 파일
```

---

## 각 모듈 및 파일 역할

### 1. 루트 파일
- **`config.py`**: 서버 포트(기본 443), 바인드 주소, 오디오 백엔드(`auto`/`arecord`/`wasapi`/`directshow`), 샘플레이트(16kHz), 청크 크기, JWT 비밀키, 세션 만료 시간 등 시스템 전반의 설정을 관리합니다.
- **`main.py`**: FastAPI 인스턴스를 초기화하고 미들웨어, 라우터, 오디오 엔진 라이프사이클(시작/종료)을 등록하며 Uvicorn을 통해 HTTPS/WSS 서버를 기동합니다.
- **`requirements.txt`**: FastAPI, Uvicorn, sounddevice, qrcode, cryptography, psutil 등 경량 패키지 목록을 정의합니다.

### 2. `core/` (핵심 로직 계층)
- **`audio_engine.py`**:
  - `arecord`(Linux), `WASAPI`(Windows 10/11 초저지연), `DirectShow` 중 최적의 백엔드를 자동 선택하여 16-bit PCM 데이터를 캡처합니다.
  - 마이크가 연결되어 있지 않은 환경(테스트/개발 모드)에서는 가상 테스트 사인파 톤(440Hz)을 생성하여 시스템 오류 없이 작동을 검증할 수 있도록 지원합니다.
- **`broadcaster.py`**:
  - 오디오 엔진에서 전달된 실시간 바이너리 오디오 패킷을 접속 중인 모든 인증된 WSS 세션에 비동기로 안전하게 브로드캐스트합니다.
- **`session_manager.py`**:
  - 관리자 및 청취자 세션을 메모리에서 추적합니다.
  - 관리자가 특정 세션을 강제 종료(`kick_session`)하면 즉시 해당 웹소켓 연결을 차단(`code=4001`)하고 인증을 무효화합니다.
- **`system_monitor.py`**:
  - 호스트 시스템의 CPU 점유율, 메모리 사용량, CPU 온도, 가동 시간(Uptime)을 측정합니다.
- **`ssl_cert.py`**:
  - TLS 인증서가 없으면 자체 서명(Self-Signed) 인증서를 자동 생성하여 즉시 안전한 WSS/HTTPS 통신을 지원합니다.

### 3. `routers/` (웹/API 계층)
- **`auth_router.py`**: 관리자 인증 및 세션 토큰 발급/검증/비밀번호 변경 엔드포인트를 제공합니다.
- **`session_router.py`**: 활성 세션 목록 조회, 스마트폰 카메라 스캔용 **QR 코드(SVG) 생성**, 세션 강제 추방(Kick) API를 제공합니다.
- **`stream_router.py`**: 클라이언트가 WSS로 접속하여 실시간 오디오 스트림을 수신하는 웹소켓 엔드포인트입니다.
- **`system_router.py`**: 시스템 상태 조회 및 오디오 입력 감도(볼륨 게인) 제어 API를 제공합니다.
- **`web_router.py`**: 관리자 대시보드, 로그인 및 청취자 전용 페이지를 서빙합니다.

### 4. `static/` & `templates/` (웹 UI)
- 안드로이드, iOS, 윈도우, Mac의 모든 브라우저에서 일관되게 쾌적한 관리 및 청취 경험을 제공합니다.
- **Web Audio API & iOS 백그라운드 앵커**: 무음 오디오 루프 및 MediaSession API를 내장하여 화면이 꺼져도 오디오가 끊기지 않도록 지원합니다.
