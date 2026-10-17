from fastapi import APIRouter, Request, Response, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import config
from core.session_manager import session_manager

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """관리자 메인 대시보드"""
    session_id = request.cookies.get(config.COOKIE_NAME)
    session = session_manager.get_session(session_id) if session_id else None

    # 미로그인 상태면 로그인 페이지로 이동
    if not session or session.role != "admin":
        return RedirectResponse(url="/login")

    import platform
    os_name = platform.system()
    machine = platform.machine()
    platform_name = f"{os_name} ({machine})"

    from core.system_monitor import system_monitor
    from core.audio_engine import audio_engine

    stats = system_monitor.get_system_stats()
    audio_status = audio_engine.get_status()
    sessions = session_manager.get_all_sessions()
    active_listeners = session_manager.get_active_listener_count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "session": session,
            "sample_rate": config.AUDIO_SAMPLE_RATE,
            "server_port": config.SERVER_PORT,
            "platform_name": platform_name,
            "stats": stats,
            "audio_status": audio_status,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "active_listeners": active_listeners,
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    """관리자 로그인 페이지"""
    session_id = request.cookies.get(config.COOKIE_NAME)
    session = session_manager.get_session(session_id) if session_id else None

    # 이미 로그인되어 있다면 대시보드로 이동
    if session and session.role == "admin":
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    브라우저 네이티브 폼 제출 로그인 핸들러:
    자바스크립트 fetch 지연이나 쿠키 동기화 지연 없이 즉시 303 See Other로 대시보드로 이동하여
    0.05초 미만의 번개 같은 첫 페이지 진입 속도를 보장합니다.
    """
    if username != config.ADMIN_USERNAME or not session_manager.verify_admin_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "아이디 또는 비밀번호가 일치하지 않습니다."},
            status_code=401,
        )

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    session = session_manager.create_admin_session(ip_address=client_ip, user_agent=user_agent)

    is_https = request.url.scheme == "https"
    # 303 See Other 리디렉션으로 대시보드로 즉시 전환
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.set_cookie(
        key=config.COOKIE_NAME,
        value=session.session_id,
        max_age=config.SESSION_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=is_https,
        samesite="lax",
        path="/",
    )
    return redirect

@router.get("/listen", response_class=HTMLResponse)
async def listener_page(request: Request, token: str = ""):
    """
    청취자 전용 미니 웹 플레이어 페이지.
    안드로이드, iOS, 윈도우, 웹 등에서 초대 링크(?token=...)를 열면
    복잡한 설정 없이 원클릭으로 즉시 실시간 오디오를 수신합니다.
    """
    return templates.TemplateResponse(
        "listener.html",
        {
            "request": request,
            "token": token,
            "sample_rate": config.AUDIO_SAMPLE_RATE,
        }
    )
