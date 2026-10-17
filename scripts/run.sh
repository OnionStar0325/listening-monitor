#!/usr/bin/env bash
set -e

# 프로젝트 루트 디렉토리 결정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_ROOT="$SCRIPT_DIR"
else
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
fi
cd "$PROJECT_ROOT"

# 기본 포트 8443 (비특권 포트 권장)
export PORT="${PORT:-8443}"
export AUDIO_CAPTURE_BACKEND="${AUDIO_CAPTURE_BACKEND:-auto}"

echo "========================================================"
echo "  🎙️ Listening Monitor 스트리밍 서버 시작"
echo "========================================================"
echo " - 서비스 포트 : $PORT (접속 주소: https://localhost:$PORT)"
echo " - 오디오 백엔드: $AUDIO_CAPTURE_BACKEND"
echo ""
echo " * 자체 서명 SSL 인증서 경고가 표시되면 [고급] -> [계속 진행]을 클릭하세요."
echo " * 기본 관리자 계정: admin / admin1234!"
echo "--------------------------------------------------------"

# 가상환경(venv) 존재 시 가상환경의 python3 사용
if [ -f "venv/bin/python3" ]; then
    exec ./venv/bin/python3 main.py "$@"
else
    exec python3 main.py "$@"
fi
