@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo YouTube Downloader をセットアップしています...

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [エラー] Python 3 が見つかりません。
        echo https://www.python.org/downloads/ からPythonをインストールし、
        echo 「Add Python to PATH」を有効にしてから再実行してください。
        goto :error
    )
    set "PYTHON_CMD=python"
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo FFmpeg が見つからないため、wingetでインストールします...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [エラー] winget が見つかりません。
        echo Microsoft Storeから「アプリ インストーラー」を導入して再実行してください。
        goto :error
    )

    winget install --id Gyan.FFmpeg --exact --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [エラー] FFmpegのインストールに失敗しました。
        goto :error
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Python仮想環境を作成しています...
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 (
        echo.
        echo [エラー] Python仮想環境の作成に失敗しました。
        goto :error
    )
)

echo 必要なPythonパッケージをインストールしています...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade -r "requirements.txt"
if errorlevel 1 (
    echo.
    echo [エラー] Pythonパッケージのインストールに失敗しました。
    goto :error
)

echo.
echo セットアップが完了しました。run.bat からアプリを起動できます。
pause
exit /b 0

:error
echo.
pause
exit /b 1
