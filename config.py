import os
import secrets
from pathlib import Path

# 기본 디렉토리 경로
BASE_DIR = Path(__file__).resolve().parent
CERTS_DIR = BASE_DIR / "certs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# [네트워크 및 포트 설정]
# 기본값은 443(표준 HTTPS)이며, 환경변수 PORT 또는 본 설정값으로 변경 가능합니다.
# (루트 권한 없이 실행하려면 8443 등으로 변경할 수 있습니다)
SERVER_HOST: str = os.getenv("HOST", "0.0.0.0")
SERVER_PORT: int = int(os.getenv("PORT", "443"))

# [SSL / TLS 보안 설정]
SSL_CERT_FILE: Path = CERTS_DIR / "server.crt"
SSL_KEY_FILE: Path = CERTS_DIR / "server.key"
# 인증서가 없을 때 자동 생성할 자체 서명 인증서 설정
SSL_AUTO_GENERATE: bool = True
SSL_ORGANIZATION: str = "ListeningMonitor"
SSL_COMMON_NAME: str = os.getenv("SSL_CN", "listening-monitor.local")

# [보안 및 인증 설정]
# 세션 암호화 키 (고정하거나 환경변수로 전달 가능)
SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_hex(32))
# 관리자 기본 비밀번호 (최초 접속 후 웹에서 변경 권장)
ADMIN_USERNAME: str = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin1234!")
# 세션 유효 기간 (분 단위, 기본 24시간)
SESSION_EXPIRE_MINUTES: int = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))
# 관리자 세션 쿠키 이름
COOKIE_NAME: str = "lm_session_id"

# [오디오 스트리밍 설정 (PCM 16-bit Mono)]
# 시스템 CPU 부하를 최소화하고 음성 모니터링에 최적화된 16kHz
AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS: int = 1  # 모노
AUDIO_CHUNK_SIZE: int = 1024  # 1회 캡처/전송 단위 (샘플 수, ~64ms)
AUDIO_FORMAT: str = "S16_LE"  # 16-bit Little Endian PCM

# [오디오 캡처 백엔드 설정]
# 옵션: 'auto' (자동 감지), 'arecord' (Linux/RPi ALSA), 'wasapi' (Windows 저지연), 'directshow' (Windows 호환)
# - auto: Linux에서는 arecord/ALSA 우선, Windows에서는 WASAPI 우선 적용
# - arecord: Linux ALSA 전용 유틸리티 사용
# - wasapi: Windows Audio Session API (Windows 10/11 초저지연 오디오 캡처 표준)
# - directshow: Windows DirectShow / DirectSound 호환 모드
AUDIO_CAPTURE_BACKEND: str = os.getenv("AUDIO_CAPTURE_BACKEND", "auto").lower()

# 캡처 오디오 입력 장치 이름 또는 인덱스 ('default', 'plughw:1,0', 또는 특정 마이크 이름)
# 마이크 미인식 시 자동으로 가상 톤(Sine Wave) 모드로 폴백됩니다.
AUDIO_DEVICE_NAME: str = os.getenv("AUDIO_DEVICE_NAME", os.getenv("ALSA_DEVICE", "default"))
# 하위 호환성용 별칭
ALSA_DEVICE: str = AUDIO_DEVICE_NAME

# 입력 게인 배율 (1.0 = 기본, 1.5 = 증폭)
DEFAULT_INPUT_GAIN: float = 1.0

# [스트림 대역폭 및 동시 접속 제한]
MAX_STREAM_QUEUE_SIZE: int = 10  # 클라이언트별 오디오 패킷 큐 최대 크기 (초과시 지연 방지 드롭)
MAX_CONCURRENT_LISTENERS: int = int(os.getenv("MAX_CONCURRENT_LISTENERS", "20"))
