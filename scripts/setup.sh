#!/usr/bin/env bash
set -e

# 실행 경로와 관계없이 프로젝트 루트 디렉토리 기준으로 동작
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=== [Listening Monitor 환경 설정 시작 (Linux / Raspberry Pi / ChromeOS)] ==="

# 1. OS 시스템 필수 패키지 설치
echo "[1/4] OS 필수 패키지 설치 중 (apt)..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    alsa-utils \
    libasound2-dev \
    libasound2-plugins \
    libportaudio2 \
    portaudio19-dev \
    pulseaudio-utils \
    openssl

# 2. 파이썬 가상환경(venv) 및 패키지 설치 (Debian 12 Bookworm / Ubuntu PEP 668 호환)
echo "[2/4] 파이썬 가상환경 및 라이브러리 설치 중..."
if [ ! -d "venv" ]; then
    echo "   가상환경(venv)을 생성합니다..."
    python3 -m venv venv 2>/dev/null || true
fi

if [ -f "venv/bin/pip" ]; then
    echo "   가상환경(venv)에 패키지를 설치합니다..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    echo "   시스템 파이썬 환경에 패키지를 설치합니다..."
    pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt
fi

# 3. 오디오 캡처 장치 점검
echo "[3/4] 오디오 캡처 장치 점검 중..."
MIC_FOUND=false

# 3-1. ALSA 하드웨어 사운드카드 확인
if command -v arecord >/dev/null 2>&1; then
    if arecord -l 2>/dev/null | grep -q "card"; then
        echo "   ✅ ALSA 하드웨어 마이크 감지됨:"
        arecord -l 2>/dev/null | grep "card" | sed 's/^/      /'
        MIC_FOUND=true
    fi
fi

# 3-2. PulseAudio / PipeWire / ChromeOS 오디오 소스 확인
if command -v pactl >/dev/null 2>&1; then
    PA_SOURCES=$(pactl list sources short 2>/dev/null | grep -v "monitor" || true)
    if [ -n "$PA_SOURCES" ]; then
        echo "   ✅ PulseAudio / ChromeOS 마이크 소스 감지됨:"
        echo "$PA_SOURCES" | sed 's/^/      /'
        MIC_FOUND=true
    fi
fi

if [ "$MIC_FOUND" = false ]; then
    echo "   ⚠️ 현재 물리 마이크가 연결되지 않았거나 Linux 컨테이너 마이크 권한이 비활성화되어 있습니다."
    echo "      (시스템 구동 시 자동으로 '가상 톤(Sine Wave) 모드'로 안전하게 동작합니다)"
    echo ""
    echo "   💡 [크롬북(ChromeOS) 마이크 활성화 방법]:"
    echo "      1. 크롬북 오른쪽 하단 시계 클릭 -> [설정 ⚙️] 열기"
    echo "      2. [고급] -> [개발자] -> [Linux 개발 환경(Crostini)] 선택"
    echo "      3. '마이크 액세스 허용 (Allow Linux to access your microphone)' 스위치를 켭니다."
    echo "      4. 터미널을 완전히 닫고 다시 열면 마이크가 활성화됩니다."
fi

# 4. 실행 환경 및 권한 점검
echo "[4/4] 실행 환경 및 권한 점검..."
PYTHON_BIN=$(which python3 2>/dev/null || true)
if [ -n "$PYTHON_BIN" ]; then
    # 443 포트 사용을 위한 setcap 시도 (컨테이너/ChromeOS에서는 권한 제한으로 실패할 수 있으며 기본 8443 포트를 사용하므로 무방)
    sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_BIN" 2>/dev/null || true
fi

# 실행 스크립트 실행 권한 부여
chmod +x scripts/run.sh 2>/dev/null || true

echo ""
echo "=================================================================="
echo "  🎉 Listening Monitor 환경 설정이 성공적으로 완료되었습니다!"
echo "=================================================================="
echo "  ▶ 실행 방법:"
echo "     ./run.sh               (권장: 가상환경 자동 감지)"
echo "     또는"
echo "     python3 main.py"
echo ""
echo "  ▶ 웹 대시보드 접속 주소:"
echo "     https://localhost:8443 (또는 https://<서버IP>:8443)"
echo "=================================================================="
