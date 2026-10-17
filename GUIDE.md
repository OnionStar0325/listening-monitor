# 🛠️ 개발, 유지보수 및 운영 가이드 (GUIDE.md)

본 문서는 다른 세션이나 다른 개발자가 프로젝트를 수정, 확장, 유지보수하더라도 **동일한 아키텍처 원칙과 실행 결과를 보장**할 수 있도록 작성된 종합 기술 지침서입니다.

---

## 1. 아키텍처 원칙 및 설계 가이드라인

### 1.1 저지연 & 저부하 자원 최적화 원칙
- **CPU 및 메모리 부하 최소화**:
  - 임베디드 기기(라즈베리파이 등)부터 일반 PC/서버까지 원활히 구동되도록 설계되었습니다.
  - 무거운 실시간 비디오 인코딩이나 복잡한 다중 트랜스코딩을 지양하고, **단일 캡처 버퍼 -> 다중 WSS 브로드캐스트** 구조를 유지해야 합니다.
  - CPU를 지속적으로 소모하는 동기식 블로킹 루프(`while True: pass`)를 절대 사용하지 말고, 반드시 `asyncio.sleep()` 또는 비동기 큐(`asyncio.Queue`)를 사용하십시오.
- **메모리 누수 방지**:
  - 연결이 끊어진 웹소켓 클라이언트는 브로드캐스트 리스트에서 즉시 제거되어야 합니다.
  - 오디오 버퍼 큐는 무한정 누적되지 않도록 `maxsize`를 설정하고, 오래된 청크는 드롭(Drop) 정책을 취해야 합니다.

### 1.2 보안 통신 원칙
- **TLS 1.2+ 전용 통신**:
  - 일반 HTTP 및 WS(비암호화 웹소켓)는 허용하지 않으며, 모든 라우팅과 스트림은 HTTPS와 WSS를 강제합니다.
  - 내부 로컬망 통신이라도 음성 데이터 도청을 방지하기 위해 SSL 인증서를 필수로 적용합니다.

### 1.3 무중단/내결함성(Fault Tolerance) 원칙
- **마이크 미연결 안전 처리**:
  - 실제 마이크가 꽂혀있지 않거나 사운드 드라이버 초기화에 실패하더라도 서버 프로세스가 다운(Crash)되어서는 안 됩니다.
  - `core/audio_engine.py`는 오디오 장치 인식 실패 시 자동으로 **가상 톤(Sine Wave Generator)** 모드로 폴백하여 관리자가 웹에서 상태를 확인하고 장치를 재연결할 수 있도록 해야 합니다.

---

## 2. 개발 및 실행 환경 설정

### 2.1 개발 환경 (Python 3.8+)
```bash
# 1. 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 필수 라이브러리 설치
pip install -r requirements.txt
```

