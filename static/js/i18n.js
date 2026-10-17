/**
 * Listening Monitor - 클라이언트 다국어(i18n) 모듈 (한국어 & English)
 */

const I18N_DICTIONARY = {
    ko: {
        // 네비게이션
        lang_name: "English",
        nav_uptime_prefix: "가동 시간: ",
        nav_change_pw: "🔑 비밀번호 변경",
        nav_logout: "로그아웃",

        // 시스템 상태 지표
        stat_cpu: "호스트 CPU 사용률",
        stat_temp_prefix: "온도: ",
        stat_ram: "메모리 사용량 (RAM)",
        stat_sessions: "현재 연결 세션",
        stat_unit_count: "개",
        stat_streaming_prefix: "실시간 청취 중: ",
        stat_streaming_suffix: "명",
        stat_audio: "오디오 스트림 상태",
        stat_audio_normal: "마이크 활성",
        stat_audio_virtual: "가상 톤",
        stat_audio_unrec: "마이크 미인식",

        // 플레이어 패널
        player_title: "🎧 실시간 청취 & 마이크 제어",
        player_status_stopped: "정지됨",
        player_status_connecting: "스트림 연결 중...",
        player_status_online: "실시간 청취 중",
        player_status_ios_online: "실시간 청취 중 (iOS 잠금화면 무중단 가동)",
        player_status_offline: "연결 끊김",
        player_status_error: "연결 오류",
        player_status_kicked: "관리자에 의해 강제 종료됨",
        btn_start_listen: "실시간 청취 시작",
        btn_pause_listen: "청취 일시정지",
        label_volume: "청취 볼륨:",
        label_mic_gain: "마이크 입력 게인(소프트웨어 증폭):",

        // 초대 & QR 코드
        invite_title: "🔗 청취자 초대 & QR 코드 발급",
        invite_desc: "스마트폰(Android/iOS)이나 PC에서 별도 앱 설치 없이 접속할 수 있는 보안 초대 링크 및 QR 코드를 생성합니다.",
        ph_invite_name: "청취자 이름 (예: 거실 태블릿, 스마트폰)",
        opt_1h: "1시간 유효",
        opt_6h: "6시간 유효",
        opt_24h: "24시간 유효",
        opt_7d: "7일 유효",
        btn_create_invite: "초대 생성",
        label_generated_url: "현재 생성된 접속 URL:",
        ph_generated_url: "초대 생성 버튼을 누르면 URL이 표시됩니다",
        btn_copy: "📋 복사",
        btn_copied: "✅ 복사됨!",
        invite_target_label: "수신자는 링크를 열면 웹 브라우저로 즉시 청취할 수 있습니다.",
        qr_scan_title: "📱 스마트폰 카메라로 스캔",
        qr_click_zoom: "클릭 시 확대 보기",

        // 활성 세션 테이블
        session_mgmt_title: "👥 활성 세션 관리",
        session_mgmt_desc: "현재 시스템에 인증되었거나 오디오를 청취 중인 클라이언트 목록입니다.",
        btn_kick_all: "🚨 모든 청취자 일괄 추방",
        th_user: "사용자 / 세션",
        th_role: "역할",
        th_ip: "접속 IP",
        th_device: "기기 / 브라우저",
        th_time: "접속 시간",
        th_status: "청취 상태",
        th_control: "관리 제어",
        role_admin: "관리자",
        role_listener: "청취자",
        stream_badge_active: "청취 중",
        stream_badge_idle: "대기",
        btn_kick: "추방(Kick)",
        no_sessions: "등록된 세션이 없습니다.",
        seconds_ago: "초 전",
        minutes_ago: "분 전",
        hours_ago: "시간 전",

        // 모달 창
        pw_modal_title: "🔑 관리자 비밀번호 변경",
        label_old_pw: "현재 비밀번호",
        label_new_pw: "새 비밀번호 (4자 이상)",
        btn_cancel: "취소",
        btn_save: "변경 저장",
        btn_saving: "저장 중...",
        qr_modal_title_default: "📱 스마트폰 접속 QR 코드",
        qr_modal_desc: "스마트폰 카메라로 비추면 즉시 청취 페이지로 접속됩니다.",
        btn_close: "닫기",

        // 청취자 페이지
        listener_header_title: "실시간 오디오 모니터",
        listener_status_ready: "연결 준비 중...",
        listener_status_online: "실시간 수신 중",
        listener_status_stopped: "정지됨",
        listener_status_blocked: "연결 차단됨",
        listener_play_start: "청취 시작하기",
        listener_play_pause: "청취 일시정지",
        listener_label_volume: "볼륨:",
        alert_kicked_text: "🚨 알림: 관리자에 의해 세션 연결이 종료되었습니다.",
        footer_secure_text: "🔒 TLS 암호화 보안 스트림 구동 중",

        // 로그인 페이지
        login_subtitle: "실시간 오디오 보안 스트리밍 & 관리 시스템",
        label_username: "관리자 계정",
        label_password: "비밀번호",
        btn_login: "보안 접속 시작",
        btn_logging_in: "접속 중...",
        login_footer_secure: "🔒 TLS/WSS 암호화 보안 통신 구동 중",
        login_footer_default_pw: "기본 비밀번호는 admin1234! 입니다.",

        // JS 다이얼로그
        confirm_kick: "해당 세션의 접속을 즉시 강제 종료(추방)하시겠습니까?",
        confirm_kick_all: "현재 연결된 모든 청취자의 세션을 강제 종료하시겠습니까?",
        alert_enter_name: "청취자 이름을 입력해 주세요. (예: 거실 태블릿, 스마트폰)",
        alert_invite_fail: "초대 링크 생성 실패: ",
        alert_copy_done: "초대 링크가 클립보드에 복사되었습니다!",
        alert_copy_fail: "복사 실패: ",
        alert_pw_min_length: "새 비밀번호를 4자 이상 입력하세요.",
        alert_pw_changed: "비밀번호가 성공적으로 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.",
        server_comm_error: "서버 통신 오류: "
    },
    en: {
        // Navigation
        lang_name: "한국어",
        nav_uptime_prefix: "Uptime: ",
        nav_change_pw: "🔑 Change Password",
        nav_logout: "Logout",

        // System Telemetry Cards
        stat_cpu: "Host CPU Usage",
        stat_temp_prefix: "Temp: ",
        stat_ram: "Memory Usage (RAM)",
        stat_sessions: "Active Sessions",
        stat_unit_count: "",
        stat_streaming_prefix: "Active Listeners: ",
        stat_streaming_suffix: "",
        stat_audio: "Audio Stream Status",
        stat_audio_normal: "Mic Active",
        stat_audio_virtual: "Virtual Tone",
        stat_audio_unrec: "Mic Not Detected",

        // Player Panel
        player_title: "🎧 Live Audio & Mic Control",
        player_status_stopped: "Stopped",
        player_status_connecting: "Connecting...",
        player_status_online: "Live Streaming",
        player_status_ios_online: "Live Streaming (iOS Lock-Screen Background Active)",
        player_status_offline: "Disconnected",
        player_status_error: "Connection Error",
        player_status_kicked: "Disconnected by Administrator",
        btn_start_listen: "Start Listening",
        btn_pause_listen: "Pause Listening",
        label_volume: "Listening Volume:",
        label_mic_gain: "Mic Input Gain (Software Amp):",

        // Invite & QR Code Panel
        invite_title: "🔗 Invite Listeners & QR Code",
        invite_desc: "Generate secure invite links and QR codes accessible directly from smartphone (Android/iOS) or PC browsers without app installation.",
        ph_invite_name: "Client Name (e.g. Living Room Tablet, iPhone)",
        opt_1h: "Valid for 1 Hour",
        opt_6h: "Valid for 6 Hours",
        opt_24h: "Valid for 24 Hours",
        opt_7d: "Valid for 7 Days",
        btn_create_invite: "Create Invite",
        label_generated_url: "Generated Access URL:",
        ph_generated_url: "Click 'Create Invite' to generate an access URL",
        btn_copy: "📋 Copy",
        btn_copied: "✅ Copied!",
        invite_target_label: "Recipients can immediately listen in their web browser upon opening this link.",
        qr_scan_title: "📱 Scan with Smartphone Camera",
        qr_click_zoom: "Click to Enlarge",

        // Active Session Management Table
        session_mgmt_title: "👥 Active Session Management",
        session_mgmt_desc: "List of clients currently authenticated or listening to the audio stream.",
        btn_kick_all: "🚨 Kick All Listeners",
        th_user: "User / Session",
        th_role: "Role",
        th_ip: "IP Address",
        th_device: "Device / Browser",
        th_time: "Connected Time",
        th_status: "Stream Status",
        th_control: "Action",
        role_admin: "Admin",
        role_listener: "Listener",
        stream_badge_active: "Listening",
        stream_badge_idle: "Idle",
        btn_kick: "Kick",
        no_sessions: "No active sessions registered.",
        seconds_ago: "s ago",
        minutes_ago: "m ago",
        hours_ago: "h ago",

        // Modal Dialogs
        pw_modal_title: "🔑 Change Admin Password",
        label_old_pw: "Current Password",
        label_new_pw: "New Password (min 4 chars)",
        btn_cancel: "Cancel",
        btn_save: "Save Changes",
        btn_saving: "Saving...",
        qr_modal_title_default: "📱 Smartphone Access QR Code",
        qr_modal_desc: "Point your smartphone camera to connect to the listening page immediately.",
        btn_close: "Close",

        // Listener Page
        listener_header_title: "Realtime Audio Monitor",
        listener_status_ready: "Ready to Connect...",
        listener_status_online: "Streaming Live Audio",
        listener_status_stopped: "Stopped",
        listener_status_blocked: "Connection Blocked",
        listener_play_start: "Start Listening",
        listener_play_pause: "Pause Listening",
        listener_label_volume: "Volume:",
        alert_kicked_text: "🚨 Notice: Session terminated by administrator.",
        footer_secure_text: "🔒 TLS Encrypted Secure Stream Active",

        // Login Page
        login_subtitle: "Realtime Audio Security Streaming & Monitoring System",
        label_username: "Admin Username",
        label_password: "Password",
        btn_login: "Secure Login",
        btn_logging_in: "Logging in...",
        login_footer_secure: "🔒 TLS/WSS Encrypted Secure Communication Active",
        login_footer_default_pw: "Default password is admin1234!",

        // JS Dialogs
        confirm_kick: "Are you sure you want to kick and disconnect this session immediately?",
        confirm_kick_all: "Are you sure you want to disconnect all active listeners?",
        alert_enter_name: "Please enter a client name. (e.g. Living Room Tablet, iPhone)",
        alert_invite_fail: "Failed to create invite link: ",
        alert_copy_done: "Invite link copied to clipboard!",
        alert_copy_fail: "Copy failed: ",
        alert_pw_min_length: "New password must be at least 4 characters long.",
        alert_pw_changed: "Password changed successfully. Please log in with the new password.",
        server_comm_error: "Server communication error: "
    }
};

