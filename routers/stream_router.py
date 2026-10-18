import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status, Request, HTTPException
from fastapi.responses import StreamingResponse

import config
from core.session_manager import session_manager, extract_client_ip
from core.broadcaster import broadcaster

logger = logging.getLogger("listening_monitor.stream")

router = APIRouter(tags=["stream"])

# --- 1. WebSocket (WSS) 초저지연 엔드포인트 ---
@router.websocket("/ws/stream")
async def audio_stream_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
):
    """
    실시간 바이너리 오디오 스트림(PCM 16-bit)을 전달하는 보안 웹소켓(WSS) 엔드포인트.
    - 관리자: session_id 파라미터 또는 쿠키 기반 인증
    - 청취자: 초대 토큰(?token=...) 기반 자동 세션 인증
    """
    client_ip = extract_client_ip(websocket)
    user_agent = websocket.headers.get("user-agent", "unknown")
    target_session = None

    # 1. 쿼리 파라미터 session_id 또는 쿠키 확인
    active_session_id = session_id or websocket.cookies.get(config.COOKIE_NAME)
    if active_session_id:
        target_session = session_manager.get_session(active_session_id, current_ip=client_ip)

    # 2. 초대 토큰(token) 파라미터 확인 (새로운 청취자 세션 생성)
    if not target_session and token:
        target_session = session_manager.authenticate_listener_token(
            token=token,
            ip_address=client_ip,
            user_agent=user_agent
        )
    elif target_session and client_ip not in ("127.0.0.1", "::1", "localhost", "unknown"):
        target_session.ip_address = client_ip

    # 3. 인증 실패 시 연결 거부
    if not target_session or not target_session.is_valid():
        logger.warning(f"[WSS 거부] 유효하지 않은 세션 접근: IP={client_ip}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="인증되지 않은 세션입니다.")
        return

    # 4. 동시 접속 제한 확인
    if broadcaster.connection_count >= config.MAX_CONCURRENT_LISTENERS:
        logger.warning(f"[WSS 거부] 최대 동시 접속자 수 초과 ({config.MAX_CONCURRENT_LISTENERS}명)")
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="최대 동시 접속 인원을 초과했습니다.")
        return

    # 5. 브로드캐스터에 연결 등록 및 스트리밍 시작
    try:
        await broadcaster.connect(target_session.session_id, websocket)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"[WSS 정상 종료] 클라이언트 연결 종료: {target_session.session_id}")
    except Exception as e:
        logger.debug(f"[WSS 예외] {target_session.session_id}: {e}")
    finally:
        await broadcaster.disconnect(target_session.session_id)


# --- 2. iOS Safari / 모바일 화면 잠금 무중단 HTTP 라이브 스트림 엔드포인트 ---
@router.get("/api/stream/audio.wav")
async def audio_stream_http(
    request: Request,
    token: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
):
    """
    iOS(iPhone/iPad) Safari의 잠금 화면(화면 꺼짐)에서도 끊김 없이 100% 지속 재생을 보장하는
    HTTP 라이브 오디오(Endless WAV) 스트리밍 엔드포인트.
    HTML5 <audio playsinline src="/api/stream/audio.wav?token=..."> 태그로 직접 재생됩니다.
    """
    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    target_session = None

    # 1. session_id 또는 쿠키 확인
    active_session_id = session_id or request.cookies.get(config.COOKIE_NAME)
    if active_session_id:
        target_session = session_manager.get_session(active_session_id, current_ip=client_ip)

    # 2. 초대 토큰 확인
    if not target_session and token:
        target_session = session_manager.authenticate_listener_token(
            token=token,
            ip_address=client_ip,
            user_agent=user_agent
        )
    elif target_session and client_ip not in ("127.0.0.1", "::1", "localhost", "unknown"):
        target_session.ip_address = client_ip

    # 3. 인증 검증
    if not target_session or not target_session.is_valid():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않거나 만료된 세션입니다.")

    logger.info(f"[HTTP Stream] iOS 백그라운드 스트림 요청 수락: {target_session.client_name} (IP: {client_ip})")

    headers = {
        "Content-Type": "audio/wav",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        broadcaster.stream_wav_generator(target_session.session_id, request=request),
        media_type="audio/wav",
        headers=headers
    )
