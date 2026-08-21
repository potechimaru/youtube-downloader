@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [エラー] セットアップが完了していません。
    echo 先に setup.bat を実行してください。
    echo.
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [エラー] FFmpeg が見つかりません。
    echo setup.bat を再実行し、必要であればWindowsへ再サインインしてください。
    echo.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "%~dp0app.py"
if errorlevel 1 (
    echo [エラー] アプリを起動できませんでした。
    echo.
    pause
    exit /b 1
)

exit /b 0