### 2.2 시스템 패키지 요구사항
- **Linux / Raspberry Pi / ChromeOS**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y alsa-utils libasound2-dev openssl
  ```
- **Windows**:
  - 별도 시스템 패키지 불필요 (Python 3.8+ 설치 및 `scripts\setup.bat` 실행)

### 2.3 오디오 입력 장치 확인 및 설정
- **Linux (ALSA)**:
  ```bash
  # 녹음 가능 장치 목록 조회
  arecord -l
  ```
- **Windows**:
  - Windows 사운드 설정 또는 `python -m sounddevice` 명령어로 장치 목록 및 인덱스 확인 가능

---

## 3. 핵심 모듈별 동작 원리 및 확장 가이드

### 3.1 오디오 엔진 (`core/audio_engine.py`)
- **역할**: 설정된 백엔드(`arecord`, `WASAPI`, `DirectShow`, `auto`)에 따라 마이크에서 16-bit PCM 데이터를 읽어 비동기 스트림 버퍼에 공급합니다.
- **백엔드별 특성**:
  - **`arecord` (Linux / Raspberry Pi ALSA)**: 별도 C 컴파일 라이브러리 없이 커널의 ALSA 장치를 가장 가볍게 직결 캡처.
  - **`wasapi` (Windows Audio Session API)**: Windows 10/11 환경에서 오디오 하드웨어와 직접 통신하여 10ms 이하의 캡처 버퍼 레이턴시를 제공하는 초저지연 표준 백엔드.
  - **`directshow` (Windows DirectSound/MME)**: 구형 윈도우 사운드 카드 또는 가상 오디오 케이블(VB-Cable 등)과의 폭넓은 호환성을 제공하는 백엔드.
  - **안전 폴백(Sine Wave)**: 마이크가 연결되어 있지 않거나 장치 충돌 시 자동으로 440Hz 가상 테스트 톤으로 전환되어 무중단 서비스 유지.

### 3.2 세션 매니저 (`core/session_manager.py`) & QR 코드
- **역할**: 클라이언트의 로그인 및 세션 생명주기를 관리합니다.
- **초대 링크 및 QR 코드 연동**:
  - `session_router.py`에서 초대 생성 시 순수 파이썬(`qrcode`)으로 벡터 SVG QR 코드를 즉시 생성하여 관리자 화면에 표출합니다.
  - 스마트폰 사용자는 카메라로 QR 코드를 스캔하여 별도 타이핑 없이 즉시 청취 화면에 진입합니다.
- **추방 처리 로직**:
  - `session_manager.kick(session_id)` 호출 시 세션 상태가 `REVOKED`로 변경되며, `broadcaster`에 등록된 해당 세션의 웹소켓 연결이 `code=4001, reason="Kicked by admin"`으로 즉시 닫힙니다.

### 3.3 프론트엔드 오디오 플레이어 (`static/js/audio_player.js`)
- 브라우저의 `window.AudioContext`를 사용하여 수신된 16-bit PCM 바이너리 패킷을 Float32 버퍼로 변환 후 갭리스(Gapless) 스케줄링 재생합니다.
- **iOS / 모바일 백그라운드 및 화면 꺼짐 유지 메커니즘**:
  1. **무음 오디오 앵커(Silent Keep-Alive Loop)**: 초경량 1초짜리 무음 WAV를 `<audio loop playsinline>` 요소로 동시 재생시켜 iOS WebKit이 이 탭을 "활성 미디어 탭"으로 인식하게 함으로써 화면이 꺼지거나 잠겨도 Web Audio API와 WSS 프로세스가 일시 중단(Suspended)되지 않도록 방지합니다.
  2. **Media Session API**: `navigator.mediaSession`을 등록하여 iOS/Android 잠금 화면 및 제어 센터에 재생 컨트롤을 띄워 시스템 절전 정책을 우회합니다.
  3. **Visibility State 자동 복구**: `visibilitychange` 이벤트를 통해 사용자가 화면을 다시 켜거나 잠금 해제할 때 일시 중지된 AudioContext를 즉시 `resume()` 처리합니다.

---

## 4. 테스트 및 검증 절차

코드 변경 후에는 다음 테스트 스위트를 반드시 실행하여 검증하십시오:

```bash
python3 test_system.py
```
- SSL 인증서 자동 생성 및 로드
- 세션 발급, 토큰 인증, 강제 추방(Kick) 생명주기
- 오디오 엔진 및 가상 톤 폴백
- 스마트폰 QR 코드 SVG 생성 및 엔드포인트 응답
- 호스트 시스템 메트릭 수집 및 웹 대시보드 렌더링

---

## 5. Linux 서비스 자동 등록 (systemd)

서버가 재부팅되어도 백그라운드에서 자동으로 시스템이 실행되도록 등록하는 절차입니다:

```bash
# 1. 서비스 설정 파일 복사
sudo cp scripts/listening-monitor.service /etc/systemd/system/

# 2. 서비스 데몬 리로드 및 활성화
sudo systemctl daemon-reload
sudo systemctl enable listening-monitor.service

# 3. 서비스 시작 및 상태 확인
sudo systemctl start listening-monitor.service
sudo systemctl status listening-monitor.service
```

---

## 6. 트러블슈팅 (자주 발생하는 문제 및 해결책)

| 현상 | 원인 | 해결 방법 |
| :--- | :--- | :--- |
| **"Device or resource busy" 오류 (Linux)** | 다른 프로세스가 마이크 장치를 점유 중 | `sudo fuser -v /dev/snd/*` 명령어로 점유 프로세스 확인 후 종료 |
| **Windows 마이크 소리 안 들어옴** | `config.py`의 캡처 백엔드 불일치 | `AUDIO_CAPTURE_BACKEND=wasapi` 또는 `directshow`로 변경 후 재실행 |
| **iOS에서 소리가 나오지 않음** | iOS Safari의 자동 재생 차단 정책 | 웹 화면의 [청취 시작하기] 버튼을 반드시 탭하여 AudioContext 활성화 |
| **iOS 잠금 화면 시 소리 유지** | Safari 백그라운드 절전 정책 | 최신 플레이어에 내장된 0.1초 무음 WAV 앵커와 MediaStream 파이프라인이 자동 적용되어, [청취 시작] 버튼을 누른 후 화면을 꺼도 백그라운드에서 소리가 지속됩니다. |
| **SSL 인증서 경고** | 자체 서명 인증서 사용 | 브라우저 경고에서 [고급] -> [계속 진행] 선택 (또는 Let's Encrypt 공인 인증서 설정) |
