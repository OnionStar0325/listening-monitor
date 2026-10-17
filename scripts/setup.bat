@echo off
chcp 65001 >nul
echo ========================================================
echo   Listening Monitor - Windows 환경 설정 스크립트
echo ========================================================

echo [1/2] Python 환경 확인 중...
python --version
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo https://www.python.org 에서 Python 3.8 이상을 설치해 주세요.
    pause
    exit /b 1
)

echo.
echo [2/2] 필수 파이썬 라이브러리 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   설치가 완료되었습니다!
echo   'scripts\run.bat' 을 실행하여 서버를 시작하세요.
echo ========================================================
pause
