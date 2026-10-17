/**
 * 실시간 오디오 보안 모니터 관리자 웹 대시보드 인터랙션 스크립트
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. 오디오 플레이어 초기화 (관리자 모니터링용)
    initAudioPlayer({
        statusElemId: "playerStatus",
        playBtnId: "playBtn",
        canvasId: "vuMeter"
    });

    // 2. 초기 데이터 로드 및 2초 주기 폴링 시작
    fetchAllData();
    setInterval(fetchAllData, 2000);

    // 3. 언어 전환 시 실시간 데이터 즉각 재렌더링
    window.addEventListener("languageChanged", () => {
        fetchAllData();
    });
});

// 전체 모니터링 데이터 일괄 갱신
async function fetchAllData() {
    try {
        await Promise.all([
            fetchSystemStats(),
            fetchAudioStatus(),
            fetchSessions()
        ]);
    } catch (e) {
        console.warn("대시보드 폴링 오류:", e);
    }
}

// 1. 시스템 리소스 조회
async function fetchSystemStats() {
    const res = await fetch("/api/system/stats");
    if (!res.ok) {
        if (res.status === 401) window.location.href = "/login";
        return;
    }
    const data = await res.json();

    const tempPrefix = window.i18n ? window.i18n.t("stat_temp_prefix") : "온도: ";
    const uptimePrefix = window.i18n ? window.i18n.t("nav_uptime_prefix") : "가동 시간: ";

    document.getElementById("cpuStat").textContent = `${data.cpu_percent}%`;
    document.getElementById("tempStat").textContent = `${tempPrefix}${data.cpu_temperature} °C`;
    document.getElementById("memStat").textContent = `${data.memory_percent}%`;
    document.getElementById("memDetailStat").textContent = `${data.memory_used_mb} / ${data.memory_total_mb} MB`;
    document.getElementById("serverUptime").textContent = `${uptimePrefix}${data.uptime_str}`;
}

// 2. 오디오 엔진 상태 및 게인 조회
async function fetchAudioStatus() {
    const res = await fetch("/api/system/audio");
    if (!res.ok) return;
    const data = await res.json();

    const badge = document.getElementById("audioModeBadge");
    const detail = document.getElementById("audioDetail");
    const gainSlider = document.getElementById("inputGain");
    const gainValue = document.getElementById("gainValue");

    if (data.is_virtual_mode) {
        badge.textContent = window.i18n ? window.i18n.t("stat_audio_virtual") : "가상 톤";
        badge.className = "stat-value text-accent";
        const unrec = window.i18n ? window.i18n.t("stat_audio_unrec") : "마이크 미인식";
        detail.textContent = `${unrec} (${data.configured_backend})`;
    } else {
        const activeText = window.i18n ? window.i18n.t("stat_audio_normal") : "마이크 활성";
        badge.textContent = data.active_backend || activeText;
        badge.className = "stat-value text-success";
        detail.textContent = `${data.device} (${data.sample_rate}Hz)`;
    }

    if (!gainSlider.dataset.userEditing) {
        gainSlider.value = Math.round(data.gain * 10);
        gainValue.textContent = `${data.gain.toFixed(1)}x`;
    }
}

// 3. 소프트웨어 게인(증폭) 조절
async function updateGain(val) {
    const gain = parseFloat(val) / 10.0;
    document.getElementById("gainValue").textContent = `${gain.toFixed(1)}x`;
    try {
        await fetch("/api/system/audio/gain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gain: gain })
        });
    } catch (e) {
        console.error("게인 설정 실패:", e);
    }
}

// 4. 활성 세션 목록 조회 및 테이블 렌더링
async function fetchSessions() {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const data = await res.json();

    const unitCount = window.i18n ? window.i18n.t("stat_unit_count") : "개";
    const streamPrefix = window.i18n ? window.i18n.t("stat_streaming_prefix") : "실시간 청취 중: ";
    const streamSuffix = window.i18n ? window.i18n.t("stat_streaming_suffix") : "명";

    document.getElementById("activeSessionsCount").textContent = `${data.total_count}${unitCount}`;
    document.getElementById("streamingCount").textContent = `${streamPrefix}${data.active_streaming_count}${streamSuffix}`;

    const tbody = document.getElementById("sessionTableBody");
    if (!data.sessions || data.sessions.length === 0) {
        const noSessions = window.i18n ? window.i18n.t("no_sessions") : "등록된 세션이 없습니다.";
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">${noSessions}</td></tr>`;
        return;
    }

    const roleAdmin = window.i18n ? window.i18n.t("role_admin") : "관리자";
    const roleListener = window.i18n ? window.i18n.t("role_listener") : "청취자";
    const activeText = window.i18n ? window.i18n.t("stream_badge_active") : "청취 중";
    const idleText = window.i18n ? window.i18n.t("stream_badge_idle") : "대기";
    const kickText = window.i18n ? window.i18n.t("btn_kick") : "추방(Kick)";

    let rowsHtml = "";
    data.sessions.forEach(s => {
        const roleBadge = s.role === "admin"
            ? `<span class="badge badge-admin">${roleAdmin}</span>`
            : `<span class="badge badge-listener">${roleListener}</span>`;

        const streamBadge = s.is_streaming
            ? `<span class="status-indicator online">${activeText}</span>`
            : `<span class="status-indicator offline">${idleText}</span>`;

        const duration = formatDuration(s.duration_seconds);
        const isSelf = s.role === "admin";

        const kickBtn = isSelf
            ? '<span class="text-muted small">-</span>'
            : `<button class="btn btn-danger-sm" onclick="kickSession('${s.session_id}')">${kickText}</button>`;

        rowsHtml += `
            <tr>
                <td><strong>${escapeHtml(s.client_name)}</strong><br><small class="text-muted">${s.session_id.substring(0, 16)}...</small></td>
                <td>${roleBadge}</td>
                <td><code>${escapeHtml(s.ip_address)}</code></td>
                <td><small title="${escapeHtml(s.user_agent)}">${parseDevice(s.user_agent)}</small></td>
                <td>${duration}</td>
                <td>${streamBadge}</td>
                <td>${kickBtn}</td>
            </tr>
        `;
    });
    tbody.innerHTML = rowsHtml;
}

// 5. 특정 세션 강제 추방(Kick)
async function kickSession(sessionId) {
    const confirmMsg = window.i18n ? window.i18n.t("confirm_kick") : "해당 세션의 접속을 즉시 강제 종료(추방)하시겠습니까?";
    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch(`/api/sessions/${sessionId}/kick`, { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            await fetchAllData();
        } else {
            alert(data.detail || "추방 실패");
        }
    } catch (e) {
        alert((window.i18n ? window.i18n.t("server_comm_error") : "서버 통신 오류: ") + e.message);
    }
}

// 6. 모든 청취자 일괄 추방
async function kickAllListeners() {
    const confirmMsg = window.i18n ? window.i18n.t("confirm_kick_all") : "현재 연결된 모든 청취자의 세션을 강제 종료하시겠습니까?";
    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch("/api/sessions/kick-all-listeners", { method: "POST" });
        const data = await res.json();
        alert(data.message);
        await fetchAllData();
    } catch (e) {
        alert((window.i18n ? window.i18n.t("server_comm_error") : "오류 발생: ") + e.message);
    }
}

// 7. 청취자 초대 링크, 토큰 및 QR 코드 발급 (초대 생성 버튼 클릭 시 호출)
async function createInviteToken() {
    const nameInput = document.getElementById("inviteName");
    const expireSelect = document.getElementById("inviteExpire");
    const name = nameInput ? nameInput.value.trim() : "";
    
    if (!name) {
        alert(window.i18n ? window.i18n.t("alert_enter_name") : "청취자 이름을 입력해 주세요. (예: 거실 태블릿, 스마트폰)");
        if (nameInput) nameInput.focus();
        return;
    }

    const hours = expireSelect ? parseInt(expireSelect.value, 10) : 24;
    const baseUrl = `${window.location.protocol}//${window.location.host}`;

    try {
        const res = await fetch("/api/sessions/invite", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                client_name: name, 
                valid_hours: hours,
                base_url: baseUrl
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            renderQrCodeData(data.url, data.qr_png, name);
            if (nameInput) nameInput.value = "";
        } else {
            alert((window.i18n ? window.i18n.t("alert_invite_fail") : "초대 링크 생성 실패: ") + (data.detail || "오류가 발생했습니다."));
        }
    } catch (e) {
        alert((window.i18n ? window.i18n.t("server_comm_error") : "통신 오류: ") + e.message);
    }
}

// QR 코드 및 초대 정보 렌더링 (초대 생성 완료 시 호출)
function renderQrCodeData(url, qrPngDataUrl, clientName) {
    // 1. URL 인풋 채우기
    const urlInput = document.getElementById("generatedUrl");
    if (urlInput) urlInput.value = url;

    // 2. 카드 내 QR 이미지 세팅
    const qrImg = document.getElementById("qrImage");
    const qrPlaceholder = document.getElementById("qrPlaceholder");
    if (qrImg && qrPngDataUrl) {
        qrImg.src = qrPngDataUrl;
        qrImg.style.display = "block";
    }
    if (qrPlaceholder) {
        qrPlaceholder.style.display = "none";
    }

    // 3. 확대 모달 이미지 세팅
    const modalImg = document.getElementById("qrModalImage");
    const modalTitle = document.getElementById("qrModalTitle");
    const isEn = window.i18n && window.i18n.getLanguage() === "en";

    if (modalImg && qrPngDataUrl) {
        modalImg.src = qrPngDataUrl;
    }
    if (modalTitle && clientName) {
        modalTitle.textContent = isEn ? `📱 QR Code for ${clientName}` : `📱 ${clientName} 접속용 QR 코드`;
    }

    const targetLabel = document.getElementById("inviteTargetLabel");
    if (targetLabel && clientName) {
        targetLabel.innerHTML = isEn 
            ? `QR & link for <strong>${escapeHtml(clientName)}</strong> are now active.`
            : `<strong>${escapeHtml(clientName)}</strong> 초대용 QR 및 링크가 활성화되었습니다.`;
    }

    // 4. 숨겨져 있던 생성 결과 영역 노출!
    const inviteResult = document.getElementById("inviteResult");
    if (inviteResult) {
        inviteResult.classList.remove("hidden");
    }
}

// QR 확대 모달 열기/닫기
function openQrModal() {
    const modal = document.getElementById("qrModal");
    if (modal) modal.classList.remove("hidden");
}

function closeQrModal() {
    const modal = document.getElementById("qrModal");
    if (modal) modal.classList.add("hidden");
}

function copyInviteUrl() {
    const input = document.getElementById("generatedUrl");
    if (!input || !input.value) return;
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
        alert(window.i18n ? window.i18n.t("alert_copy_done") : "초대 링크가 클립보드에 복사되었습니다!");
    }).catch(err => {
        alert((window.i18n ? window.i18n.t("alert_copy_fail") : "복사 실패: ") + err);
    });
}

// 8. 비밀번호 변경 모달
function openPasswordModal() {
    document.getElementById("passwordModal").classList.remove("hidden");
    document.getElementById("pwAlert").classList.add("hidden");
    document.getElementById("oldPassword").value = "";
    document.getElementById("newPassword").value = "";
}

function closePasswordModal() {
    document.getElementById("passwordModal").classList.add("hidden");
}

async function submitPasswordChange() {
    const oldP = document.getElementById("oldPassword").value;
    const newP = document.getElementById("newPassword").value;
    const alertBox = document.getElementById("pwAlert");

    if (!newP || newP.length < 4) {
        alert(window.i18n ? window.i18n.t("alert_pw_min_length") : "새 비밀번호를 4자 이상 입력하세요.");
        return;
    }

    try {
        const res = await fetch("/api/auth/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldP, new_password: newP })
        });
        const data = await res.json();
        if (res.ok) {
            alert(window.i18n ? window.i18n.t("alert_pw_changed") : "비밀번호가 성공적으로 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.");
            closePasswordModal();
        } else {
            alertBox.textContent = data.detail || "비밀번호 변경 실패";
            alertBox.classList.remove("hidden");
        }
    } catch (e) {
        alertBox.textContent = (window.i18n ? window.i18n.t("server_comm_error") : "통신 오류: ") + e.message;
        alertBox.classList.remove("hidden");
    }
}

// 9. 로그아웃
async function logout() {
    const isEn = window.i18n && window.i18n.getLanguage() === "en";
    const confirmMsg = isEn ? "Do you want to log out of the admin console?" : "관리자 콘솔에서 로그아웃하시겠습니까?";
    if (!confirm(confirmMsg)) return;

    try {
        await fetch("/api/auth/logout", { method: "POST" });
    } finally {
        window.location.href = "/login";
    }
}

// 유틸리티
function formatDuration(sec) {
    const isEn = window.i18n && window.i18n.getLanguage() === "en";
    if (sec < 60) return isEn ? `${sec}s ago` : `${sec}초 전`;
    if (sec < 3600) return isEn ? `${Math.floor(sec / 60)}m ago` : `${Math.floor(sec / 60)}분 전`;
    return isEn ? `${Math.floor(sec / 3600)}h ago` : `${Math.floor(sec / 3600)}시간 전`;
}

function parseDevice(ua) {
    const isEn = window.i18n && window.i18n.getLanguage() === "en";
    if (!ua) return isEn ? "Unknown" : "알 수 없음";
    if (ua.includes("Android")) return isEn ? "📱 Android" : "📱 안드로이드";
    if (ua.includes("iPhone") || ua.includes("iPad")) return isEn ? "🍎 iOS Device" : "🍎 iOS 기기";
    if (ua.includes("Windows")) return isEn ? "💻 Windows PC" : "💻 윈도우 PC";
    if (ua.includes("Mac")) return "💻 Mac";
    if (ua.includes("Linux")) return "🐧 Linux";
    return isEn ? "🌐 Web Browser" : "🌐 웹 브라우저";
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
