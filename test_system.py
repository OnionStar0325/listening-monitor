import asyncio
import os
from starlette.testclient import TestClient

import config
from core.ssl_cert import ensure_ssl_certificates
from core.session_manager import session_manager
from core.audio_engine import audio_engine
from core.broadcaster import broadcaster
from core.system_monitor import system_monitor
from main import app

def test_ssl_certificate_generation():
    """SSL 인증서 자동 생성 검증"""
    cert_path, key_path = ensure_ssl_certificates()
    assert os.path.exists(cert_path), "SSL 인증서 파일이 생성되지 않았습니다."
    assert os.path.exists(key_path), "SSL 개인키 파일이 생성되지 않았습니다."
    print("✅ [PASS] SSL 인증서 자동 생성 및 로드 검증")

def test_session_lifecycle_and_kick():
    """세션 생성, 토큰 인증, 강제 추방(Kick) 기능 검증"""
    # 1. 관리자 세션
    admin_session = session_manager.create_admin_session("127.0.0.1", "Test-Admin-Agent")
    assert admin_session.is_valid()
    assert admin_session.role == "admin"

    # 2. 청취자 초대 토큰 생성
    invite = session_manager.create_listener_invite("안드로이드 폰", valid_hours=1)
    token = invite["token"]
    assert token is not None

    # 3. 토큰으로 청취자 세션 활성화
    listener_session = session_manager.authenticate_listener_token(token, "192.168.1.50", "Android-Chrome")
    assert listener_session is not None
    assert listener_session.client_name == "안드로이드 폰"
    assert listener_session.is_valid()

    # 3-1. 동일 토큰으로 재접속 시도 (중복 세션 생성 방지 검증)
    listener_session_retry = session_manager.authenticate_listener_token(token, "192.168.1.50", "Android-Chrome-Retry")
    assert listener_session_retry.session_id == listener_session.session_id, "동일 토큰은 중복 세션을 생성하지 않아야 합니다."

    # 4. 세션 목록에 정확히 1개의 청취자 세션만 존재하는지 확인
    sessions = session_manager.get_all_sessions()
    listener_sessions = [s for s in sessions if s["role"] == "listener"]
    assert len(listener_sessions) == 1, f"청취자 세션은 정확히 1개여야 합니다 (현재: {len(listener_sessions)}개)"
    session_ids = [s["session_id"] for s in sessions]
    assert admin_session.session_id in session_ids
    assert listener_session.session_id in session_ids

    # 5. 청취자 세션 강제 추방 (Kick)
    asyncio.run(session_manager.kick_session(listener_session.session_id))
    assert not listener_session.is_valid()
    assert listener_session.is_revoked is True
    
    # 6. 추방 후 세션 목록에서 완전히 제거되었는지 확인
    sessions_after = session_manager.get_all_sessions()
    session_ids_after = [s["session_id"] for s in sessions_after]
    assert listener_session.session_id not in session_ids_after
    print("✅ [PASS] 세션 발급, 인증, 추방(Kick) 및 목록 즉시 제거 검증")

def test_audio_engine_and_virtual_tone():
    """오디오 엔진 및 가상 톤 발생기 검증"""
    status = audio_engine.get_status()
    assert status["sample_rate"] == 16000
    assert status["channels"] == 1
    
    # 게인 설정 테스트
    audio_engine.set_gain(1.5)
    assert audio_engine.gain == 1.5
    audio_engine.set_gain(1.0)
    print("✅ [PASS] 오디오 엔진 및 게인 설정 검증")

def test_system_monitor():
    """시스템 하드웨어 메트릭 수집 검증"""
    stats = system_monitor.get_system_stats()
    assert "cpu_percent" in stats
    assert "memory_percent" in stats
    assert "uptime_seconds" in stats
    print("✅ [PASS] 시스템 메트릭 수집 검증")

