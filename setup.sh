#!/usr/bin/env bash
# 校內運動會系統 - 一鍵初始化 (macOS/Linux)
set -e
PYTHON=${PYTHON:-python3}

echo "=== 安裝套件 ==="
$PYTHON -m pip install -r requirements.txt

echo "=== 建立資料庫 ==="
$PYTHON db_init.py

echo "=== 產生示範資料 ==="
$PYTHON make_demo_data.py
$PYTHON import_data.py students templates/students_demo.xlsx
$PYTHON import_data.py events templates/events_demo.xlsx
$PYTHON import_data.py bib
$PYTHON import_data.py regs templates/registrations_demo.xlsx
$PYTHON create_accounts.py

echo ""
echo "[OK] 初始化完成"
echo "啟動：$PYTHON web_app.py"
