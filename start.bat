@echo off
REM 校內運動會系統 - 啟動網頁 (Windows)
set PYTHON=C:\Users\DW\anaconda3\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo 啟動網頁伺服器 http://127.0.0.1:5000
echo   admin / admin123
echo 學生: 學號 = 密碼
echo.
echo Ctrl+C 停止
"%PYTHON%" -X utf8 web_app.py
pause
