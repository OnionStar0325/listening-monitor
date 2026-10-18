from __future__ import annotations
import time
import uuid
import secrets
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

import config

logger = logging.getLogger("listening_monitor.session")

@dataclass
class Session:
    session_id: str
    role: str  # 'admin' or 'listener'
    client_name: str
    ip_address: str
    user_agent: str
    created_at: float
    last_active: float
    is_streaming: bool = False
    is_revoked: bool = False
    invite_token: Optional[str] = None
    expires_at: Optional[float] = None

    def is_valid(self) -> bool:
        if self.is_revoked:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        # 세션 비활성 만료 (분 단위 설정 기준)
        if time.time() - self.last_active > (config.SESSION_EXPIRE_MINUTES * 60):
            return False
        return True


def extract_client_ip(request_or_websocket) -> str:
    """
    HTTP Request 또는 WebSocket에서 실제 접속지 클라이언트 IP 주소를 신뢰성 있게 추출합니다.
    Tailscale(Serve/Funnel), X-Forwarded-For, X-Real-IP, Cloudflare, 리버스 프록시 환경 지원.
    """
    if not request_or_websocket:
        return "unknown"

    headers = getattr(request_or_websocket, "headers", {})

    # 1. Tailscale 전용 헤더 (Tailscale Serve / Funnel 사용 시 클라이언트 Tailscale 100.x.y.z IP 주입)
    ts_ip = headers.get("tailscale-client-ip")
    if ts_ip and ts_ip.strip():
        return ts_ip.strip()

    # 2. X-Forwarded-For 헤더 (표준 프록시 체인: 클라이언트, 프록시1, 프록시2...)
    xff = headers.get("x-forwarded-for")
    if xff and xff.strip():
        ips = [x.strip() for x in xff.split(",") if x.strip()]
        for ip in ips:
            clean_ip = ip.split(":")[0] if ":" in ip and not ip.startswith("[") else ip.strip("[]")
            if clean_ip and clean_ip not in ("127.0.0.1", "::1", "localhost"):
                return clean_ip
        if ips:
            return ips[0].split(":")[0].strip("[]")

    # 3. X-Real-IP 헤더 (Nginx, Caddy, Tailscale, HAProxy 등)
    x_real = headers.get("x-real-ip")
    if x_real and x_real.strip():
        clean_real = x_real.split(":")[0].strip("[]")
        if clean_real not in ("127.0.0.1", "::1", "localhost"):
            return clean_real

    # 4. Cloudflare 전용 헤더 (Cloudflare Tunnel 사용 시)
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    # 5. 기타 프록시 표준 헤더
    for h in ("true-client-ip", "x-client-ip"):
        val = headers.get(h)
        if val and val.strip():
            return val.split(":")[0].strip("[]")

    # 6. 소켓 레벨 직접 연결 클라이언트 IP
    client = getattr(request_or_websocket, "client", None)
    if client and getattr(client, "host", None):
        return client.host

    return "unknown"


