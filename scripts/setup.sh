#!/usr/bin/env bash
set -e

echo "=== [Listening Monitor 환경 설정 시작 (Linux / Raspberry Pi / ChromeOS)] ==="

# 1. 시스템 필수 패키지 설치
echo "[1/4] OS 필수 패키지 설치 중..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip alsa-utils libasound2-dev libportaudio2 openssl

# 2. 파이썬 의존성 설치
echo "[2/4] 파이썬 패키지 설치 중..."
pip3 install -r requirements.txt

# 3. 오디오 장치 점검
echo "[3/4] 연결된 마이크 장치 점검:"
arecord -l || echo "⚠️ 연결된 USB 마이크가 없습니다. (가상 톤 모드로 자동 동작합니다)"

# 4. 포트 443 일반 유저 바인딩 권한 (선택 사항: python3 바이너리에 CAP_NET_BIND_SERVICE 부여)
echo "[4/4] 443 포트 권한 확인..."
PYTHON_BIN=$(which python3)
if [ -n "$PYTHON_BIN" ]; then
    sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_BIN" || true
fi

echo "=== [설치 완료! 'python3 main.py' 로 실행하실 수 있습니다] ==="
