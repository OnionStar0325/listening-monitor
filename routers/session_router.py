from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from pydantic import BaseModel
from typing import Optional
import io
import base64
import qrcode
import qrcode.image.svg

from core.session_manager import session_manager, Session
from routers.auth_router import require_admin

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class CreateInviteRequest(BaseModel):
    client_name: str
    valid_hours: Optional[int] = 24
    base_url: Optional[str] = None  # 클라이언트 브라우저 주소 (프로토콜+호스트)

def generate_qr_png_data_url(url: str) -> str:
    """순수 파이썬으로 100% 브라우저 호환 Base64 PNG QR 코드 생성 (Pillow 미설치 시 SVG Data URL로 안전 자동 폴백)"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"
    except Exception:
        # Pillow(PIL) 미설치 또는 런타임 오류 시 100% 표준 호환 SVG Base64 Data URL로 자동 폴백
        svg_content = generate_qr_svg(url)
        b64_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64_svg}"

def generate_qr_svg(url: str) -> str:
    """SVG 헤더를 제거한 순수 벡터 SVG QR 코드"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=qrcode.image.svg.SvgPathImage
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf)
    raw_svg = buf.getvalue().decode("utf-8")
    # <?xml ...?> 선언 제거 (HTML innerHTML 삽입 호환성)
    if "<?xml" in raw_svg:
        raw_svg = raw_svg.split("?>", 1)[-1].strip()
    return raw_svg

@router.get("")
async def list_sessions(admin_session: Session = Depends(require_admin)):
    """현재 시스템에 등록된 전체 활성 세션 목록 조회"""
    sessions = session_manager.get_all_sessions()
    active_listeners = session_manager.get_active_listener_count()
    return {
        "total_count": len(sessions),
        "active_streaming_count": active_listeners,
        "sessions": sessions,
    }

@router.post("/invite")
async def create_invite(req: CreateInviteRequest, request: Request, admin_session: Session = Depends(require_admin)):
    """
    청취자용 초대 링크, 일회용 세션 토큰 및 스마트폰 카메라 스캔용 QR 코드(PNG Data URL & SVG) 생성
    """
    invite = session_manager.create_listener_invite(
        client_name=req.client_name,
        valid_hours=req.valid_hours or 24,
    )
    token = invite["token"]

    if req.base_url:
        full_url = f"{req.base_url.rstrip('/')}/listen?token={token}"
    else:
        host = request.headers.get("host", "localhost")
        scheme = "https"
        full_url = f"{scheme}://{host}/listen?token={token}"

    qr_png = generate_qr_png_data_url(full_url)
    qr_svg = generate_qr_svg(full_url)

    return {
        "success": True,
        "invite": invite,
        "url": full_url,
        "qr_png": qr_png,
        "qr_svg": qr_svg,
    }

@router.get("/invite/{token}/qr")
async def get_invite_qr(token: str, request: Request, format: str = "png"):
    """특정 초대 토큰에 대한 QR 코드 이미지 직접 서빙 (png 또는 svg)"""
    host = request.headers.get("host", "localhost")
    full_url = f"https://{host}/listen?token={token}"
    
    if format.lower() == "svg":
        qr_svg = generate_qr_svg(full_url)
        return Response(content=qr_svg, media_type="image/svg+xml")
    
    # PNG 바이너리 스트림 반환 (Pillow 미설치 시 SVG로 안전하게 자동 폴백)
    try:
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(full_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception:
        qr_svg = generate_qr_svg(full_url)
        return Response(content=qr_svg, media_type="image/svg+xml")

@router.post("/{session_id}/kick")
async def kick_session(session_id: str, admin_session: Session = Depends(require_admin)):
    """특정 세션을 강제 추방하고 웹소켓 연결을 차단"""
    if session_id == admin_session.session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자기 자신의 세션은 추방할 수 없습니다.")

    success = await session_manager.kick_session(session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 세션을 찾을 수 없습니다.")

    return {"success": True, "message": f"세션 {session_id} 이(가) 추방되었습니다."}

@router.post("/kick-all-listeners")
async def kick_all_listeners(admin_session: Session = Depends(require_admin)):
    """모든 청취자 세션 일괄 종료"""
    count = await session_manager.revoke_all_listeners()
    return {"success": True, "kicked_count": count, "message": f"{count}개의 청취자 세션이 종료되었습니다."}
