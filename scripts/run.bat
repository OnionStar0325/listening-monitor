@echo off
chcp 65001 >nul
setlocal

echo ========================================================
echo   🎙️ Listening Monitor - Windows 스트리밍 서버 시작
echo ========================================================

REM 윈도우에서는 기본 포트를 8443(비특권)으로 권장하거나, 
REM 관리자 권한 실행 시 443으로 실행할 수 있습니다.
if "%PORT%"=="" (
    set PORT=8443
)

REM 오디오 백엔드 기본값: WASAPI (Windows Audio Session API)
if "%AUDIO_CAPTURE_BACKEND%"=="" (
    set AUDIO_CAPTURE_BACKEND=wasapi
)

echo [설정 안내]
echo - 서비스 포트 : %PORT% (브라우저 주소: https://localhost:%PORT%)
echo - 오디오 백엔드: %AUDIO_CAPTURE_BACKEND% (WASAPI / DirectShow)
echo.
echo * 자체 서명 SSL 인증서 경고가 브라우저에 표시되면 [고급] -^> [계속 진행]을 클릭하세요.
echo * 기본 관리자 계정: admin / admin1234!
echo.
echo --------------------------------------------------------

cd /d "%~dp0\.."
python main.py

if errorlevel 1 (
    echo.
    echo [오류 발생] 서버가 비정상 종료되었습니다.
    echo 443 포트 사용 시 관리자 권한이 필요할 수 있습니다.
    pause
)
