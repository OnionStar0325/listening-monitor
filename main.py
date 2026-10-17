import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import config
from core.ssl_cert import ensure_ssl_certificates
from core.audio_engine import audio_engine
from routers.auth_router import router as auth_router
from routers.session_router import router as session_router
from routers.stream_router import router as stream_router
from routers.system_router import router as system_router
from routers.web_router import router as web_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("listening_monitor")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 라이프사이클 관리"""
    logger.info("=== [실시간 오디오 보안 모니터 시스템 시작] ===")
    
    # 1. SSL 인증서 자동 확인 및 발급
    if config.SSL_AUTO_GENERATE:
        cert_file, key_file = ensure_ssl_certificates()
        logger.info(f"[보안] TLS/SSL 인증서 준비 완료: {cert_file}")

    # 2. 오디오 캡처 엔진 시작 (마이크 또는 가상 테스트 톤)
    await audio_engine.start()

    yield

    # 애플리케이션 종료 처리
    logger.info("=== [시스템 종료 중...] ===")
    await audio_engine.stop()

# FastAPI 애플리케이션 인스턴스
app = FastAPI(
    title="실시간 오디오 보안 스트리밍 모니터",
    description="안드로이드, iOS, 윈도우, 웹 다중 플랫폼 실시간 오디오 스트리밍 및 세션 제어 솔루션",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 등록 (안전한 교차 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 압축 미들웨어 등록 (네트워크 페이로드 압축으로 첫 페이지 및 정적 자원 전송 속도 가속)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 정적 파일 서빙 (/static)
config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

# API 및 웹 라우터 등록
app.include_router(auth_router)
app.include_router(session_router)
app.include_router(stream_router)
app.include_router(system_router)
app.include_router(web_router)


def run_server():
    """Uvicorn HTTPS / WSS 서버 구동"""
    cert_path, key_path = ensure_ssl_certificates()

    port = config.SERVER_PORT
    host = config.SERVER_HOST

    logger.info(f"🌐 보안 서버 구동: https://{host}:{port}")
    logger.info(f"🔒 WSS 스트림 주소: wss://{host}:{port}/ws/stream")

    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            ssl_keyfile=key_path,
            ssl_certfile=cert_path,
            log_level="info",
            access_log=False,  # 시스템 I/O 부하 절감
        )
    except PermissionError:
        if port == 443:
            logger.warning(
                "⚠️ 포트 443 바인딩 권한 부족 (비특권 사용자 또는 ChromeOS/컨테이너 환경).\n"
                "   안전한 대체 포트 8443으로 자동 전환하여 서버를 실행합니다."
            )
            port = 8443
            logger.info(f"🌐 보안 서버 구동: https://{host}:{port}")
            logger.info(f"🔒 WSS 스트림 주소: wss://{host}:{port}/ws/stream")
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                ssl_keyfile=key_path,
                ssl_certfile=cert_path,
                log_level="info",
                access_log=False,
            )
        else:
            logger.error(
                f"❌ 포트 {port} 바인딩 권한 오류: 권한이 부족합니다.\n"
                f"   포트를 8443 등 1024 이상의 비특권 포트로 변경하여 실행하세요."
            )
            sys.exit(1)


if __name__ == "__main__":
    run_server()