class I18nManager {
    constructor() {
        this.lang = localStorage.getItem("lm_lang") || "ko";
        if (!I18N_DICTIONARY[this.lang]) {
            this.lang = "ko";
        }
    }

    getLanguage() {
        return this.lang;
    }

    setLanguage(newLang) {
        if (!I18N_DICTIONARY[newLang]) return;
        this.lang = newLang;
        localStorage.setItem("lm_lang", newLang);
        this.apply();
        window.dispatchEvent(new CustomEvent("languageChanged", { detail: { lang: newLang } }));
    }

    toggle() {
        const target = this.lang === "ko" ? "en" : "ko";
        this.setLanguage(target);
    }

    t(key, fallback = "") {
        const dict = I18N_DICTIONARY[this.lang] || I18N_DICTIONARY.ko;
        return dict[key] !== undefined ? dict[key] : (fallback || key);
    }

    apply() {
        document.documentElement.lang = this.lang;

        // 1. data-i18n 텍스트 치환
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            const translated = this.t(key);
            if (translated !== undefined) {
                el.textContent = translated;
            }
        });

        // 2. data-i18n-html HTML 치환
        document.querySelectorAll("[data-i18n-html]").forEach(el => {
            const key = el.getAttribute("data-i18n-html");
            const translated = this.t(key);
            if (translated !== undefined) {
                el.innerHTML = translated;
            }
        });

        // 3. data-i18n-placeholder 속성 치환
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.getAttribute("data-i18n-placeholder");
            const translated = this.t(key);
            if (translated !== undefined) {
                el.placeholder = translated;
            }
        });

        // 4. data-i18n-title 속성 치환
        document.querySelectorAll("[data-i18n-title]").forEach(el => {
            const key = el.getAttribute("data-i18n-title");
            const translated = this.t(key);
            if (translated !== undefined) {
                el.title = translated;
            }
        });

        // 5. 언어 전환 토글 버튼 라벨 갱신
        const langToggleLabel = document.getElementById("langLabel");
        if (langToggleLabel) {
            langToggleLabel.textContent = `🌐 ${this.t("lang_name")}`;
        }
    }
}

// 싱글톤 전역 객체 등록
window.i18n = new I18nManager();

// 페이지 로드 시 즉시 언어 적용
document.addEventListener("DOMContentLoaded", () => {
    window.i18n.apply();
});

function toggleLanguage() {
    window.i18n.toggle();
}
