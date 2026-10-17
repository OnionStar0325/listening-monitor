# 🎙️ Listening Monitor (크로스 플랫폼 실시간 오디오 보안 스트리밍 & 모니터링 시스템)

[🇰🇷 한국어 버전 (Korean)](README.md) | [🇺🇸 English Version](README_EN.md)

라즈베리파이, Linux, Windows, ChromeOS 등 다양한 호스트 시스템에서 마이크 입력을 캡처하여 **안드로이드, iOS, 윈도우, 웹 브라우저**로 초저지연 실시간 스트리밍하고, 안전한 암호화 통신(WSS/HTTPS)과 세션 제어 및 QR 코드 연동 기능을 제공하는 모니터링 솔루션입니다.

---

## 🌟 주요 특징

1. **초저지연 실시간 오디오 송출 (WSS + Web Audio API)**
   - WSS(WebSocket Secure) 프로토콜 기반 바이너리 PCM 16-bit 오디오 스트리밍
   - 버퍼링을 최소화하여 100~200ms 수준의 초저지연(Ultra-low latency) 실시간 청취 지원
   - **크로스 플랫폼**: 별도 전용 앱 설치 없이 안드로이드(Chrome), iOS(Safari), 윈도우/맥(Chrome/Edge) 모든 기기에서 웹 브라우저로 즉시 청취 가능
   - **iOS 백그라운드 재생 최적화**: 무음 오디오 앵커 및 MediaSession API 연동으로 아이폰 화면이 꺼지거나 잠겨도 소리 지속 재생

