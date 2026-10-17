/**
 * Listening Monitor - 초저지연 실시간 오디오 플레이어 (Web Audio & iOS 무중단 앵커)
 * 
 * [iOS Safari 화면 잠금 무중단 재생 솔루션]:
 * 1. 0.1초 무음 WAV 오디오 루프 앵커:
 *    - iOS WebKit은 화면 잠금(절전 모드) 진입 시 백그라운드 탭을 일시정지(freeze)시킵니다.
 *    - 사용자 터치 직후 HTML5 <audio playsinline loop> 무음 앵커를 재생시켜 OS의 AVAudioSessionCategoryPlayback을 점유합니다.
 * 2. MediaStreamDestination & MediaSession 연동:
 *    - Web Audio 출력을 MediaStreamDestination으로 변환하여 <audio playsinline>에 연결 및 MediaSession 등록.
 *    - 이를 통해 화면을 끄거나 잠금 화면에 들어가도 WebSocket과 오디오 프로세스가 멈추지 않고 100% 지속 재생됩니다.
 */

// iOS 환경 감지 (iPhone, iPad, iPadOS Safari 포함)
function detectIsIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) || 
           (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

// 0.1초 유효한 초경량 무음 PCM WAV Data URI (8kHz 8-bit mono, 1KB 미만)
const SILENT_WAV_DATA_URI = "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==";

class RealtimeAudioPlayer {
    constructor(options = {}) {
        this.sampleRate = options.sampleRate || 16000;
        this.token = options.token || "";
        this.statusElemId = options.statusElemId || "playerStatus";
        this.playBtnId = options.playBtnId || "playBtn";
        this.canvasId = options.canvasId || "vuMeter";
        this.onKicked = options.onKicked || null;

        this.isIOS = detectIsIOS();

        // Web Audio 노드
        this.audioCtx = null;
        this.gainNode = null;
        this.analyser = null;
        this.mediaStreamDestination = null;
        this.websocket = null;
        this.nextStartTime = 0;

        // iOS 잠금화면 무중단 오디오 앵커 엘리먼트들
        this.silentAudio = null;
        this.mediaStreamAudio = null;

        this.isPlaying = false;
        this.volume = 0.85;

        this.canvas = null;
        this.canvasCtx = null;
        this.animFrameId = null;
    }

    init() {
        this.canvas = document.getElementById(this.canvasId);
        if (this.canvas) {
            this.canvasCtx = this.canvas.getContext("2d");
            this._drawIdleVisualizer();
        }

        this._initAudioElements();
        this._setupMediaSession();
        this._setupVisibilityHandler();

        if (this.isIOS) {
            console.log("[Audio] iOS 기기 감지: 잠금화면 무중단 재생 앵커 및 MediaStream 파이프라인이 자동 활성화됩니다.");
        }
    }

    /**
     * iOS 백그라운드 유지를 위한 오디오 엘리먼트 초기화
     */
    _initAudioElements() {
        // 1. 무음 오디오 루프 앵커 (iOS CoreAudio 세션 점유용)
        let silent = document.getElementById("lmSilentAnchor");
        if (!silent) {
            silent = document.createElement("audio");
            silent.id = "lmSilentAnchor";
            silent.setAttribute("playsinline", "");
            silent.setAttribute("webkit-playsinline", "");
            silent.loop = true;
            silent.src = SILENT_WAV_DATA_URI;
            silent.style.display = "none";
            document.body.appendChild(silent);
        }
        this.silentAudio = silent;

        // 2. iOS Safari용 MediaStream 오디오 엘리먼트 (Web Audio 하드웨어 출력 라우팅용)
        if (this.isIOS) {
            let streamEl = document.getElementById("lmMediaStreamAudio");
            if (!streamEl) {
                streamEl = document.createElement("audio");
                streamEl.id = "lmMediaStreamAudio";
                streamEl.setAttribute("playsinline", "");
                streamEl.setAttribute("webkit-playsinline", "");
                streamEl.autoplay = true;
                streamEl.style.display = "none";
                document.body.appendChild(streamEl);
            }
            this.mediaStreamAudio = streamEl;
        }
    }

    _setupMediaSession() {
        if (!("mediaSession" in navigator)) return;

        try {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: "Listening Monitor (실시간 마이크 청취)",
                artist: "원격 마이크 스트리밍",
                album: "보안 모니터링",
            });

            navigator.mediaSession.setActionHandler("play", async () => {
                await this.start();
            });

            navigator.mediaSession.setActionHandler("pause", () => {
                this.stop();
            });
        } catch (e) {
            console.debug("MediaSession 설정 경고:", e);
        }
    }

    _setupVisibilityHandler() {
        document.addEventListener("visibilitychange", async () => {
            if (!document.hidden && this.isPlaying) {
                if (this.audioCtx && this.audioCtx.state === "suspended") {
                    try {
                        await this.audioCtx.resume();
                    } catch (e) {}
                }
                if (this.silentAudio && this.silentAudio.paused) {
                    try {
                        await this.silentAudio.play();
                    } catch (e) {}
                }
            }
        });
    }

    setVolume(val) {
        this.volume = Math.max(0, Math.min(1, val));
        if (this.gainNode && this.audioCtx) {
            this.gainNode.gain.setValueAtTime(this.volume, this.audioCtx.currentTime);
        }
        if (this.mediaStreamAudio) {
            this.mediaStreamAudio.volume = this.volume;
        }
    }

    async toggle() {
        if (this.isPlaying) {
            this.stop();
        } else {
            await this.start();
        }
    }

    async start() {
        if (this.isPlaying) return;
        this.isPlaying = true;

        // 1. 사용자 제스처 컨텍스트에서 무음 오디오 앵커 즉시 재생 (iOS 백그라운드 세션 점유)
        if (this.silentAudio) {
            try {
                this.silentAudio.currentTime = 0;
                await this.silentAudio.play();
            } catch (err) {
                console.warn("[Audio] 무음 앵커 재생 경고 (무시 가능):", err);
            }
        }

        // 2. Web Audio AudioContext 초기화 및 활성화
        this._initAudioContext();
        if (this.audioCtx.state === "suspended") {
            try {
                await this.audioCtx.resume();
            } catch (e) {
                console.warn("[Audio] AudioContext resume 경고:", e);
            }
        }

        // 시간 축 초기화 (중단 후 재개 시 이전 타임스탬프와의 시간차 보정)
        this.nextStartTime = this.audioCtx.currentTime;

        // 3. iOS MediaStream 오디오 재생 활성화
        if (this.isIOS && this.mediaStreamAudio) {
            if (this.mediaStreamDestination && this.mediaStreamAudio.srcObject !== this.mediaStreamDestination.stream) {
                this.mediaStreamAudio.srcObject = this.mediaStreamDestination.stream;
            }
            try {
                await this.mediaStreamAudio.play();
            } catch (e) {
                console.debug("[Audio] MediaStream 오디오 play 경고:", e);
            }
        }

        if ("mediaSession" in navigator) {
            navigator.mediaSession.playbackState = "playing";
        }

        // 4. WebSocket 연결
        this._connectWebSocket();

        this._updateUI(true);
        this._startVisualizer();
    }

    stop() {
        this.isPlaying = false;

        if ("mediaSession" in navigator) {
            navigator.mediaSession.playbackState = "paused";
        }

        // 무음 앵커 일시정지
        if (this.silentAudio) {
            try {
                this.silentAudio.pause();
            } catch (e) {}
        }

        // iOS MediaStream 오디오 일시정지 (srcObject 연결은 유지하여 재시작 시 즉시 소리 출력)
        if (this.mediaStreamAudio) {
            try {
                this.mediaStreamAudio.pause();
            } catch (e) {}
        }

        // WebSocket 연결 안전 종료 (이전 소켓의 뒤늦은 onclose 이벤트가 재시작된 플레이어를 강제 정지시키지 않도록 리스너 사전 해제)
        if (this.websocket) {
            const ws = this.websocket;
            this.websocket = null;
            ws.onopen = null;
            ws.onmessage = null;
            ws.onerror = null;
            ws.onclose = null;
            try {
                ws.close();
            } catch (e) {}
        }

        // 비주얼라이저 정지
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }

        this.nextStartTime = 0;
        this._setStatus("정지됨", "offline");
        this._updateUI(false);
        this._drawIdleVisualizer();
    }

    _initAudioContext() {
        if (this.audioCtx && this.audioCtx.state !== "closed") {
            // 이미 존재하는 컨텍스트의 경우, iOS MediaStream 연결 유효성 재확인
            if (this.isIOS && this.mediaStreamAudio && this.mediaStreamDestination) {
                if (this.mediaStreamAudio.srcObject !== this.mediaStreamDestination.stream) {
                    this.mediaStreamAudio.srcObject = this.mediaStreamDestination.stream;
                }
            }
            return;
        }

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        this.audioCtx = new AudioContextClass({ sampleRate: this.sampleRate });

        this.gainNode = this.audioCtx.createGain();
        this.gainNode.gain.setValueAtTime(this.volume, this.audioCtx.currentTime);

        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;

        this.gainNode.connect(this.analyser);

        // iOS의 경우 잠금화면 소리 출력을 위해 MediaStreamDestination 연결
        if (this.isIOS && this.audioCtx.createMediaStreamDestination && this.mediaStreamAudio) {
            this.mediaStreamDestination = this.audioCtx.createMediaStreamDestination();
            this.analyser.connect(this.mediaStreamDestination);
            this.mediaStreamAudio.srcObject = this.mediaStreamDestination.stream;
        } else {
            // 안드로이드, PC, 크롬북, 맥 등 일반 환경
            this.analyser.connect(this.audioCtx.destination);
        }

        this.nextStartTime = this.audioCtx.currentTime;
    }

    _connectWebSocket() {
        // 기존 소켓이 혹시 남아있다면 정리
        if (this.websocket) {
            const oldWs = this.websocket;
            this.websocket = null;
            oldWs.onclose = null;
            try { oldWs.close(); } catch(e) {}
        }

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        let wsUrl = `${protocol}//${window.location.host}/ws/stream`;
        if (this.token) {
            wsUrl += `?token=${encodeURIComponent(this.token)}`;
        }

        this._setStatus("스트림 연결 중...", "offline");
        const ws = new WebSocket(wsUrl);
        this.websocket = ws;
        ws.binaryType = "arraybuffer";

        ws.onopen = () => {
            // 현재 플레이어의 활성 소켓인 경우에만 상태 업데이트
            if (this.websocket === ws && this.isPlaying) {
                const modeText = this.isIOS ? "실시간 청취 중 (iOS 잠금화면 무중단 가동)" : "실시간 청취 중 (초저지연 WSS)";
                this._setStatus(modeText, "online");
            }
        };

        ws.onmessage = (event) => {
            if (this.websocket === ws && this.isPlaying && event.data instanceof ArrayBuffer) {
                this._playPcmChunk(event.data);
            }
        };

        ws.onerror = (err) => {
            if (this.websocket === ws) {
                console.error("WSS 스트림 에러:", err);
                this._setStatus("연결 오류", "offline");
            }
        };

        ws.onclose = (event) => {
            // 현재 활성 소켓의 종료 이벤트인 경우에만 처리
            if (this.websocket === ws) {
                this.websocket = null;
                if (event.code === 4001) {
                    this._setStatus("관리자에 의해 강제 종료됨", "offline");
                    if (this.onKicked) this.onKicked();
                    this.stop();
                } else if (this.isPlaying) {
                    this._setStatus("연결 끊김", "offline");
                    this.stop();
                }
            }
        };
    }

    _playPcmChunk(arrayBuffer) {
        if (!this.audioCtx || this.audioCtx.state === "closed" || !this.isPlaying) return;

        // 백그라운드 복구 와치독: AudioContext가 suspended 상태이면 즉시 재개
        if (this.audioCtx.state === "suspended") {
            try { this.audioCtx.resume(); } catch(e) {}
        }

        const int16Array = new Int16Array(arrayBuffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        const audioBuffer = this.audioCtx.createBuffer(1, float32Array.length, this.sampleRate);
        audioBuffer.copyToChannel(float32Array, 0);

        const sourceNode = this.audioCtx.createBufferSource();
        sourceNode.buffer = audioBuffer;
        sourceNode.connect(this.gainNode);

        const currentTime = this.audioCtx.currentTime;
        // 지터 버퍼 보정: 중단 후 재개하거나 잠금화면 전환 시 끊김 없이 부드럽게 스케줄링
        if (this.nextStartTime < currentTime || this.nextStartTime > currentTime + 0.35) {
            this.nextStartTime = currentTime + 0.04;
        }

        sourceNode.start(this.nextStartTime);
        this.nextStartTime += audioBuffer.duration;
    }

    _setStatus(text, className) {
        const elem = document.getElementById(this.statusElemId);
        if (elem) {
            elem.textContent = text;
            elem.className = `status-indicator ${className}`;
        }
    }

    _updateUI(playing) {
        const btn = document.getElementById(this.playBtnId);
        const playIcon = document.getElementById("playIcon");
        const playText = document.getElementById("playText");

        if (btn) {
            if (playing) {
                btn.classList.add("playing");
                if (playIcon) playIcon.textContent = "⏸";
                if (playText) playText.textContent = "청취 일시정지";
            } else {
                btn.classList.remove("playing");
                if (playIcon) playIcon.textContent = "▶";
                if (playText) playText.textContent = "실시간 청취 시작";
            }
        }
    }

    _startVisualizer() {
        if (!this.canvas || !this.canvasCtx || !this.analyser) return;
        const canvas = this.canvas;
        const ctx = this.canvasCtx;
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            if (!this.isPlaying) return;
            this.animFrameId = requestAnimationFrame(draw);

            this.analyser.getByteFrequencyData(dataArray);

            ctx.fillStyle = "#090d16";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const barWidth = (canvas.width / bufferLength) * 2.2;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height;

                const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
                gradient.addColorStop(0, "#10b981");
                gradient.addColorStop(0.6, "#f59e0b");
                gradient.addColorStop(1, "#ef4444");

                ctx.fillStyle = gradient;
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

                x += barWidth + 1;
            }
        };

        draw();
    }

    _drawIdleVisualizer() {
        if (!this.canvas || !this.canvasCtx) return;
        const ctx = this.canvasCtx;
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, this.canvas.height / 2);
        ctx.lineTo(this.canvas.width, this.canvas.height / 2);
        ctx.stroke();
    }
}

// 전역 인스턴스 래퍼
let globalPlayer = null;

function initAudioPlayer(options) {
    globalPlayer = new RealtimeAudioPlayer(options);
    globalPlayer.init();
    return globalPlayer;
}

async function toggleAudioPlayback() {
    if (globalPlayer) {
        await globalPlayer.toggle();
    }
}

function setPlayerVolume(val) {
    const vol = parseFloat(val) / 100.0;
    if (globalPlayer) globalPlayer.setVolume(vol);
    const label = document.getElementById("volumeValue");
    if (label) label.textContent = `${Math.round(vol * 100)}%`;
}
