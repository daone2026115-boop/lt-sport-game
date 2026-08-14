@echo off
REM ────────────────────────────────────────────
REM  一鍵呼叫啟動 (Windows)
REM  自動安裝 + 建 DB + 啟動網頁 + 開瀏覽器
REM ────────────────────────────────────────────
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PYTHON=C:\Users\DW\anaconda3\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo.
echo === [1/4] 檢查 Python ===
"%PYTHON%" --version 2>nul
if errorlevel 1 (
    echo [X] 找不到 Python，請先安裝 Anaconda 或 Python 3.10+
    pause & exit /b 1
)

echo.
echo === [2/4] 檢查套件 ===
"%PYTHON%" -c "import flask, pandas, openpyxl, matplotlib" 2>nul
if errorlevel 1 (
    echo 缺少套件，執行安裝...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] 套件安裝失敗
        pause & exit /b 1
    )
) else (
    echo [OK] 套件齊全
)

echo.
echo === [3/4] 檢查資料庫 ===
if not exist "data\sportmeet.db" (
    echo 首次啟動，建立資料庫與示範資料...
    "%PYTHON%" db_init.py
    "%PYTHON%" make_demo_data.py
    "%PYTHON%" import_data.py students templates/students_demo.xlsx
    "%PYTHON%" import_data.py events templates/events_demo.xlsx
    "%PYTHON%" import_data.py bib
    "%PYTHON%" import_data.py regs templates/registrations_demo.xlsx
    "%PYTHON%" create_accounts.py
    echo [OK] 初始化完成
) else (
    echo [OK] 資料庫已存在 (data\sportmeet.db)
)

echo.
echo === [4/4] 啟動網頁 ===
echo.
echo   ─────────────────────────────────────────
echo    網址：http://127.0.0.1:5000
echo    管理員：admin / admin123
echo    學生：帳號=學號、密碼=學號
echo   ─────────────────────────────────────────
echo   Ctrl+C 停止伺服器
echo.

REM 5 秒後開瀏覽器 (讓伺服器先起來)
start "" cmd /c "timeout /t 5 /nobreak >nul & start http://127.0.0.1:5000"

"%PYTHON%" -X utf8 web_app.py

echo.
echo 伺服器已停止
pause
