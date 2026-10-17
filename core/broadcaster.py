from __future__ import annotations
import asyncio
import logging
import struct
from typing import Dict, AsyncGenerator
from fastapi import WebSocket, status

import config
from core.session_manager import session_manager

logger = logging.getLogger("listening_monitor.broadcaster")

def build_wav_header(sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """
    브라우저(iOS Safari / Chrome 등)가 라이브 무한 스트림으로 인식할 수 있는
    표준 44바이트 WAV 스트리밍 헤더를 생성합니다.
    """
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    # 0x7FFFFFFF = 약 2GB (실시간 라이브 스트림 표준)
    data_size = 0x7FFFFFFF
    riff_chunk_size = data_size + 36

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        riff_chunk_size,
        b'WAVE',
        b'fmt ',
        16,                # PCM 서브청크 크기
        1,                 # 포맷 코드 (1 = PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    return header


class AudioBroadcaster:
    """
    오디오 스트림 브로드캐스터.
    1. WSS(WebSocket Secure): 웹 브라우저/PC 초저지연(100~200ms) 바이너리 스트림
    2. HTTP Live WAV Stream: iOS Safari / 모바일 화면 잠금 무중단 백그라운드 재생 전용 스트림
    """
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

        # iOS / 모바일 백그라운드 재생용 HTTP 클라이언트 큐
        self._http_queues: Dict[str, asyncio.Queue] = {}

        # session_manager에 broadcaster 참조 등록
        session_manager.set_broadcaster(self)

    @property
    def connection_count(self) -> int:
        return len(self._connections) + len(self._http_queues)

    # --- 1. WebSocket (WSS) 스트림 관리 ---
    async def connect(self, session_id: str, websocket: WebSocket):
        """인증된 클라이언트의 웹소켓을 등록하고 개별 스트리밍 태스크를 시작합니다."""
        await websocket.accept()
        
        if session_id in self._connections:
            await self.disconnect(session_id)

        queue: asyncio.Queue = asyncio.Queue(maxsize=config.MAX_STREAM_QUEUE_SIZE)
        self._connections[session_id] = websocket
        self._queues[session_id] = queue
        
        session_manager.update_streaming_status(session_id, is_streaming=True)
        task = asyncio.create_task(self._client_sender_loop(session_id, websocket, queue))
        self._tasks[session_id] = task
        logger.info(f"[WSS] 클라이언트 스트림 연결됨: {session_id} (총 WSS 접속자: {len(self._connections)}명)")

    async def disconnect(self, session_id: str):
        """웹소켓 접속 해제 처리"""
        session_manager.update_streaming_status(session_id, is_streaming=False)

        task = self._tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        self._queues.pop(session_id, None)
        ws = self._connections.pop(session_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(f"[WSS] 클라이언트 연결 해제: {session_id} (남은 WSS 접속자: {len(self._connections)}명)")

    async def disconnect_session(self, session_id: str, reason: str = "Disconnected by server"):
        """관리자 추방(Kick) 시 호출: WSS 및 HTTP 스트림 모두 즉시 강제 종료"""
        # WSS 소켓 차단
        ws = self._connections.get(session_id)
        if ws:
            logger.warning(f"[WSS] 세션 강제 추방(Kick): {session_id} (사유: {reason})")
            try:
                await ws.close(code=4001, reason=reason)
            except Exception:
                pass
        await self.disconnect(session_id)

        # HTTP 스트림 차단
        http_q = self._http_queues.pop(session_id, None)
        if http_q:
            logger.warning(f"[HTTP] 세션 강제 추방(Kick): {session_id}")
            # None을 큐에 넣어 비동기 제너레이터 즉시 종료
            try:
                http_q.put_nowait(None)
            except Exception:
                pass
            session_manager.update_streaming_status(session_id, is_streaming=False)

    async def _client_sender_loop(self, session_id: str, websocket: WebSocket, queue: asyncio.Queue):
        """개별 클라이언트로 바이너리 PCM 청크를 전송하는 루프"""
        try:
            while True:
                chunk = await queue.get()
                await websocket.send_bytes(chunk)
                queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"클라이언트 {session_id} 전송 루프 종료: {e}")
        finally:
            await self.disconnect(session_id)

    # --- 2. iOS Safari / 모바일 화면 꺼짐 무중단 HTTP 라이브 스트림 ---
    async def stream_wav_generator(self, session_id: str, request = None) -> AsyncGenerator[bytes, None]:
        """
        iOS Safari의 HTML5 <audio playsinline src="..."> 태그를 위한
        무한 HTTP 라이브 WAV 스트림 비동기 제너레이터.
        화면이 꺼지거나 잠겨도 iOS 시스템(AVPlayer)이 백그라운드에서 오디오를 멈추지 않고 유지합니다.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=config.MAX_STREAM_QUEUE_SIZE * 2)
        self._http_queues[session_id] = queue
        session_manager.update_streaming_status(session_id, is_streaming=True)
        logger.info(f"[HTTP Live] iOS/모바일 스트림 시작: {session_id} (총 HTTP 접속: {len(self._http_queues)}명)")

        try:
            # 1. 표준 44바이트 WAV 헤더 최초 1회 전송
            header = build_wav_header(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                channels=config.AUDIO_CHANNELS,
                bits_per_sample=16
            )
            yield header

            # 2. 오디오 청크 지속 스트리밍
            while True:
                if request and await request.is_disconnected():
                    break

                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.5)
                    if chunk is None:  # 세션 추방(Kick) 또는 종료 신호
                        break
                    yield chunk
                    queue.task_done()
                except asyncio.TimeoutError:
                    if request and await request.is_disconnected():
                        break
                    session = session_manager.get_session(session_id)
                    if not session or not session.is_valid():
                        break
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"[HTTP Live] 스트림 종료 ({session_id}): {e}")
        finally:
            self._http_queues.pop(session_id, None)
            session_manager.update_streaming_status(session_id, is_streaming=False)
            logger.info(f"[HTTP Live] 스트림 종료됨: {session_id}")

    # --- 3. 오디오 청크 일괄 브로드캐스트 ---
    async def broadcast_chunk(self, chunk: bytes):
        """
        오디오 엔진에서 캡처된 새 오디오 청크를
        WSS 및 HTTP 라이브 스트림 구독자 전체에 분배합니다.
        """
        # A. WebSocket 큐 분배
        for session_id, queue in list(self._queues.items()):
            try:
                if queue.full():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(chunk)
            except Exception:
                pass

        # B. HTTP Live 스트림 큐 분배 (iOS / 백그라운드용)
        for session_id, queue in list(self._http_queues.items()):
            try:
                if queue.full():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(chunk)
            except Exception:
                pass


# 싱글톤 브로드캐스터 인스턴스
broadcaster = AudioBroadcaster()
