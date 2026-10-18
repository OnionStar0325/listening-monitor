from __future__ import annotations
import asyncio
import logging
import math
import shutil
import sys
from typing import Optional
import numpy as np

import config
from core.broadcaster import broadcaster

logger = logging.getLogger("listening_monitor.audio")

class AudioEngine:
    """
    크로스 플랫폼(Linux, Windows, ChromeOS, Raspberry Pi) 실시간 오디오 캡처 엔진.
    
    지원 백엔드:
    - 'arecord': Linux ALSA 전용 경량 유틸리티
    - 'wasapi': Windows WASAPI (Windows Audio Session API, Windows 10/11 초저지연 표준)
    - 'directshow': Windows DirectSound / DirectShow 호환 모드
    - 'auto': OS에 따라 Linux=arecord, Windows=WASAPI 자동 선택

    마이크 미연결 또는 오류 시 시스템 중단 없이 '가상 테스트 톤(Sine Wave)' 모드로 안전하게 자동 폴백합니다.
    """
    def __init__(self):
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.channels = config.AUDIO_CHANNELS
        self.chunk_size = config.AUDIO_CHUNK_SIZE  # 1024 샘플 (~64ms)
        self.chunk_bytes = self.chunk_size * 2 * self.channels  # 16-bit PCM = 2 bytes per sample
        self.backend_setting = config.AUDIO_CAPTURE_BACKEND
        self.device_name = config.AUDIO_DEVICE_NAME
        self.gain = config.DEFAULT_INPUT_GAIN

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._sd_stream = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self.active_backend = "none"
        self.is_virtual_mode = False
        self.status_message = "초기화 대기 중"

    def set_gain(self, gain: float):
        """소프트웨어 입력 게인 설정 (0.0 ~ 3.0)"""
        self.gain = max(0.0, min(float(gain), 3.0))
        logger.info(f"오디오 입력 게인 변경: {self.gain:.2f}x")

    async def start(self):
        """오디오 캡처 루프 시작"""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._run_capture_loop())
        logger.info(
            f"오디오 엔진 시작됨 (플랫폼: {sys.platform}, 설정 백엔드: {self.backend_setting}, "
            f"샘플레이트: {self.sample_rate}Hz)"
        )

    async def stop(self):
        """오디오 캡처 종료 및 정리"""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception:
                pass
            self._process = None

        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception:
                pass
            self._sd_stream = None

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.status_message = "정지됨"
        logger.info("오디오 엔진 정지 완료")

    async def _run_capture_loop(self):
        """설정된 백엔드에 따라 최적의 캡처 루틴 실행"""
        backend = self.backend_setting.lower()

        # 1. 명시적 arecord 요청 또는 Linux auto
        if backend == "arecord" or (backend == "auto" and sys.platform.startswith("linux")):
            arecord_path = shutil.which("arecord")
            if arecord_path:
                success = await self._start_arecord_capture(arecord_path)
                if success:
                    return
            elif backend == "arecord":
                logger.warning("arecord 명령어를 찾을 수 없습니다. (Linux alsa-utils 필요)")

        # 2. Windows WASAPI 요청 또는 Windows auto
        if backend == "wasapi" or (backend == "auto" and sys.platform == "win32"):
            success = await self._start_sounddevice_capture(target_hostapi="wasapi")
            if success:
                return

        # 3. DirectShow / DirectSound 요청
        if backend == "directshow":
            success = await self._start_sounddevice_capture(target_hostapi="directsound")
            if success:
                return

        # 4. 범용 sounddevice 시도 (플랫폼 무관)
        if backend not in ("virtual", "none"):
            success = await self._start_sounddevice_capture(target_hostapi=None)
            if success:
                return

        # 5. 모든 하드웨어 장치 초기화 실패 시 가상 톤 제너레이터로 폴백
        await self._start_virtual_tone_generator()

    # --- 1. Linux ALSA arecord 파이프라인 ---
    async def _start_arecord_capture(self, arecord_path: str) -> bool:
        device = self.device_name if self.device_name != "default" else "default"
        cmd = [
            arecord_path,
            "-D", device,
            "-f", config.AUDIO_FORMAT,
            "-r", str(self.sample_rate),
            "-c", str(self.channels),
            "-t", "raw",
            "-q",
        ]
        logger.info(f"ALSA arecord 캡처 시작: {' '.join(cmd)}")
        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # 첫 바이트 읽기 검증 (1.5초 타임아웃)
            first_chunk = await asyncio.wait_for(self._process.stdout.read(self.chunk_bytes), timeout=1.5)
            if not first_chunk:
                raise RuntimeError("arecord 데이터 수신 없음")

            self.active_backend = "arecord (Linux ALSA)"
            self.is_virtual_mode = False
            self.status_message = f"ALSA 마이크 정상 수신 중 ({device})"
            logger.info(f"ALSA 마이크 스트림 활성화: {device}")

            await self._process_and_broadcast(first_chunk)

            while self._running and self._process and self._process.returncode is None:
                chunk = await self._process.stdout.readexactly(self.chunk_bytes)
                if not chunk:
                    break
                await self._process_and_broadcast(chunk)

            return True
        except Exception as e:
            logger.warning(f"arecord 캡처 실패 ({e}), 다른 백엔드 탐색")
            if self._process:
                try:
                    self._process.terminate()
                    await self._process.wait()
                except Exception:
                    pass
                self._process = None
            return False

    # --- 2. Windows WASAPI / DirectShow / PortAudio (sounddevice) 파이프라인 ---
    async def _start_sounddevice_capture(self, target_hostapi: Optional[str] = None) -> bool:
        try:
            import sounddevice as sd
        except (ImportError, OSError) as e:
            logger.warning(f"sounddevice 라이브러리 로드 불가 ({e})")
            return False

        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            selected_device_idx = None
            selected_api_name = ""

            # 타겟 Host API (WASAPI 또는 DirectSound/MME) 탐색
            target_api_idx = None
            if target_hostapi:
                for idx, api in enumerate(hostapis):
                    api_name_lower = api["name"].lower()
                    if target_hostapi in api_name_lower:
                        target_api_idx = idx
                        selected_api_name = api["name"]
                        break

            # 디바이스 매칭
            for idx, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    # Host API 필터링 (지정된 경우)
                    if target_api_idx is not None and dev["hostapi"] != target_api_idx:
                        continue
                    
                    # 사용자 지정 장치명 매칭 (지정된 경우)
                    if self.device_name != "default" and self.device_name.lower() not in dev["name"].lower():
                        continue
                    
                    selected_device_idx = idx
                    if not selected_api_name:
                        selected_api_name = hostapis[dev["hostapi"]]["name"]
                    break

            if selected_device_idx is None:
                # 필터 없이 기본 입력 장치 탐색
                default_in = sd.default.device[0]
                if default_in is not None and default_in >= 0:
                    selected_device_idx = default_in
                    selected_api_name = hostapis[devices[selected_device_idx]["hostapi"]]["name"]

            if selected_device_idx is None:
                logger.warning(f"적합한 오디오 입력 장치를 찾을 수 없습니다. (타겟: {target_hostapi})")
                return False

            dev_info = devices[selected_device_idx]
            backend_label = f"WASAPI" if "wasapi" in selected_api_name.lower() else (
                "DirectShow" if "direct" in selected_api_name.lower() else selected_api_name
            )
            logger.info(f"선택된 오디오 장치: [{selected_device_idx}] {dev_info['name']} (API: {selected_api_name})")

            # 오디오 프레임 전달용 비동기 큐
            audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=15)
            loop = self._loop or asyncio.get_event_loop()

            def sd_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"sounddevice 상태 알림: {status}")
                # float32 또는 int16 정규화 변환
                if indata.dtype == np.int16:
                    raw_bytes = indata.tobytes()
                else:
                    # float32 -> int16
                    int16_data = np.clip(indata * 32767.0, -32768, 32767).astype(np.int16)
                    raw_bytes = int16_data.tobytes()

                # 비동기 이벤트 루프로 스레드 안전하게 전달
                try:
                    loop.call_soon_threadsafe(
                        lambda: audio_queue.put_nowait(raw_bytes) if not audio_queue.full() else None
                    )
                except Exception:
                    pass

            self._sd_stream = sd.InputStream(
                device=selected_device_idx,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                dtype="int16",
                callback=sd_callback,
            )
            self._sd_stream.start()

            self.active_backend = f"{backend_label} ({dev_info['name'][:24]})"
            self.is_virtual_mode = False
            self.status_message = f"마이크 스트림 수신 중 ({backend_label})"
            logger.info(f"사운드 장치 스트림 시작 완료: {self.active_backend}")

            # 큐 소비 및 브로드캐스트 루프
            while self._running:
                chunk = await audio_queue.get()
                await self._process_and_broadcast(chunk)
                audio_queue.task_done()

            return True

        except Exception as e:
            logger.warning(f"sounddevice ({target_hostapi}) 초기화/스트리밍 실패: {e}")
            if self._sd_stream:
                try:
                    self._sd_stream.stop()
                    self._sd_stream.close()
                except Exception:
                    pass
                self._sd_stream = None
            return False

    # --- 3. 안전 폴백: 가상 테스트 톤 (Sine Wave 440Hz) ---
    async def _start_virtual_tone_generator(self):
        self.active_backend = "Virtual Tone Generator (가상 톤)"
        self.is_virtual_mode = True
        self.status_message = "가상 테스트 톤 모드 (마이크 미연결 / 테스트 모드)"
        logger.info("가상 테스트 톤 제너레이터 기동 (440Hz 사인파 펄스)")

        phase = 0.0
        freq = 440.0
        pulse_period = 2.0
        t_start = asyncio.get_event_loop().time()
        sleep_interval = self.chunk_size / self.sample_rate

        while self._running:
            t_now = asyncio.get_event_loop().time()
            elapsed = (t_now - t_start) % pulse_period

            envelope = 0.5 * (1.0 + math.sin(math.pi * elapsed)) if elapsed < 1.0 else 0.02
            t = np.arange(self.chunk_size) / self.sample_rate
            sine_wave = (np.sin(2.0 * np.pi * freq * t + phase) * 0.4 * envelope).astype(np.float32)
            phase = (phase + 2.0 * np.pi * freq * (self.chunk_size / self.sample_rate)) % (2.0 * np.pi)

            int16_samples = (sine_wave * 32767.0).astype(np.int16)
            raw_bytes = int16_samples.tobytes()

            await self._process_and_broadcast(raw_bytes)
            await asyncio.sleep(sleep_interval)

    async def _process_and_broadcast(self, raw_bytes: bytes):
        """소프트웨어 게인 적용 및 브로드캐스터 전달"""
        if self.gain != 1.0 and len(raw_bytes) > 0:
            arr = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            arr = np.clip(arr * self.gain, -32768, 32767).astype(np.int16)
            raw_bytes = arr.tobytes()

        await broadcaster.broadcast_chunk(raw_bytes)

    def get_status(self) -> dict:
        return {
            "is_running": self._running,
            "is_virtual_mode": self.is_virtual_mode,
            "is_fallback_tone": self.is_virtual_mode,
            "platform": sys.platform,
            "configured_backend": self.backend_setting,
            "active_backend": self.active_backend,
            "device": self.device_name,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "gain": self.gain,
            "status_message": self.status_message,
        }


# 싱글톤 오디오 엔진 인스턴스
audio_engine = AudioEngine()
