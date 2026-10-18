from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel

import config
from core.session_manager import session_manager, Session, extract_client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_session(request: Request) -> Session:
    """쿠키 또는 Authorization 헤더로부터 세션을 검증하는 의존성 주입 함수"""
    session_id = request.cookies.get(config.COOKIE_NAME)
    if not session_id:
        # Bearer 토큰 시도
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header.split(" ")[1]

    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")

    client_ip = extract_client_ip(request)
    session = session_manager.get_session(session_id, current_ip=client_ip)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="세션이 만료되었거나 유효하지 않습니다.")

    return session


def require_admin(session: Session = Depends(get_current_session)) -> Session:
    if session.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return session


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    # 관리자 아이디 및 비밀번호 검증
    if req.username != config.ADMIN_USERNAME or not session_manager.verify_admin_password(req.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디 또는 비밀번호가 일치하지 않습니다.")

    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    session = session_manager.create_admin_session(ip_address=client_ip, user_agent=user_agent)

    is_https = request.url.scheme == "https"
    # 보안 쿠키 설정 (path='/' 필수: 하위 경로 및 루트 대시보드 전체에서 쿠키 유효)
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=session.session_id,
        max_age=config.SESSION_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=is_https,
        samesite="lax",
        path="/",
    )

    return {
        "success": True,
        "session_id": session.session_id,
        "role": session.role,
        "client_name": session.client_name,
    }


@router.post("/logout")
async def logout(response: Response, session: Session = Depends(get_current_session)):
    await session_manager.kick_session(session.session_id)
    response.delete_cookie(key=config.COOKIE_NAME, path="/")
    return {"success": True, "message": "로그아웃되었습니다."}


@router.get("/me")
async def get_me(session: Session = Depends(get_current_session)):
    return {
        "session_id": session.session_id,
        "role": session.role,
        "client_name": session.client_name,
        "ip_address": session.ip_address,
        "is_streaming": session.is_streaming,
    }


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, session: Session = Depends(require_admin)):
    success = session_manager.change_admin_password(req.old_password, req.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="기존 비밀번호가 일치하지 않거나 새 비밀번호 형식이 올바르지 않습니다.")
    return {"success": True, "message": "비밀번호가 안전하게 변경되었습니다."}
