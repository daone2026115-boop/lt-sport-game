@echo off
REM 校內運動會系統 - 一鍵初始化 (Windows)
setlocal enabledelayedexpansion

set PYTHON=C:\Users\DW\anaconda3\python.exe
if not exist "%PYTHON%" (
    echo [X] 找不到 Anaconda Python，改用系統 python
    set PYTHON=python
)

echo === 安裝套件 ===
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :err

echo === 建立資料庫 ===
"%PYTHON%" db_init.py

echo === 產生示範資料 ===
"%PYTHON%" make_demo_data.py
"%PYTHON%" import_data.py students templates/students_demo.xlsx
"%PYTHON%" import_data.py events templates/events_demo.xlsx
"%PYTHON%" import_data.py bib
"%PYTHON%" import_data.py regs templates/registrations_demo.xlsx
"%PYTHON%" create_accounts.py

echo.
echo [OK] 初始化完成
echo.
echo 下一步：執行 start.bat 啟動網頁伺服器
echo   或直接跑：python web_app.py
pause
goto :eof

:err
echo [X] 安裝失敗，請檢查 Python 環境
pause