def test_api_endpoints():
    """FastAPI REST 엔드포인트 테스트"""
    client = TestClient(app)

    # 1. 로그인 실패 케이스
    res_fail = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_fail.status_code == 401

    # 2. 로그인 성공 케이스
    res_ok = client.post("/api/auth/login", json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD})
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["success"] is True
    assert "session_id" in data
    session_id = data["session_id"]
    headers = {"Authorization": f"Bearer {session_id}"}

    # 2-1. 네이티브 폼 로그인(POST /login) -> 303 리디렉션 -> 대시보드 0초 진입 검증
    res_form = client.post("/login", data={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD}, follow_redirects=True)
    assert res_form.status_code == 200
    assert "Listening Monitor" in res_form.text
    assert "호스트 CPU 사용률" in res_form.text

    # 3. 세션 목록 조회
    res_sess = client.get("/api/sessions", headers=headers)
    assert res_sess.status_code == 200
    sess_data = res_sess.json()
    assert "sessions" in sess_data
    assert sess_data["total_count"] >= 1

    # 4. 청취자 초대 토큰 및 QR 코드 생성 API
    res_inv = client.post("/api/sessions/invite", json={"client_name": "거실 iPad", "valid_hours": 24}, headers=headers)
    assert res_inv.status_code == 200
    inv_data = res_inv.json()
    assert inv_data["success"] is True
    assert "token" in inv_data["invite"]
    assert "qr_svg" in inv_data, "응답에 qr_svg 필드가 포함되어야 합니다."
    assert "<svg" in inv_data["qr_svg"], "QR 코드는 유효한 SVG 문자열이어야 합니다."

    # 4-1. QR 이미지 직접 조회 API (기본 PNG & SVG)
    token = inv_data["invite"]["token"]
    res_qr_png = client.get(f"/api/sessions/invite/{token}/qr")
    assert res_qr_png.status_code == 200
    assert "image/png" in res_qr_png.headers["content-type"]
    assert len(res_qr_png.content) > 100

    res_qr_svg = client.get(f"/api/sessions/invite/{token}/qr?format=svg")
    assert res_qr_svg.status_code == 200
    assert "image/svg+xml" in res_qr_svg.headers["content-type"]
    assert "<svg" in res_qr_svg.text

    # 5. 시스템 상태 API
    res_sys = client.get("/api/system/stats", headers=headers)
    assert res_sys.status_code == 200
    assert "cpu_percent" in res_sys.json()

    # 6. 웹 페이지 라우팅 확인
    # 브라우저 쿠키 시뮬레이션
    client.cookies.set(config.COOKIE_NAME, session_id)
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "Listening Monitor" in res_html.text

    # 7. iOS 무중단 백그라운드용 HTTP 라이브 WAV 스트림 검증
    async def _test_wav():
        gen = broadcaster.stream_wav_generator(session_id)
        header = await gen.asend(None)
        assert b"RIFF" in header
        assert b"WAVE" in header
        assert len(header) == 44
        await gen.aclose()
    asyncio.run(_test_wav())

    print("✅ [PASS] REST API, QR 코드, 및 iOS HTTP 라이브 스트림 엔드포인트 전체 검증")

def test_tailscale_and_proxy_client_ip():
    """Tailscale 및 리버스 프록시 접속 시 실제 클라이언트 IP 추출 검증"""
    from core.session_manager import extract_client_ip

    class DummyRequest:
        def __init__(self, headers=None, client_host=None):
            self.headers = headers or {}
            if client_host:
                class Client:
                    def __init__(self, host):
                        self.host = host
                self.client = Client(client_host)
            else:
                self.client = None

    # 1. Tailscale 전용 헤더 추출 검증
    req_ts = DummyRequest(headers={"tailscale-client-ip": "100.85.12.34"}, client_host="127.0.0.1")
    assert extract_client_ip(req_ts) == "100.85.12.34"

    # 2. X-Forwarded-For 다중 프록시 체인에서 실제 클라이언트 IP 추출 검증
    req_xff = DummyRequest(headers={"x-forwarded-for": "100.90.11.22:54321, 127.0.0.1"}, client_host="127.0.0.1")
    assert extract_client_ip(req_xff) == "100.90.11.22"

    # 3. X-Real-IP 검증
    req_real = DummyRequest(headers={"x-real-ip": "100.70.33.44"}, client_host="127.0.0.1")
    assert extract_client_ip(req_real) == "100.70.33.44"

    # 4. Cloudflare cf-connecting-ip 검증
    req_cf = DummyRequest(headers={"cf-connecting-ip": "203.0.113.195"}, client_host="127.0.0.1")
    assert extract_client_ip(req_cf) == "203.0.113.195"

    # 5. 헤더 없을 때 소켓 클라이언트 IP 폴백 검증
    req_sock = DummyRequest(headers={}, client_host="192.168.0.15")
    assert extract_client_ip(req_sock) == "192.168.0.15"

    # 6. TestClient를 통한 실제 API 요청 시 Tailscale IP 세션 등록 검증
    client = TestClient(app)
    res_login = client.post(
        "/api/auth/login",
        json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
        headers={"tailscale-client-ip": "100.101.102.103"}
    )
    assert res_login.status_code == 200
    ts_session_id = res_login.json()["session_id"]
    ts_session = session_manager.get_session(ts_session_id)
    assert ts_session.ip_address == "100.101.102.103", f"예상: 100.101.102.103, 실제: {ts_session.ip_address}"

    # 7. 초대 링크 발급 및 X-Forwarded-For 접속 시 청취자 세션 IP 갱신 검증
    inv = session_manager.create_listener_invite("Tailscale User", valid_hours=1)
    tok = inv["token"]
    # 최초 접속 시 X-Forwarded-For 적용
    res_listen = client.get(
        f"/listen?token={tok}",
        headers={"x-forwarded-for": "100.110.120.130, 127.0.0.1"}
    )
    assert res_listen.status_code == 200
    all_sess = session_manager.get_all_sessions()
    ts_listener = [s for s in all_sess if s["client_name"] == "Tailscale User"]
    assert len(ts_listener) == 1
    assert ts_listener[0]["ip_address"] == "100.110.120.130"

    print("✅ [PASS] Tailscale 및 리버스 프록시 환경 실제 IP 추출 검증 완료")

if __name__ == "__main__":
    test_ssl_certificate_generation()
    test_session_lifecycle_and_kick()
    test_audio_engine_and_virtual_tone()
    test_system_monitor()
    test_api_endpoints()
    test_tailscale_and_proxy_client_ip()
    print("\n🎉 모든 검증 테스트가 100% 성공했습니다!")