2. **종단간 보안 프로토콜 (TLS/SSL 암호화)**
   - 모든 웹 통신(HTTPS) 및 오디오 스트림(WSS)에 최신 TLS 암호화 적용
   - 최초 실행 시 **자체 서명(Self-Signed) SSL 인증서 자동 생성** 기능 내장
   - 공인 SSL 인증서(Let's Encrypt 등)로 손쉬운 교체 지원

3. **강력한 실시간 세션 관리 & 스마트폰 QR 코드 연동**
   - 관리자 비밀번호 인증 및 청취자용 일회용/기간제 세션 토큰 발급
   - **스마트폰 QR 코드 즉시 생성**: 관리자 대시보드에서 초대 생성 시 카메라로 스캔 가능한 SVG QR 코드 자동 렌더링
   - 현재 접속 중인 모든 세션의 실시간 모니터링 (IP 주소, 디바이스/User-Agent, 연결 시간, 청취 상태)
   - 웹 관리자 콘솔에서 특정 접속자 **실시간 강제 추방(Kick)** 및 소켓 차단 기능

4. **웹 기반 통합 관리 대시보드**
   - 모바일, 태블릿, 데스크탑에 최적화된 모던 반응형 웹 UI
   - **실시간 오디오 플레이어**: 재생/일시정지, 볼륨 조절, VU 미터 및 실시간 파형 시각화
   - **호스트 시스템 상태 모니터링**: CPU 점유율, RAM 사용량, CPU 온도, 네트워크 상태 실시간 표시
   - **오디오 드라이버 다중 백엔드 지원**:
     - `arecord`: Linux / Raspberry Pi ALSA 전용 경량 백엔드
     - `WASAPI`: Windows 10/11 초저지연 오디오 세션 API
     - `DirectShow`: Windows DirectSound 호환 백엔드
     - `auto`: OS 환경에 따른 최적 드라이버 자동 선택
     - 마이크 미연결 시 시스템 다운을 방지하는 440Hz 가상 테스트 톤 자동 폴백

5. **초경량 저부하 설계**
   - Python 비동기 이벤트 루프(FastAPI/Asyncio) 기반 설계로 임베디드 기기부터 일반 PC까지 최소한의 CPU/RAM 점유율 유지

---

## 📋 시스템 및 하드웨어 요구사항

- **지원 운영체제**: Linux (Ubuntu, Debian, Raspberry Pi OS), Windows 10/11, ChromeOS (Linux 개발 환경)
- **오디오 입력**: USB 마이크, 내장 마이크, USB 사운드카드, I2S 마이크 모듈 등
  > 💡 **참고**: 마이크가 연결되어 있지 않은 환경에서도 시스템이 정상 구동되며, '가상 테스트 톤' 모드로 소리 송출/재생을 검증할 수 있습니다.
- **네트워크**: 유선 이더넷 또는 Wi-Fi 연결

---

## 🚀 빠른 시작 가이드 (Quick Start)

### A. Linux / ChromeOS / 라즈베리파이 환경
```bash
# 1. 원클릭 자동 설정 스크립트 실행 (apt 필수 패키지 및 venv 자동 구성)
./setup.sh
# (또는 bash scripts/setup.sh)

# 2. 서버 실행 (기본 8443 포트)
./run.sh
# (또는 python3 main.py)
```
> 💡 **크롬북(ChromeOS) 마이크 설정**: 크롬북 내장 마이크를 사용하시려면 `ChromeOS 설정 > 고급 > 개발자 > Linux 개발 환경 > 마이크 액세스 허용` 토글을 활성화하세요. (마이크 미인식 시에도 가상 톤 모드로 정상 동작합니다)

### B. 윈도우 (Windows 10/11) 환경
```cmd
:: 1. 의존성 설치
scripts\setup.bat

:: 2. 서버 실행 (기본 8443 포트 및 WASAPI 마이크 자동 선택)
scripts\run.bat
```

> 최초 실행 시 `certs/` 디렉토리에 SSL 인증서(`server.crt`, `server.key`)가 자동 생성되며, `https://<서버-IP>:<포트>` 로 보안 서버가 시작됩니다.

---

## 📱 스마트폰(Android/iOS) 청취 방법

1. 관리자 대시보드(`https://<서버-IP>:<포트>`)에 로그인합니다. (기본: `admin` / `admin1234!`)
2. [청취자 초대 & QR 코드 발급] 영역에서 사용자 이름을 입력하고 **[초대 생성]**을 클릭합니다.
3. 화면에 표시된 **QR 코드를 스마트폰 기본 카메라로 스캔**하거나, 링크 URL을 전달합니다.
4. 스마트폰 브라우저에서 **[청취 시작하기]**를 누르면 실시간 소리가 즉시 스트리밍됩니다.
   - iOS의 경우 화면을 잠그거나 다른 앱을 켜도 백그라운드에서 오디오가 지속 재생됩니다.

---

## 🔒 보안 및 세션 동작 원리

```text
[클라이언트 기기 (스마트폰/PC)]             [호스트 서버 (Linux/Windows)]
          |                                              |
          |------- 1. QR 스캔 또는 초대 URL 접속 ---------->| (토큰 검증 및 세션 생성)
          |                                              |
          |<====== 2. WSS 암호화 오디오 스트림 수신 =======| (16-bit PCM 바이너리 전송)
          |                                              |
      [관리자]                                           |
          |------- 3. 특정 세션 추방(Kick) 요청 ---------->| (세션 무효화 & 소켓 즉시 종료)
          |<xxxxxx 4. 해당 클라이언트 즉시 연결 차단
```

---

## ⚙️ 주요 설정 (`config.py`)

- `SERVER_HOST`: 서버 바인드 IP (기본값: `0.0.0.0`)
- `SERVER_PORT`: 서비스 포트 (기본값: `443`, 환경변수 `PORT`로 변경 가능)
- `AUDIO_CAPTURE_BACKEND`: 오디오 캡처 장치 백엔드
  - `auto`: Linux는 `arecord`, Windows는 `WASAPI` 자동 선택 (기본값)
  - `arecord`: Linux ALSA 전용 저부하 캡처
  - `wasapi`: Windows WASAPI (Windows 10/11 초저지연 오디오 표준)
  - `directshow`: Windows DirectSound / DirectShow 호환 모드
- `AUDIO_DEVICE_NAME`: 특정 마이크 장치명 또는 번호 (기본값: `default`)
- `AUDIO_SAMPLE_RATE`: 오디오 샘플레이트 (기본값: `16000` Hz)
- `AUDIO_CHANNELS`: 채널 수 (기본값: `1` Mono)
- `SESSION_EXPIRE_MINUTES`: 세션 유효 시간 (기본값: `1440`분 = 24시간)
- `ADMIN_PASSWORD`: 관리자 비밀번호 (기본값: `admin1234!`)

---

## 📖 문서 링크

- [프로젝트 구조 상세 안내 (structure.md)](./structure.md)
- [개발, 유지보수 및 서비스 등록 가이드 (GUIDE.md)](./GUIDE.md)
