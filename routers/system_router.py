from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.system_monitor import system_monitor
from core.audio_engine import audio_engine
from core.broadcaster import broadcaster
from core.session_manager import Session
from routers.auth_router import require_admin

router = APIRouter(prefix="/api/system", tags=["system"])

class GainRequest(BaseModel):
    gain: float

@router.get("/stats")
async def get_system_stats(admin_session: Session = Depends(require_admin)):
    """라즈베리파이 CPU, RAM, 온도, Uptime 및 스트림 통계"""
    stats = system_monitor.get_system_stats()
    stats["connected_clients"] = broadcaster.connection_count
    return stats

@router.get("/audio")
async def get_audio_status(admin_session: Session = Depends(require_admin)):
    """오디오 캡처 엔진 상세 상태"""
    return audio_engine.get_status()

@router.post("/audio/gain")
async def set_audio_gain(req: GainRequest, admin_session: Session = Depends(require_admin)):
    """오디오 입력 게인(소프트웨어 볼륨) 변경"""
    audio_engine.set_gain(req.gain)
    return {"success": True, "gain": audio_engine.gain}