class SessionManager:
    """
    단일 관리자 + 청취자용 세션 토큰 체계를 관리하는 세션 매니저.
    실시간 활성 세션 추적, 세션 인증 검증, 원격 강제 추방(Kick)을 지원합니다.
    """
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._invite_tokens: Dict[str, dict] = {}  # token -> invite_metadata
        self._admin_password: str = config.ADMIN_PASSWORD
        self._broadcaster_ref = None  # 순환 참조 방지를 위해 런타임에 주입

    def set_broadcaster(self, broadcaster):
        self._broadcaster_ref = broadcaster

    # --- 관리자 비밀번호 검증 및 세션 ---
    def verify_admin_password(self, password: str) -> bool:
        return secrets.compare_digest(password, self._admin_password)

    def change_admin_password(self, old_pw: str, new_pw: str) -> bool:
        if not self.verify_admin_password(old_pw):
            return False
        if len(new_pw) < 4:
            return False
        self._admin_password = new_pw
        logger.info("관리자 비밀번호가 성공적으로 변경되었습니다.")
        return True

    def create_admin_session(self, ip_address: str, user_agent: str) -> Session:
        session_id = f"admin-{uuid.uuid4().hex}"
        now = time.time()
        session = Session(
            session_id=session_id,
            role="admin",
            client_name="관리자",
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_active=now,
            expires_at=now + (config.SESSION_EXPIRE_MINUTES * 60),
        )
        self._sessions[session_id] = session
        logger.info(f"관리자 세션 생성됨: {session_id} (IP: {ip_address})")
        return session

    # --- 청취자용 세션 및 초대 토큰 ---
    def create_listener_invite(self, client_name: str, valid_hours: int = 24) -> dict:
        """
        관리자가 특정 청취자(예: '거실 태블릿', '사용자 A')에게 부여할 초대 토큰을 생성합니다.
        """
        token = secrets.token_urlsafe(24)
        expires_at = time.time() + (valid_hours * 3600)
        metadata = {
            "token": token,
            "client_name": client_name or "청취자",
            "created_at": time.time(),
            "expires_at": expires_at,
            "valid_hours": valid_hours,
        }
        self._invite_tokens[token] = metadata
        logger.info(f"청취자 초대 토큰 생성: {client_name} (만료: {valid_hours}시간 후)")
        return metadata

    def authenticate_listener_token(self, token: str, ip_address: str, user_agent: str) -> Optional[Session]:
        """
        청취자 초대 토큰으로 청취자 세션을 인증합니다.
        [중복 세션 생성 방지]: 동일한 초대 토큰으로 접속한 경우 기존 세션을 갱신하여 반환하고,
        새로운 중복 세션이 리스트에 추가되지 않도록 보장합니다.
        """
        invite = self._invite_tokens.get(token)
        if not invite:
            return None
        
        if time.time() > invite["expires_at"]:
            del self._invite_tokens[token]
            return None

        now = time.time()

        # 1. 이미 동일한 초대 토큰으로 생성된 유효 세션이 있는지 확인 (중복 등록 방지)
        for s in list(self._sessions.values()):
            if s.invite_token == token and s.is_valid() and not s.is_revoked:
                # 127.0.0.1이 아닌 실제 원격 IP가 들어왔거나 기존 IP가 로컬호스트인 경우 최신 IP로 갱신
                if ip_address not in ("127.0.0.1", "::1", "localhost", "unknown") or s.ip_address in ("127.0.0.1", "::1", "localhost", "unknown"):
                    s.ip_address = ip_address
                s.user_agent = user_agent
                s.last_active = now
                logger.info(f"기존 청취자 세션 재사용(중복 방지): {s.session_id} ({s.client_name}, IP: {s.ip_address})")
                return s
        
        # 2. 최초 접속 시에만 신규 세션 1개 생성
        session_id = f"listener-{uuid.uuid4().hex}"
        session = Session(
            session_id=session_id,
            role="listener",
            client_name=invite["client_name"],
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_active=now,
            invite_token=token,
            expires_at=invite["expires_at"],
        )
        self._sessions[session_id] = session
        logger.info(f"신규 청취자 세션 활성화: {session_id} ({session.client_name}, IP: {ip_address})")
        return session

    # --- 세션 조회 및 검증 ---
    def get_session(self, session_id: str, current_ip: Optional[str] = None) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_valid():
            session.last_active = time.time()
            # 프록시/Tailscale 등에서 실제 접속지 IP가 확인되면 세션 IP 갱신
            if current_ip and current_ip not in ("127.0.0.1", "::1", "localhost", "unknown"):
                session.ip_address = current_ip
            return session
        return None

    def update_streaming_status(self, session_id: str, is_streaming: bool):
        if session_id in self._sessions:
            self._sessions[session_id].is_streaming = is_streaming
            self._sessions[session_id].last_active = time.time()

    # --- 세션 강제 추방(Kick) ---
    async def kick_session(self, session_id: str) -> bool:
        """
        관리자가 특정 세션을 강제 종료합니다.
        스트리밍 연결을 즉시 끊고, 초대 토큰 폐기 및 활성 세션 딕셔너리에서 즉시 삭제합니다.
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return False

        session.is_revoked = True
        session.is_streaming = False

        # 해당 세션의 초대 토큰도 즉시 폐기하여 동일 토큰으로의 재접속 원천 차단
        if session.invite_token and session.invite_token in self._invite_tokens:
            self._invite_tokens.pop(session.invite_token, None)
            logger.info(f"추방된 세션의 초대 토큰 폐기 완료: {session.invite_token}")

        logger.warning(f"세션 강제 추방 및 목록에서 삭제: {session_id} ({session.client_name})")

        # 연결된 웹소켓 / HTTP 스트림 강제 종료
        if self._broadcaster_ref:
            await self._broadcaster_ref.disconnect_session(session_id, reason="Kicked by administrator")

        return True

    async def revoke_all_listeners(self) -> int:
        """모든 청취자 세션 일괄 추방 및 삭제"""
        listener_sessions = [s for s in list(self._sessions.values()) if s.role == "listener"]
        count = 0
        for s in listener_sessions:
            await self.kick_session(s.session_id)
            count += 1
        return count

    def get_all_sessions(self) -> list[dict]:
        """대시보드 표시용 전체 활성 세션 목록 (추방되거나 만료된 세션 자동 정리)"""
        now = time.time()
        result = []
        for sid, s in list(self._sessions.items()):
            if not s.is_valid() or s.is_revoked:
                self._sessions.pop(sid, None)
                continue
            data = asdict(s)
            data["is_valid"] = True
            data["duration_seconds"] = int(now - s.created_at)
            data["idle_seconds"] = int(now - s.last_active)
            result.append(data)
        # 최신 생성순 정렬
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    def get_active_listener_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_valid() and s.is_streaming)


# 싱글톤 세션 매니저 인스턴스
session_manager = SessionManager()
